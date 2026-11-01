#!/usr/bin/env python3
"""Exercise primary selection through the installed launcher and native tmux.

Agent executables and Firstmate extension files are controlled fixtures. This
checks selection, installation, argv/environment transport, and reattachment;
it makes no model calls and does not validate upstream extension execution.
"""

import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time


ROOT = Path(__file__).resolve().parent.parent


class Terminal:
    def __init__(self, command, env):
        self.output = bytearray()
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 100, 0, 0))
            os.execvpe(command[0], command, env)

    def until(self, predicate):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if select.select([self.fd], [], [], 0.05)[0]:
                try:
                    self.output.extend(os.read(self.fd, 65536))
                except OSError:
                    pass
            result = predicate()
            if result:
                return result
        raise AssertionError(self.output.decode(errors="replace")[-4000:])

    def close(self):
        os.close(self.fd)
        try:
            if os.waitpid(self.pid, os.WNOHANG)[0]:
                return
            os.kill(self.pid, signal.SIGTERM)
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if os.waitpid(self.pid, os.WNOHANG)[0]:
                    return
                time.sleep(0.02)
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass


def main():
    tmux = shutil.which("tmux")
    if not tmux:
        raise SystemExit("Native tmux is required: install tmux, then run make test-firstmate-primary.")
    with (tempfile.TemporaryDirectory(prefix="firstmate-primary-") as temporary,
          tempfile.TemporaryDirectory(prefix="fm-", dir="/tmp") as sockets):
        temporary = Path(temporary).resolve()
        fixture_home = temporary / "home"
        executables = temporary / "bin"
        fixture_home.mkdir()
        executables.mkdir()
        (executables / "tmux").symlink_to(tmux)
        firstmate = fixture_home / "src/firstmate"
        (firstmate / "bin").mkdir(parents=True)
        session_start = firstmate / "bin/fm-session-start.sh"
        session_start.write_text("#!/bin/sh\nexit 0\n")
        session_start.chmod(0o755)
        # The primary's Firstmate home can differ from the install default.
        alternate = temporary / "another Firstmate checkout"
        shutil.copytree(firstmate, alternate)
        extensions = alternate / ".pi/extensions"
        extensions.mkdir(parents=True)
        (extensions / "fm-primary-turnend-guard.ts").write_text("// Fixture only.\n")
        (extensions / "fm-branch-supervision.ts").write_text("// Fixture only.\n")
        theme = fixture_home / ".files/rc/tmux.conf"
        theme.parent.mkdir(parents=True)
        theme.write_text("set -g default-shell /bin/bash\nset -g status off\n")
        record = temporary / "primary.json"
        agent_source = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
if sys.argv[1:] == ['--version']:
    print('1.4.0')
    raise SystemExit(0)
record = Path({str(record)!r})
pending = record.with_suffix('.pending')
pending.write_text(json.dumps({{
    'agent': Path(sys.argv[0]).name, 'args': sys.argv[1:], 'pid': os.getpid(),
    'cwd': os.getcwd(), 'home': os.environ.get('FM_HOME'),
    'backend': os.environ.get('FM_BACKEND'),
    'checkpoint': os.environ.get('FM_CODEX_WATCH_CHECKPOINT'),
}}))
pending.replace(record)
print('primary-ready>', flush=True)
for _ in sys.stdin:
    pass
