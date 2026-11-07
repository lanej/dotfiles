#!/usr/bin/env python3
"""One bootstrap/recovery workflow; packages, SSH, services and Atuin CLI are fixtures."""
import contextlib
import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import plistlib
import runpy
import shlex
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
REAL_RUN = subprocess.run
spec = importlib.util.spec_from_file_location("atuin_setup", ROOT / "scripts/setup-atuin-sync.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


@contextlib.contextmanager
def database(path):
    with contextlib.closing(sqlite3.connect(str(path))) as db:
        with db:
            yield db


class SetupWorkflow(unittest.TestCase):
    def test_provision_then_recover_account_on_rerun(self):
        with tempfile.TemporaryDirectory(prefix="atuin-test-") as temporary:
            homes = [Path(temporary) / "mac", Path(temporary) / "dev"]
            for home in homes:
                root = home / ".files"
                for name in ("bootstrap.sh", "scripts/setup-atuin-sync.py", "sh/atuin.toml",
                             "sh/atuin-server.toml.template", "rc/systemd/atuin-server.service",
                             "rc/launchd/com.joshlane.atuin-sync-tunnel.plist.template"):
                    destination = root / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / name, destination)
                data = home / ".local/share/atuin"
                data.mkdir(parents=True)
                (data / "key").write_bytes(home.name.encode() + b"-original-key")
                # This fixture starts with pre-sharing settings, like an existing machine.
                (root / "sh/atuin.toml").write_text('auto_sync = false\nfilter_mode = "host"\n')
                for name in ("history.db", "records.db", "meta.db"):
                    with database(data / name) as db:
                        db.execute("create table saved (value text primary key)")
                        db.execute("insert into saved values (?)", (home.name,))
                if home == homes[1]:
                    # Atuin shell init can create a private store before enrollment.
                    (data / "shared-key").write_bytes(b"dev-unenrolled-key")
                    with database(data / "shared-records.db") as db:
                        db.execute("create table saved (value text primary key)")
                        db.execute("insert into saved values ('dev')")
            registered = {}
            linger = {"enabled": False}
            sessions = {str(home): "previous-server" for home in homes}
            fixture_bin = Path(temporary) / "bin"
            fixture_bin.mkdir()
            for program in ("uname", "getconf", "tr", "sed", "chmod"):
                (fixture_bin / program).symlink_to(shutil.which(program))
            make_request = Path(temporary) / "make-request"
            (fixture_bin / "make").write_text(
                '#!/bin/sh\n'
                'for argument do\n'
                '  case "$argument" in UV=*) atuin_uv=${argument#UV=} ;; esac\n'
                'done\n'
                '"$atuin_uv" --version >/dev/null || exit 1\n'
                'printf "%s\\n" "$@" > "$ATUIN_FIXTURE_MAKE_REQUEST"\n')
            (fixture_bin / "make").chmod(0o755)

            def bootstrap(host="dev2"):
                # Real Bash bootstrap flow; package installation and make's process boundary are fixtures.
                script = '''
source "$1"
os=macos
install_package_version() {
    if [ "$1" = uv ]; then
        printf '#!/bin/sh\\nexit 0\\n' > "$ATUIN_FIXTURE_BIN/uv"
        chmod 755 "$ATUIN_FIXTURE_BIN/uv"
    fi
}
setup_gh_auth() { :; }
gh() { return 1; }
install_dependencies() { install_package_version uv 0.12.11; }
install_dependencies
setup_atuin_sync
'''
                env = dict(os.environ, PATH=str(fixture_bin),
                           HOME=str(homes[0]), BASH_ENV="/dev/null",
                           ATUIN_FIXTURE_BIN=str(fixture_bin),
                           ATUIN_FIXTURE_MAKE_REQUEST=str(make_request),
                           ATUIN_SYNC_HOST=host)
                result = REAL_RUN(["/bin/bash", "-c", script, "bash",
                                   str(homes[0] / ".files/bootstrap.sh")],
                                  env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  universal_newlines=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                arguments = make_request.read_text().splitlines()
                self.assertIn("atuin-sync", arguments)
                host = next(a.split("=", 1)[1] for a in arguments if a.startswith("ATUIN_SYNC_HOST="))
                with patch.object(sys, "argv", ["setup-atuin-sync.py", "--host", host]):
                    runpy.run_path(str(homes[0] / ".files/scripts/setup-atuin-sync.py"), run_name="__main__")

            def which(program):
                if program == "atuin":
                    path = Path.home() / ".cargo/bin/atuin"
                    return str(path) if path.exists() else None
                return program

            def fake_run(argv, input=None, **kwargs):
                home = Path.home()
                data = home / ".local/share/atuin"
                output, error, code = "", "", 0
                program = Path(argv[0]).name
                if program == "ssh" and argv[1:2] == ["-G"]:
                    if argv[-1] == "admindev":
                        output = "controlpath {}/missing-master\n".format(temporary)
                    else:
                        output = ("hostname dev.example.test\nuser vagrant\nport 22\n"
                                  "identityagent /tmp/agent with spaces.sock\nproxyjump admindev\n"
                                  "identityfile ~/.ssh/id_rsa\n")
                elif program == "ssh" and "--remote" in argv[-1]:
                    with patch.object(Path, "home", return_value=homes[1]), patch.dict(os.environ, {"USER": "vagrant"}):
                        output = json.dumps(helper.server(json.loads(input)))
                elif program == "ssh" or program in ("systemctl", "launchctl"):
                    pass
                elif program == "loginctl":
                    if argv[1] == "show-user":
                        output = "Linger={}\n".format("yes" if linger["enabled"] else "no")
                    else:
                        code, error = 1, "PolicyKit unavailable"
                elif program == "sudo":
                    self.assertEqual(argv[1:], ["-n", "loginctl", "enable-linger", "vagrant"])
                    linger["enabled"] = True
                elif program == "git":
                    output = "josh@example.test\n"
                elif program == "bash":
                    version, binary = argv[-2:]
                    directory = home / (".cargo/bin" if binary == "atuin" else ".local/bin")
                    directory.mkdir(parents=True, exist_ok=True)
                    (directory / binary).write_text(version)
                elif program.startswith("atuin"):
                    command = argv[1:]
                    if command == ["--version"]:
                        output = program + " " + Path(argv[0]).read_text() + "\n"
                    elif command == ["key"]:
                        path = data / "shared-key"
                        output = (path if path.exists() else data / "key").read_bytes().hex() + "\n"
                    elif command == ["uuid"]:
                        output = home.name + "-session\n"
                    elif command == ["logout"]:
                        sessions.pop(str(home), None)
                        with database(data / "meta.db") as db:
                            db.execute("delete from saved")
                            db.execute("insert into saved values ('logged-out')")
                    elif command[0] == "login":
                        username = command[command.index("-u") + 1]
                        password = command[command.index("-p") + 1]
                        key = command[command.index("-k") + 1]
                        if str(home) in sessions:
                            output = "You are logged in to your sync server.\n"
                        elif (registered.get("username"), registered.get("password")) != (username, password):
                            code, error = 1, "Not registered."
                        elif key != (data / "shared-key").read_bytes().hex():
                            code, error = 1, "Wrong key."
                        else:
                            sessions[str(home)] = "selected-server"
                    elif command[0] == "register":
                        registered.update(username=command[command.index("-u") + 1],
                                          password=command[command.index("-p") + 1])
                        sessions[str(home)] = "selected-server"
                    elif command == ["history", "init-store"]:
                        with database(data / "shared-records.db") as db:
                            db.execute("create table if not exists saved (value text primary key)")
                    elif command == ["store", "verify"]:
                        if (data / "shared-key").read_bytes() == b"dev-unenrolled-key":
                            self.assertEqual(Path(kwargs["env"]["ATUIN_KEY_PATH"]), data / "shared-key")
                            self.assertEqual(Path(kwargs["env"]["ATUIN_RECORD_STORE_PATH"]), data / "shared-records.db")
                        if (data / "shared-key").exists() and (data / "shared-records.db").exists():
                            output = "Local store encryption verified OK\n"
                        else:
                            output = "Local store encryption failed\n"
                    elif command == ["sync"]:
                        if sessions.get(str(home)) != "selected-server":
                            code, error = 1, "Not logged in."
                        else:
                            for other in homes:
                                with database(other / ".local/share/atuin/history.db") as original:
                                    rows = original.execute("select value from saved").fetchall()
                                with database(data / "history.db") as db:
                                    db.executemany("insert or ignore into saved values (?)", rows)
                    else:
                        raise AssertionError("Unexpected Atuin operation")
                else:
                    raise AssertionError("Unexpected program: " + program)
                return subprocess.CompletedProcess(argv, code, output, error)

            output = io.StringIO()
            with patch.object(Path, "home", return_value=homes[0]), \
                    patch("platform.system", return_value="Darwin"), \
                    patch("shutil.which", side_effect=which), \
                    patch("subprocess.run", side_effect=fake_run), \
                    patch("urllib.request.urlopen", side_effect=lambda *a, **k: io.StringIO('{"version":"18.21.0"}')), \
                    patch("time.strftime", return_value="20261006-000000"), \
                    patch.dict(os.environ, {"USER": "josh"}), contextlib.redirect_stdout(output):
                bootstrap()
                account_path = homes[0] / ".local/share/atuin" / helper.ACCOUNT_FILE
                account = json.loads(account_path.read_text())
                account_path.unlink()
                bootstrap(host="")
                self.assertEqual(json.loads(account_path.read_text()), account)
                self.assertEqual((homes[0] / ".local/state/atuin-sync/host").read_text().strip(), "dev2")
                # An enrolled Linux host also configures and syncs on bootstrap reruns.
                with patch.object(Path, "home", return_value=homes[1]), \
                        patch("platform.system", return_value="Linux"), \
                        patch.dict(os.environ, {"USER": "vagrant"}):
                    helper.setup(argparse.Namespace(host="dev", tunnel_only=False))
            for home in homes:
                data = home / ".local/share/atuin"
                self.assertEqual((data / "shared-key").read_bytes(), b"mac-original-key")
                self.assertEqual((data / "key").read_bytes(), home.name.encode() + b"-original-key")
                self.assertEqual((data / helper.ACCOUNT_FILE).stat().st_mode & 0o777, 0o600)
                self.assertEqual(json.loads((data / helper.ACCOUNT_FILE).read_text()), account)
                with database(data / "history.db") as db:
                    self.assertEqual(set(db.execute("select value from saved")), {("mac",), ("dev",)})
                with database(data / "records.db") as db:
                    self.assertEqual(db.execute("select value from saved").fetchone(), (home.name,))
                self.assertTrue((home / ".config/atuin/config.toml").is_symlink())
                self.assertTrue(any((data / "backups").glob("setup-*/history.db")))
                restored_metadata = []
                for saved in (data / "backups").glob("setup-*/meta.db"):
                    with database(saved) as db:
                        restored_metadata.extend(row[0] for row in db.execute("select value from saved"))
                self.assertIn(home.name, restored_metadata)
            server_config = (homes[1] / ".config/atuin/server.toml").read_text()
            self.assertTrue(any((homes[1] / ".local/share/atuin/backups").glob("setup-*/original-shared-key")))
            self.assertTrue(linger["enabled"])
            self.assertIn("open_registration = false", server_config)
            self.assertIn('host = "127.0.0.1"', server_config)
            plist = (homes[0] / "Library/LaunchAgents/com.joshlane.atuin-sync-tunnel.plist").read_text()
            self.assertIn("vagrant@dev.example.test", plist)
            self.assertNotIn(account["password"], output.getvalue())
            self.assertNotIn(b"mac-original-key".hex(), output.getvalue())
            # Exercise the generated jump command with real SSH after its master
            # disappears. A local listener represents the Duo-protected bastion.
            job = plistlib.loads(plist.encode())
            proxy = next(a.split("=", 1)[1] for a in job["ProgramArguments"]
                         if a.startswith("ProxyCommand="))
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                listener.listen()
                config = Path(temporary) / "ssh_config"
                config.write_text(
                    "Host admindev\n  HostName 127.0.0.1\n  Port {}\n"
                    "  ControlMaster auto\n  ControlPath {}/missing-master\n".format(
                        listener.getsockname()[1], temporary))
                command = shlex.split(proxy.replace("%h:%p", "127.0.0.1:8888"))
                result = REAL_RUN(command[:1] + ["-F", str(config)] + command[1:],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                listener.settimeout(0.1)
                with self.assertRaises(TimeoutError):
                    listener.accept()
            self.assertFalse(job.get("KeepAlive", False))


if __name__ == "__main__":
    unittest.main()
