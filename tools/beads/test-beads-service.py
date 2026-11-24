#!/usr/bin/env python3
"""Exercise the managed service through its CLI with controlled native processes."""

import importlib.util
import json
import os
from pathlib import Path
import plistlib
import hashlib
import fcntl
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from beads_lifecycle import loaded_binary_identity
SCRIPT = Path(__file__).resolve().with_name("beads-service.py")
spec = importlib.util.spec_from_file_location("beads_service", SCRIPT)
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)

NATIVE = r'''import http.server, json, os, socket, socketserver, sys, time
from pathlib import Path
root = Path(__file__).parent
with (root / "processes").open("a") as output:
    output.write(str(os.getpid()) + "\n")
args = sys.argv[1:]
with (root / "operations").open("a") as output:
    output.write(json.dumps(args) + "\n")
if Path(__file__).name == "bd":
    args = [arg for arg in args if arg not in ("--sandbox", "--readonly", "--json")]
    if args[0] == "-C":
        assert Path.cwd() == Path(args[1])
        args = args[2:]
if Path(__file__).name == "dolt":
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", int(args[args.index("--port")+1])))
    listener.listen()
    while True:
        listener.accept()[0].close()
elif args[0] == "init":
    assert "-C" not in args
    assert (Path.cwd() / ".git").is_dir()
    beads = Path.cwd() / ".beads"
    beads.mkdir()
    (beads / "metadata.json").write_text(json.dumps({
        "dolt_mode":"server", "dolt_database":args[args.index("--database")+1], "dolt_server_host":"127.0.0.1",
        "dolt_server_port":int(args[args.index("--server-port")+1])}))
elif args[0] == "sql":
    if (root / "hang-branch").exists(): time.sleep(60)
    print(json.dumps([{"branch":"wrong" if (root / "wrong-branch").exists() else "main"}]
                     if "ACTIVE_BRANCH" in args[1] else [{"hash":"checkpoint-head"}]))
elif args[:3] == ["dolt","remote","list"]:
    print(json.dumps([{"name":"origin","url":"git+https://github.com/lanej/beads-tasks.git"}]))
elif args[:2] == ["dolt","commit"]:
    print("Checkpoint committed")
elif args[:2] == ["dolt","push"]:
    if (root / "fail-push").exists(): sys.exit(7)
    print("Push complete")
else:
    assert args[0] == "serve"
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            if (root / "crash").exists(): os._exit(9)
            if self.path.startswith("/v0/beads/ready") and (root / "unready").exists():
                self.send_response(503)
                self.end_headers()
                return
            metadata=json.loads((Path.cwd() / ".beads/metadata.json").read_text())
            value = ({"database":"wrong" if (root / "wrong").exists() else metadata["dolt_database"],
                      "beads_dir":str(Path.cwd() / ".beads"), "repo_root":str(Path.cwd()),
                      "dolt_mode":"server"} if self.path.endswith("context") else {})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(value).encode())
    class LoopbackHTTPServer(http.server.HTTPServer):
        # HTTPServer resolves its server name during bind; this fixture needs no DNS.
        def server_bind(self):
            socketserver.TCPServer.server_bind(self)
    LoopbackHTTPServer(("127.0.0.1", int(args[-1].split(":")[-1])), Handler).serve_forever()
'''


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