"""
        for name in ("codex", "pi"):
            executable = executables / name
            executable.write_text(agent_source)
            executable.chmod(0o755)
        # macOS's default temporary path can exceed the Unix socket limit.
        socket_dir = Path(sockets)
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("FM_", "FIRSTMATE_", "TMUX", "ZELLIJ"))}
        env.update(HOME=str(fixture_home), PATH=str(executables) + os.pathsep + os.environ["PATH"],
                   SHELL="/bin/bash", TERM="xterm-256color", TMUX_TMPDIR=str(socket_dir),
                   FIRSTMATE_TMUX_SOCKET="primary-test", FM_BACKEND="tmux")
        install = ["make", "--no-print-directory", "firstmate-config", "IS_EASYPOST=false"]
        subprocess.run(install, cwd=ROOT, env=env, check=True, capture_output=True, timeout=15)
        launcher = str(fixture_home / ".local/bin/firstmate")
        primary_config = fixture_home / ".config/firstmate/primary-harness"
        assert primary_config.resolve() == ROOT / "firstmate/primary-harness"
        assert (firstmate / "config/crew-harness").read_text().strip() == "codex"

        def run(*args, environment=env, check=True):
            return subprocess.run([launcher, *args], env=environment, check=check,
                                  capture_output=True, text=True, timeout=10)

        def current(previous=None):
            if not record.exists():
                return None
            data = json.loads(record.read_text())
            return data if data["pid"] != previous else None

        terminals = []
        try:
            # Fresh installation retains the existing Codex primary.
            terminal = Terminal([launcher, "start", "--model", "fixture codex"], env)
            terminals.append(terminal)
            codex = terminal.until(current)
            assert codex["agent"] == "codex", codex
            assert codex["args"] == ["--approve-for-me", "--model", "fixture codex"], codex
            assert codex["checkpoint"] == "45", codex
            run("stop")
            terminal.close()
            terminals.remove(terminal)

            # A persistent local selection survives reinstall. A missing
            # required extension rejects the new session before launching Pi.
            primary_config.unlink()
            primary_config.write_text("pi\n")
            subprocess.run(install, cwd=ROOT, env=env, check=True, capture_output=True, timeout=15)
            assert primary_config.read_text() == "pi\n" and not primary_config.is_symlink()
            pi_env = {**env, "FIRSTMATE_HOME": str(alternate), "FM_CODEX_WATCH_CHECKPOINT": "999"}
            missing = run("start", environment=pi_env, check=False)
            assert missing.returncode != 0 and "fm-primary-pi-watch.ts" in missing.stderr, missing
            assert json.loads(record.read_text())["pid"] == codex["pid"], "failed preflight launched an agent"
            (extensions / "fm-primary-pi-watch.ts").write_text("// Fixture only.\n")
            terminal = Terminal([launcher, "start", "--model", "fixture/pi", "spaces; $(literal)"], pi_env)
            terminals.append(terminal)
            pi = terminal.until(lambda: current(codex["pid"]))
            assert pi["agent"] == "pi", pi
            assert pi["args"] == ["--model", "fixture/pi", "spaces; $(literal)"], pi
            assert pi["cwd"] == pi["home"] == str(alternate), pi
            assert pi["backend"] == "tmux" and pi["checkpoint"] is None, pi
            assert (firstmate / "config/crew-harness").read_text().strip() == "codex"

            # Reattaching with a different selection retains the live primary.
            run("tmux", "detach-client", "-s", "firstmate")
            terminal.close()
            terminals.remove(terminal)
            override_env = {**pi_env, "FM_PRIMARY_HARNESS": "codex"}
            terminal = Terminal([launcher, "start"], override_env)
            terminals.append(terminal)
            terminal.until(lambda: b"primary-ready>" in terminal.output)
            assert json.loads(record.read_text())["pid"] == pi["pid"]
            run("stop")
            terminal.close()
            terminals.remove(terminal)

            # The environment override selects the next captain, preserving
            # direct argument shorthand and the managed Pi preference.
            terminal = Terminal([launcher, "--model", "override"], override_env)
            terminals.append(terminal)
            overridden = terminal.until(lambda: current(pi["pid"]))
            assert overridden["agent"] == "codex", overridden
            assert overridden["args"] == ["--approve-for-me", "--model", "override"], overridden
            assert primary_config.read_text() == "pi\n"
        finally:
            try:
                run("stop", check=False)
            finally:
                for terminal in terminals:
                    terminal.close()
        print("Firstmate primary selection passed with native tmux and fixture agents.")


if __name__ == "__main__":
    main()
