#!/usr/bin/env python3
"""Exercise the managed service through its CLI with controlled native processes."""

import importlib.util
import json
import os
from pathlib import Path
import plistlib
import hashlib
import socket
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SCRIPT = ROOT / "scripts/beads-service.py"
spec = importlib.util.spec_from_file_location("beads_service", SCRIPT)
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)

NATIVE = r'''import http.server, json, os, socket, sys
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
    http.server.HTTPServer(("127.0.0.1", int(args[-1].split(":")[-1])), Handler).serve_forever()
'''


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


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
        while time.monotonic() < deadline:
            result = self.cli("status")
            if result.returncode == 0:
                return json.loads(result.stdout)
            time.sleep(0.05)
        self.fail("Service failed to become ready: " + "".join(path.read_text() for path in self.home.glob("log-*")))

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

    def test_failed_http_child_stops_database(self):
        owner = self.start()
        self.ready()
        (self.share / "crash").touch()
        self.cli("status")
        self.assertNotEqual(owner.wait(timeout=10), 0)
        self.assertFalse((self.state / "endpoint.json").exists())
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
        gh.write_text(f"#!{sys.executable}\nfrom pathlib import Path\nimport json\n"
                      "print(json.dumps({'visibility':'PUBLIC' if Path(__file__).with_name('public').exists() else 'PRIVATE'}))\n")
        gh.chmod(0o700)
        self.environment["PATH"] = str(self.share) + os.pathsep + os.environ["PATH"]
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
