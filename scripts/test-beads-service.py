#!/usr/bin/env python3
"""Exercise the managed service through its CLI with controlled native processes."""

import importlib.util
import json
import os
from pathlib import Path
import plistlib
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
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
        "dolt_mode":"server", "dolt_database":"octo", "dolt_server_host":"127.0.0.1",
        "dolt_server_port":int(args[args.index("--server-port")+1])}))
else:
    assert args[0] == "-C" and args[2] == "serve"
    assert Path.cwd() == Path(args[1])
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            if (root / "crash").exists(): os._exit(9)
            if self.path.startswith("/v0/beads/ready") and (root / "unready").exists():
                self.send_response(503)
                self.end_headers()
                return
            value = ({"database":"wrong" if (root / "wrong").exists() else "octo",
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
        config = self.home / ".config/beads-service/config.json"
        config.parent.mkdir(parents=True)
        first, second = free_port(), free_port()
        while second == first:
            second = free_port()
        self.ports = {"http_port": first, "sql_port": second}
        config.write_text(json.dumps(self.ports))
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

    def cli(self, action):
        return subprocess.run([sys.executable, str(SCRIPT), action, "--home", str(self.home)],
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


if __name__ == "__main__":
    unittest.main()