class HomebrewRuntime(unittest.TestCase):
    """Socket-free provisioning decisions, not native compatibility evidence."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="beads-homebrew-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.share, self.state, _ = service.paths(self.home)
        self.catalog = tomllib.loads((ROOT / "bootstrap/tools.toml").read_text())["tools"]["beads"]
        self.brew = self.root / "brew"
        self.brew.touch()
        self.binaries = {}
        self.prefixes = {}
        for name, formula in (("bd", "beads"), ("dolt", "dolt")):
            prefix = self.root / "Cellar" / formula / "installed-version"
            binary = prefix / "bin" / name
            binary.parent.mkdir(parents=True)
            binary.write_text("external executable must not be modified\n")
            binary.chmod(0o555)
            link = self.root / "opt" / formula
            link.parent.mkdir(exist_ok=True)
            link.symlink_to(prefix, target_is_directory=True)
            self.prefixes[formula] = link
            self.binaries[name] = str(binary)
        self.responses = {
            ("bd", "version"): "bd version 1.3.4 (release)",
            ("dolt", "version"): "dolt version 2.7.4",
            ("bd", "--help"): "--sandbox --readonly --json -C, --directory string",
            ("bd", "serve", "--help"): "Serve the Beads HTTP API --addr string",
            ("bd", "init", "--help"): "--server --external --server-host --server-port --database --prefix "
                                          "--skip-agents --skip-hooks --non-interactive",
            ("bd", "sql", "--help"): "--json",
            ("bd", "dolt", "remote", "list", "--help"): "--json",
            ("bd", "dolt", "commit", "--help"): "--message",
            ("bd", "dolt", "push", "--help"): "--remote --no-adopt",
            ("dolt", "sql-server", "--help"): "--host --port --data-dir",
        }
        self.calls = []
        self.start_patch(patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.home / ".config")}))
        self.start_patch(patch.object(service.platform, "system", return_value="Darwin"))
        self.start_patch(patch.object(service.platform, "machine", return_value="arm64"))
        self.start_patch(patch.object(service.shutil, "which", return_value=str(self.brew)))
        self.real_run = service.run
        self.command = self.start_patch(patch.object(service, "run", side_effect=self.native))
        self.manager = self.start_patch(patch.object(service, "manage", side_effect=AssertionError("service control forbidden")))
        self.start_patch(patch.object(socket, "socket", side_effect=AssertionError("socket forbidden")))
        self.start_patch(patch.object(subprocess, "run", side_effect=AssertionError("uncontrolled process forbidden")))

    def start_patch(self, patcher):
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def native(self, argv, **kwargs):
        argv = list(map(str, argv))
        self.calls.append(argv)
        self.assertEqual(kwargs["timeout"], 15)
        self.assertNotEqual(Path(kwargs["cwd"]), self.state)
        if argv[0] == str(self.brew):
            self.assertEqual(argv[1], "--prefix")
            return str(self.prefixes[argv[2]])
        return self.responses[(Path(argv[0]).name, *argv[1:])]

    def stage(self):
        service.install(self.home, start=False)

    def snapshot(self):
        return {str(path.relative_to(self.home)): (path.read_bytes(), path.stat().st_mode)
                for path in self.home.rglob("*") if path.is_file()}

    def test_stage_resolves_cellar_paths_without_download_or_service_control(self):
        original = {name: Path(path).read_bytes() for name, path in self.binaries.items()}
        self.stage()
        self.assertEqual(json.loads((self.share / "runtime.json").read_text()), self.binaries)
        self.assertFalse((self.share / "runtime").exists())
        self.assertFalse((self.state / "workspace").exists())
        self.manager.assert_not_called()
        for name, path in self.binaries.items():
            self.assertTrue(Path(path).is_absolute())
            self.assertEqual(Path(path).read_bytes(), original[name])
            self.assertEqual(Path(path).stat().st_mode & 0o777, 0o555)
        definition = plistlib.loads((self.home / "Library/LaunchAgents/com.lanej.beads.plist").read_bytes())
        self.assertEqual(definition["KeepAlive"], {"SuccessfulExit": False})

    def test_missing_or_incompatible_tools_preserve_installed_files_and_data(self):
        self.stage()
        data = self.state / "dolt" / "task-data"
        data.parent.mkdir()
        data.write_bytes(b"existing task data")
        before = self.snapshot()
        cases = [
            (("bd", "version"), "bd version 1.2.9", "require stable"),
            (("bd", "version"), "bd version 2.0.0", "require stable"),
            (("bd", "version"), "bd version 1.3.4-rc1", "require stable"),
            (("dolt", "version"), "dolt version unknown", "require stable"),
            (("dolt", "version"), "dolt version 2.7.3", "require stable"),
            (("bd", "serve", "--help"), "unknown command serve", "--addr"),
            (("bd", "init", "--help"), "--server-host --server-port", "--external"),
            (("bd", "init", "--help"), "--server-host --server-port --external --database --prefix "
             "--skip-agents --skip-hooks --non-interactive", "lacks required capabilities: --server"),
            (("bd", "dolt", "push", "--help"), "--remote", "--no-adopt"),
            (("dolt", "sql-server", "--help"), "--host --port", "--data-dir"),
        ]
        for key, response, error in cases:
            with self.subTest(key=key, response=response), patch.dict(self.responses, {key: response}):
                with self.assertRaisesRegex(ValueError, error):
                    self.stage()
                self.assertEqual(self.snapshot(), before)
        Path(self.binaries["dolt"]).chmod(0o755)
        with self.assertRaisesRegex(ValueError, "read-only for guarded activation"):
            self.stage()
        self.assertEqual(self.snapshot(), before)
        Path(self.binaries["dolt"]).unlink()
        with self.assertRaisesRegex(ValueError, "Homebrew dolt.*current service preserved"):
            self.stage()
        self.assertEqual(self.snapshot(), before)
        self.manager.assert_not_called()

    def test_preflight_isolates_ambient_configuration_and_storage(self):
        ambient = {key: str(self.home / key) for key in
                   ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME")}
        ambient.update(BEADS_DIR=str(self.state / "workspace/.beads"),
                       BD_DATABASE="live", DOLT_ROOT_PATH=str(self.state / "dolt"))
        native = self.native

        def isolated(argv, **kwargs):
            env = kwargs["env"]
            temporary = str(kwargs["cwd"])
            for key in ambient:
                if key.startswith(("BEADS_", "BD_")):
                    self.assertNotIn(key, env)
                else:
                    self.assertEqual(env[key], temporary, key)
            self.assertEqual(env["HOMEBREW_NO_AUTO_UPDATE"], "1")
            self.assertEqual(env["HOMEBREW_NO_ANALYTICS"], "1")
            self.assertEqual(env["DOLT_CLI_NO_UPDATE_CHECK"], "1")
            return native(argv, **kwargs)

        with patch.dict(os.environ, ambient), patch.object(service, "run", side_effect=isolated):
            self.assertEqual(service.homebrew_runtime(self.catalog), self.binaries)
        self.assertFalse(self.share.exists())
        self.assertFalse(self.state.exists())

    def test_existing_configuration_and_workspace_survive_successful_staging(self):
        self.stage()
        config = service.paths(self.home)[2]
        config.write_text(config.read_text() + "\n# Operator settings must survive staging\n")
        metadata = self.state / "workspace/.beads/metadata.json"
        metadata.parent.mkdir(parents=True)
        metadata.write_text('{"dolt_mode":"server","operator":"existing identity"}')
        data = self.state / "dolt/task-data"
        data.parent.mkdir()
        data.write_bytes(b"existing task data")
        before = {path: path.read_bytes() for path in (config, metadata, data)}
        self.stage()
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.manager.assert_not_called()

    def test_formula_executable_escape_and_nonexecutable_are_rejected(self):
        self.stage()
        before = self.snapshot()
        binary = Path(self.binaries["bd"])
        binary.chmod(0o444)
        with self.assertRaisesRegex(ValueError, "Homebrew beads.*executable.*current service preserved"):
            self.stage()
        self.assertEqual(self.snapshot(), before)
        binary.unlink()
        outside = self.root / "outside-bd"
        outside.write_bytes(b"not the formula executable")
        outside.chmod(0o555)
        binary.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "outside its prefix.*current service preserved"):
            self.stage()
        self.assertEqual(self.snapshot(), before)
        self.manager.assert_not_called()

    def test_newer_stable_patch_and_minor_versions_are_accepted(self):
        self.responses[("bd", "version")] = "bd version 1.10.0"
        self.responses[("dolt", "version")] = "dolt version 2.10.0"
        self.assertEqual(service.homebrew_runtime(self.catalog), self.binaries)

    def test_missing_brew_bad_prefix_and_command_errors_are_actionable(self):
        with patch.object(service.shutil, "which", return_value=None), patch.object(Path, "is_file", return_value=False):
            with self.assertRaisesRegex(ValueError, "Homebrew not found.*Install/repair"):
                self.stage()
        self.assertFalse(self.share.exists())
        with patch.dict(self.prefixes, {"beads": Path("relative-prefix")}):
            with self.assertRaisesRegex(ValueError, "not absolute.*current service preserved"):
                self.stage()
        for error in (subprocess.CalledProcessError(1, "brew", output="formula not installed"),
                      subprocess.TimeoutExpired("brew", 15), OSError("not executable")):
            with self.subTest(error=error), patch.object(service, "run", side_effect=error):
                with self.assertRaisesRegex(ValueError, "Homebrew preflight failed.*Install/repair"):
                    self.stage()
        self.assertFalse(self.share.exists())

    def test_machine_stdout_remains_separate_from_homebrew_diagnostics(self):
        def completed(argv, **kwargs):
            self.assertEqual(kwargs["stdout"], subprocess.PIPE)
            self.assertEqual(kwargs["stderr"], subprocess.PIPE)
            self.assertTrue(kwargs["check"])
            self.assertTrue(kwargs["text"])
            stdout = self.native(argv, **{key: value for key, value in kwargs.items()
                                         if key not in ("stdout", "stderr", "check", "text")})
            return subprocess.CompletedProcess(argv, 0, stdout + "\n",
                "==> Downloading https://formulae.brew.sh/api/formula.jws.json\n"
                "==> Downloading https://formulae.brew.sh/api/cask.jws.json\n"
                "Already downloaded: /private/tmp/cache/Homebrew/downloads/formula.jws.json\n")

        with patch.object(service, "run", side_effect=self.real_run), patch.object(subprocess, "run", side_effect=completed):
            self.stage()
            self.assertEqual(json.loads((self.share / "runtime.json").read_text()), self.binaries)
            before = self.snapshot()
            # Chatter in stdout is invalid, even if its last line is a valid prefix.
            for invalid in ("relative-prefix", "", "Downloading formula metadata\n" + str(self.prefixes["beads"])):
                with self.subTest(stdout=invalid), patch.dict(self.prefixes, {"beads": invalid}):
                    with self.assertRaisesRegex(ValueError, "not absolute.*current service preserved"):
                        self.stage()
                    self.assertEqual(self.snapshot(), before)
        self.manager.assert_not_called()

    def test_failed_commands_preserve_both_output_streams_and_existing_installation(self):
        self.stage()
        before = self.snapshot()
        for error in (
            subprocess.CalledProcessError(7, [str(self.brew), "--prefix", "beads"],
                                          output="partial machine output", stderr="Error: formula unavailable"),
            subprocess.TimeoutExpired("brew", 15, output=b"partial machine output",
                                      stderr=b"Error: formula unavailable"),
        ):
            with self.subTest(error=error), patch.object(service, "run", side_effect=self.real_run), \
                    patch.object(subprocess, "run", side_effect=error):
                with self.assertRaises(ValueError) as caught:
                    self.stage()
                diagnostic = str(caught.exception)
                for text in ("Homebrew preflight failed", "--prefix beads", "partial machine output",
                             "Error: formula unavailable", "Install/repair", "current service preserved"):
                    self.assertIn(text, diagnostic)
                self.assertEqual(self.snapshot(), before)
        self.manager.assert_not_called()

    def test_linux_keeps_private_verified_runtime_and_checksum_failure(self):
        with patch.object(service.platform, "system", return_value="Linux"):
            expected = {}
            for name, version in (("bd", self.catalog["version"]), ("dolt", self.catalog["dolt_version"])):
                directory = self.share / "runtime" / f"{name}-{version}-linux-arm64"
                directory.mkdir(parents=True)
                binary = directory / name
                binary.write_bytes(b"verified private runtime")
                (directory / "sha256").write_text(hashlib.sha256(binary.read_bytes()).hexdigest())
                expected[name] = str(binary)
            self.stage()
            self.assertEqual(json.loads((self.share / "runtime.json").read_text()), expected)
            self.command.assert_not_called()
            before = self.snapshot()
            Path(expected["bd"]).chmod(0o700)
            Path(expected["bd"]).write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "Preserve unverified runtime"):
                self.stage()
            self.assertEqual((self.share / "runtime.json").read_bytes(),
                             before[".local/share/beads-service/runtime.json"][0])
            self.command.assert_not_called()

    def test_linux_still_downloads_catalog_release_and_rejects_corrupt_archive(self):
        def corrupt(argv, **kwargs):
            self.assertEqual(argv[0], "curl")
            self.assertIn("/v1.3.4/beads_1.3.4_linux_arm64.tar.gz", argv[-1])
            Path(argv[argv.index("--output") + 1]).write_bytes(b"corrupt archive")
            return ""
        with patch.object(service.platform, "system", return_value="Linux"), patch.object(service, "run", side_effect=corrupt):
            with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                self.stage()
        self.assertFalse((self.share / "runtime.json").exists())
        self.manager.assert_not_called()


class SharedService(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="beads-service-test-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name).resolve()
        self.environment = {**os.environ, "XDG_CONFIG_HOME": str(self.home / ".config")}
        self.share = self.home / ".local/share/beads-service"
        self.state = self.home / ".local/state/beads-service"
        self.share.mkdir(parents=True)
        self.state.mkdir(parents=True)
        config = self.home / ".config/beads-service/config.toml"
        self.config = config
        config.parent.mkdir(parents=True)
        first, second = free_port(), free_port()
        while second == first:
            second = free_port()
        self.ports = {"http_port": first, "sql_port": second}
        template = (ROOT / "config/beads/trial.toml").read_text()
        config.write_text(template.replace("http_port = 8790", f"http_port = {first}")
                          .replace("sql_port = 3310", f"sql_port = {second}"))
        for name in ("bd", "dolt"):
            binary = self.share / name
            binary.write_text(f"#!{sys.executable}\n" + NATIVE)
            binary.chmod(0o700)
        (self.share / "runtime.json").write_text(json.dumps({name: str(self.share / name) for name in ("bd", "dolt")}))
        self.processes = []
        self.logs = []
        self.addCleanup(self.stop_processes)

    def stop_processes(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=20)
        for log in self.logs:
            log.close()

    def cli(self, action, *options):
        return subprocess.run([sys.executable, str(SCRIPT), action, *options, "--home", str(self.home)],
                              env=self.environment, capture_output=True, text=True, timeout=10)

    def start(self):
        log = (self.home / f"log-{len(self.processes)}").open("w+")
        self.logs.append(log)
        process = subprocess.Popen([sys.executable, str(SCRIPT), "run", "--home", str(self.home)],
                                   env=self.environment, stdout=log, stderr=log)
        self.processes.append(process)
        return process

    def ready(self):
        deadline = time.monotonic() + 10
        result = None
        while time.monotonic() < deadline:
            result = self.cli("status")
            if result.returncode == 0:
                return json.loads(result.stdout)
            time.sleep(0.05)
        try:
            context = service.fetch_json(f"http://127.0.0.1:{self.ports['http_port']}/v0/beads/context")
        except (OSError, ValueError) as error:
            context = str(error)
        diagnostics = {"status": result.stdout if result else None,
                       "stderr": result.stderr if result else None,
                       "context": context, "expected_beads_dir": str(self.state / "workspace/.beads"),
                       "processes": [process.poll() for process in self.processes]}
        self.fail("Service failed to become ready: " + json.dumps(diagnostics) + "\n" +
                  "".join(path.read_text() for path in self.home.glob("log-*")))

    def assert_children_stopped(self):
        # The init process is already reaped; neither long-running child may survive its owner.
        for pid in map(int, (self.share / "processes").read_text().splitlines()):
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)

    def test_single_owner_readiness_and_clean_shutdown(self):
        owner = self.start()
        self.assertTrue(self.ready()["ready"])
        duplicate = self.cli("run")
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn("already owns", duplicate.stderr)
        (self.share / "unready").touch()
        status = self.cli("status")
        self.assertEqual(status.returncode, 1)
        self.assertTrue(json.loads(status.stdout)["live"])
        self.assertFalse(json.loads(status.stdout)["ready"])
        (self.share / "unready").unlink()
        (self.share / "wrong").touch()
        self.assertEqual(self.cli("status").returncode, 1)
        owner.terminate()
        self.assertEqual(owner.wait(timeout=20), 0)
        self.assertFalse((self.state / "endpoint.json").exists())
        self.assert_children_stopped()
        (self.share / "wrong").unlink()
        restarted = self.start()
        self.assertTrue(self.ready()["ready"])
        restarted.terminate()
        self.assertEqual(restarted.wait(timeout=20), 0)
        self.assert_children_stopped()

    def test_native_checkpoint_refuses_mutable_owner_without_stopping_children(self):
        owner = self.start()
        self.ready()
        inventory = self.cli("inventory")
        self.assertEqual(inventory.returncode, 0, inventory.stderr)
        target = json.loads(inventory.stdout)["targets"][0]
        self.assertIsNone(target["running_identity"])
        self.environment["PROJECT_UPDATE_RUN_ID"] = str(uuid.uuid4())
        self.environment["PROJECT_UPDATE_EXPECTED_PROCESS"] = json.dumps(target["process"])
        refused = self.cli("checkpoint")
        self.assertEqual(refused.returncode, 3, refused.stderr)
        value = json.loads(refused.stdout)["targets"][0]
        self.assertEqual(value["checkpoint"]["state"], "refused")
        self.assertEqual(value["process"], target["process"])
        self.assertIsNone(owner.poll())
        self.assertTrue(self.ready()["ready"])

    def test_loaded_child_identity_rejects_replaced_executable_path(self):
        binary = self.home / "immutable-sleep"
        source = self.home / "native-child.c"
        source.write_text("#include <unistd.h>\nint main(void) { sleep(30); return 0; }\n")
        subprocess.run(["cc", str(source), "-o", str(binary)], check=True, capture_output=True)
        binary.chmod(0o500)
        child = subprocess.Popen([str(binary), "30"])
        self.processes.append(child)
        self.assertEqual(loaded_binary_identity(child.pid, binary),
                         hashlib.sha256(binary.read_bytes()).hexdigest())
        replacement = self.home / "replacement"
        replacement.write_bytes(b"replaced installed artifact")
        replacement.chmod(0o500)
        replacement.replace(binary)
        with self.assertRaisesRegex(ValueError, "image differs|vnode differs"):
            loaded_binary_identity(child.pid, binary)
        self.assertIsNone(child.poll())

    def test_failed_http_child_stops_database(self):
        owner = self.start()
        self.ready()
        (self.share / "crash").touch()
        self.cli("status")
        self.assertNotEqual(owner.wait(timeout=10), 0)
        self.assertFalse((self.state / "endpoint.json").exists())
        self.assert_children_stopped()

    def test_hung_startup_probe_cannot_outlive_the_shutdown_deadline(self):
        (self.share / "hang-branch").touch()
        owner = self.start()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            operations = self.share / "operations"
            if operations.exists() and any("SELECT ACTIVE_BRANCH() AS branch" in json.loads(line)
                                          for line in operations.read_text().splitlines()):
                break
            time.sleep(0.05)
        else:
            self.fail("Startup did not reach the controlled branch probe")
        owner.terminate()
        self.assertNotEqual(owner.wait(timeout=20), 0)
        self.assert_children_stopped()

    def test_existing_workspace_is_not_migrated(self):
        beads = self.state / "workspace/.beads"
        beads.mkdir(parents=True)
        metadata = beads / "metadata.json"
        original = '{"dolt_mode":"embedded"}'
        metadata.write_text(original)
        owner = self.start()
        self.assertNotEqual(owner.wait(timeout=10), 0)
        self.assertEqual(metadata.read_text(), original)
        self.assert_children_stopped()

    def test_native_units_keep_fixed_arguments_and_graceful_shutdown(self):
        with patch.object(service.platform, "system", return_value="Darwin"), patch.dict(os.environ, self.environment):
            definition = plistlib.loads(service.definition(self.home).read_bytes())
            self.assertEqual(definition["ProgramArguments"][-2:], ["--home", str(self.home)])
            self.assertGreaterEqual(definition["ExitTimeOut"], 30)
        with patch.object(service.platform, "system", return_value="Linux"), patch.dict(os.environ, self.environment):
            definition = service.definition(self.home).read_text()
            self.assertIn("KillMode=mixed\n", definition)
            self.assertIn("Restart=on-failure\n", definition)
            self.assertIn('Environment="XDG_CONFIG_HOME=' + self.environment["XDG_CONFIG_HOME"], definition)

    @unittest.skipUnless(service.platform.system() == "Linux", "Private runtimes are Linux-only; see HomebrewRuntime")
    def test_checksum_failure_prevents_runtime_execution_and_service_installation(self):
        curl = self.share / "curl"
        curl.write_text(f"#!{sys.executable}\nimport sys\nfrom pathlib import Path\n"
                        "Path(sys.argv[sys.argv.index('--output')+1]).write_bytes(b'corrupt release')\n")
        curl.chmod(0o700)
        self.environment["PATH"] = str(self.share) + os.pathsep + os.environ["PATH"]
        before = (self.share / "runtime.json").read_bytes()
        result = self.cli("install")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Checksum mismatch", result.stderr)
        self.assertFalse((self.share / "processes").exists())
        self.assertFalse((self.share / "beads-service.py").exists())
        self.assertEqual((self.share / "runtime.json").read_bytes(), before)

    @unittest.skipUnless(service.platform.system() == "Linux", "Private runtimes are Linux-only; see HomebrewRuntime")
    def test_install_can_stage_without_starting_any_process(self):
        catalog = tomllib.loads((ROOT / "bootstrap/tools.toml").read_text())["tools"]["beads"]
        target = {"Darwin": "darwin", "Linux": "linux"}[service.platform.system()]
        arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64"}[service.platform.machine()]
        for name, version in (("bd", catalog["version"]), ("dolt", catalog["dolt_version"])):
            directory = self.share / "runtime" / f"{name}-{version}-{target}-{arch}"
            directory.mkdir(parents=True)
            content = (self.share / name).read_bytes()
            (directory / name).write_bytes(content)
            (directory / name).chmod(0o700)
            (directory / "sha256").write_text(hashlib.sha256(content).hexdigest())
        before = self.config.read_bytes()
        result = self.cli("install", "--no-start")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["started"])
        self.assertFalse((self.share / "processes").exists())
        self.assertFalse((self.state / "workspace").exists())
        self.assertEqual(self.config.read_bytes(), before)
        launcher = self.home / ".local/bin/beads-service"
        installed = subprocess.run([str(launcher), "config", "--home", str(self.home)],
                                   env=self.environment, capture_output=True, text=True)
        self.assertEqual(installed.returncode, 0, installed.stderr)
        self.assertEqual(json.loads(installed.stdout)["workspace"]["database"], "octo")
        with (self.share / "install.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            blocked = self.cli("install", "--no-start")
            self.assertNotEqual(blocked.returncode, 0)
            inherited = subprocess.run(
                [sys.executable, str(SCRIPT), "install", "--no-start", "--home", str(self.home),
                 "--install-lock-fd", str(lock.fileno())], pass_fds=(lock.fileno(),),
                env=self.environment, capture_output=True, text=True, timeout=10)
            self.assertEqual(inherited.returncode, 0, inherited.stderr)
            after_child_exit = self.cli("install", "--no-start")
            self.assertNotEqual(after_child_exit.returncode, 0)

    def test_config_inspection_is_read_only_and_rejects_unsupported_behavior(self):
        before = sorted(str(path.relative_to(self.home)) for path in self.home.rglob("*"))
        result = self.cli("config")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["history"]["mode"], "manual")
        self.assertEqual(before, sorted(str(path.relative_to(self.home)) for path in self.home.rglob("*")))
        original = self.config.read_text()
        for invalid in (original.replace('mode = "manual"', 'mode = "automatic"'),
                        original + '\nunknown_switch = true\n',
                        original.replace(str(self.ports["sql_port"]), str(self.ports["http_port"]))):
            self.config.write_text(invalid)
            result = self.cli("config")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((self.share / "processes").exists())

    def test_legacy_ports_are_carried_forward_without_rewriting_local_settings(self):
        self.config.unlink()
        legacy = self.config.with_suffix(".json")
        original = json.dumps(self.ports, indent=4) + "\n"
        legacy.write_text(original)
        with patch.dict(os.environ, self.environment):
            service.seed(self.home, ROOT / "config/beads/trial.toml")
        self.assertEqual(legacy.read_text(), original)
        self.assertEqual(json.loads(self.cli("config").stdout)["service"], self.ports)
        self.config.write_text(self.config.read_text() + "\n# Local operator comment\n")
        local = self.config.read_bytes()
        with patch.dict(os.environ, self.environment):
            service.seed(self.home, ROOT / "config/beads/trial.toml")
        self.assertEqual(self.config.read_bytes(), local)

    def test_configured_database_is_used_and_wrong_branch_is_refused(self):
        self.config.write_text(self.config.read_text().replace('database = "octo"', 'database = "tasks"'))
        owner = self.start()
        self.assertEqual(self.ready()["database"], "tasks")
        owner.terminate()
        self.assertEqual(owner.wait(timeout=20), 0)
        (self.share / "wrong-branch").touch()
        rejected = self.start()
        self.assertNotEqual(rejected.wait(timeout=10), 0)
        self.assert_children_stopped()

    def test_private_checkpoint_records_confirmation_and_preserves_last_success_on_failure(self):
        self.start()
        self.ready()
        git = self.share / "git"
        git.write_text(f"#!{sys.executable}\nprint('" + 'a' * 40 + "\\trefs/dolt/data')\n")
        git.chmod(0o700)
        gh = self.share / "gh"
        gh.write_text(f"#!{sys.executable}\nfrom pathlib import Path\nimport json, sys\n"
                      "assert sys.argv[1:4] == ['repo', 'view', 'https://github.com/lanej/beads-tasks'], 'Wrong GitHub host for visibility check'\n"
                      "print(json.dumps({'visibility':'PUBLIC' if Path(__file__).with_name('public').exists() else 'PRIVATE'}))\n")
        gh.chmod(0o700)
        self.environment["PATH"] = str(self.share) + os.pathsep + os.environ["PATH"]
        self.environment["GH_HOST"] = "enterprise.example.invalid"
        result = self.cli("backup")
        self.assertEqual(result.returncode, 0, result.stderr)
        succeeded = json.loads(result.stdout)
        self.assertEqual(succeeded["state"], "succeeded")
        operations = [json.loads(line) for line in (self.share / "operations").read_text().splitlines()]
        push = next(args for args in operations if "push" in args)
        self.assertEqual(push[push.index("--remote") + 1], "origin")
        self.assertIn("--no-adopt", push)
        self.assertNotIn("--force", push)
        before = len(operations)
        (self.share / "public").touch()
        refused = self.cli("backup")
        self.assertNotEqual(refused.returncode, 0)
        operations = [json.loads(line) for line in (self.share / "operations").read_text().splitlines()]
        self.assertFalse(any("push" in args or "commit" in args for args in operations[before:]))
        (self.share / "public").unlink()
        (self.share / "fail-push").touch()
        uncertain = self.cli("backup")
        self.assertNotEqual(uncertain.returncode, 0)
        history = json.loads((self.state / "history.json").read_text())
        self.assertEqual(history["state"], "unconfirmed")
        self.assertEqual(history["lastSuccess"], succeeded["lastSuccess"])


if __name__ == "__main__":
    unittest.main()
