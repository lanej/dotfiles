#!/usr/bin/env python3
"""Exercise the installed tmux-style workflow through a real Zellij terminal.

Requires Zellij >=0.45.1 and fzf. Sessions, HOME and XDG directories are isolated;
only this check's named sessions are terminated. No user's shell files are read.
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
import tempfile
import termios
import time


ROOT = Path(__file__).resolve().parent.parent
PROMPT = b"zellij-ready> "


class Terminal:
    def __init__(self, binary, env, name):
        self.binary, self.env, self.name = binary, env, name
        self.output = bytearray()
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            # Set the slave's size before Zellij can query it. Doing this in the
            # parent after fork races the child's startup on a zero-sized PTY.
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 32, 120, 0, 0))
            os.chdir(env["HOME"])
            os.execvpe(binary, [binary, "attach", "--create", name], env)

    def drain(self, duration=0.08):
        end = time.monotonic() + duration
        while time.monotonic() < end:
            if select.select([self.fd], [], [], max(0, min(0.05, end - time.monotonic())))[0]:
                try:
                    chunk = os.read(self.fd, 65536)
                except OSError:
                    return
                if not chunk:
                    return
                self.output.extend(chunk)

    def send(self, value):
        os.write(self.fd, value)
        self.drain()

    def prefix(self, key):
        self.send(b"\x06" + key)

    def action(self, *args, session=None):
        with subprocess.Popen(
            [self.binary, "--session=" + (session or self.name), "action", *args],
            env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ) as command:
            # Keep consuming terminal renders while waiting for the CLI reply.
            # A full PTY buffer can otherwise stall the server during startup.
            deadline = time.monotonic() + 5
            while True:
                self.drain(0.01)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    command.kill()
                    stdout, stderr = command.communicate()
                    raise subprocess.TimeoutExpired(command.args, 5, stdout, stderr)
                try:
                    stdout, stderr = command.communicate(timeout=min(0.05, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            if command.returncode:
                raise subprocess.CalledProcessError(
                    command.returncode, command.args, stdout, stderr
                )
            return stdout

    def panes(self, session=None):
        return json.loads(self.action("list-panes", "--json", session=session))

    def tabs(self):
        return json.loads(self.action("list-tabs", "--json"))

    def terminals(self):
        return [p for p in self.panes() if not p["is_plugin"] and not p["is_suppressed"]]

    def until(self, description, predicate):
        deadline = time.monotonic() + 10
        last_error = None
        while time.monotonic() < deadline:
            self.drain()
            try:
                result = predicate()
                if result:
                    return result
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                    json.JSONDecodeError) as error:
                last_error = error
        details = [f"Timed out: {description}"]
        if last_error is not None:
            details.append(str(last_error))
            for stream in ("stdout", "stderr"):
                output = getattr(last_error, stream, None)
                if output:
                    if isinstance(output, bytes):
                        output = output.decode(errors="replace")
                    details.append(f"CLI {stream}:\n{output[-4000:]}")
        try:
            waited, status = os.waitpid(self.pid, os.WNOHANG)
            client_status = (f"exited with code {os.waitstatus_to_exitcode(status)}"
                             if waited else "still running")
        except ChildProcessError:
            client_status = "already reaped"
        details.append(f"Client process: {client_status}")
        details.extend(self.startup_diagnostics())
        output = self.output[-4000:].decode(errors="replace")
        details.append(f"Terminal output:\n{output or '<empty>'}")
        raise AssertionError("\n".join(details))

    def startup_diagnostics(self):
        details = []
        sample_pids = set()
        try:
            process = subprocess.run(
                ["ps", "-axo", "pid=,ppid=,stat=,command="],
                capture_output=True, text=True, timeout=5,
            )
            rows = [line.split(None, 3) for line in process.stdout.splitlines()]
            rows = [row for row in rows if len(row) == 4]
            # The server daemon reparents itself. Its unique socket path still
            # identifies it without exposing unrelated processes' arguments.
            socket_dir = self.env["ZELLIJ_SOCKET_DIR"]
            selected = {str(self.pid)} | {row[0] for row in rows if socket_dir in row[3]}
            while True:
                children = {row[0] for row in rows if row[1] in selected}
                if children <= selected:
                    break
                selected |= children
            related = [row for row in rows if row[0] in selected]
            details.append("Process snapshot (PID PPID STAT COMMAND):\n" +
                           "\n".join(" ".join(row) for row in related))
            sample_pids = {row[0] for row in related
                           if row[0] == str(self.pid) or "--server " in row[3]}
            if process.stderr:
                details.append(process.stderr)
        except (OSError, subprocess.TimeoutExpired) as error:
            details.append(f"Could not inspect test processes: {error}")
        if os.uname().sysname == "Darwin" and shutil.which("sample"):
            for pid in sorted(sample_pids):
                sample_path = Path(self.env["HOME"]) / f"process-{pid}.sample"
                try:
                    sample = subprocess.run(
                        ["sample", pid, "1", "1", "-file", str(sample_path)],
                        capture_output=True, text=True, timeout=5,
                    )
                    details.append(f"Process sample {pid}:\n{sample.stdout}{sample.stderr}")
                    if sample_path.exists():
                        details.append(sample_path.read_text(errors="replace")[:16000])
                except (OSError, subprocess.TimeoutExpired) as error:
                    details.append(f"Could not sample process {pid}: {error}")
        log = Path(self.env["TMPDIR"]) / f"zellij-{os.getuid()}" / "zellij-log" / "zellij.log"
        try:
            with log.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                handle.seek(max(0, handle.tell() - 16000))
                details.append("Zellij log:\n" + handle.read(16000).decode(errors="replace"))
        except OSError as error:
            details.append(f"Could not read isolated Zellij log: {error}")
        return details

    def close(self):
        os.close(self.fd)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                waited, _ = os.waitpid(self.pid, os.WNOHANG)
            except ChildProcessError:
                return
            if waited:
                return
            time.sleep(0.05)
        os.kill(self.pid, signal.SIGTERM)
        os.waitpid(self.pid, 0)


def main():
    binary = shutil.which("zellij")
    assert binary and shutil.which("fzf"), "Install Zellij >=0.45.1 and fzf before make test-zellij"
    with tempfile.TemporaryDirectory(prefix="zj-", dir="/tmp") as directory:
        # macOS reports process cwd through /private/tmp, the target of /tmp.
        temporary = Path(directory).resolve()
        home = temporary / "home"
        home.mkdir()
        runtime = temporary / "run"
        runtime.mkdir(mode=0o700)
        temp_files = temporary / "tmp"
        temp_files.mkdir(mode=0o700)
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh", "PS1": PROMPT.decode(),
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(temporary / "cache"),
               "XDG_DATA_HOME": str(temporary / "data"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temp_files),
               "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"]}
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "FZF_DEFAULT_OPTS",
                    "FZF_DEFAULT_OPTS_FILE", "FZF_DEFAULT_COMMAND", "ENV", "BASH_ENV"):
            env.pop(key, None)
        subprocess.run(["make", "--no-print-directory", "zellij"], cwd=ROOT, env=env,
                       check=True, capture_output=True, text=True)
        subprocess.run([binary, "setup", "--check"], env=env, check=True,
                       capture_output=True, text=True)
        name = "work-" + temporary.name
        second_name = "other-" + temporary.name
        clients = []
        try:
            terminal = Terminal(binary, env, name)
            clients.append(terminal)
            # CLI probes during first-client setup can race server initialization.
            # An actual rendered shell prompt proves that setup has completed.
            terminal.until("first shell starts", lambda:
                           PROMPT in terminal.output and len(terminal.terminals()) == 1)

            def top_bars():
                # list-panes excludes non-selectable bar plugins. Observe the
                # actual terminal geometry: one reserved top row on each tab.
                panes = [p for p in terminal.terminals() if not p["is_floating"]]
                top_rows = {}
                for pane in panes:
                    top_rows.setdefault(pane["tab_id"], []).append(pane["pane_y"])
                return all(t["tab_id"] in top_rows and min(top_rows[t["tab_id"]]) == 1
                           for t in terminal.tabs())

            terminal.until("first tab has a one-row top bar", top_bars)
            terminal.prefix(b"r")
            terminal.send(b"work\r")
            terminal.until("rename tab", lambda: terminal.tabs()[0]["name"] == "work")
            terminal.prefix(b"v")
            terminal.until("vertical split", lambda: len(terminal.terminals()) == 2)
            panes = sorted(terminal.terminals(), key=lambda p: p["pane_x"])
            assert panes[0]["pane_x"] < panes[1]["pane_x"]
            assert {p["pane_cwd"] for p in panes} == {str(home)}, panes
            terminal.prefix(b"h")
            terminal.until("focus left", lambda: next(p for p in terminal.terminals()
                           if p["is_focused"])["id"] == panes[0]["id"])
            terminal.prefix(b"s")
            terminal.until("horizontal split", lambda: len(terminal.terminals()) == 3)
            terminals_before = {p["id"] for p in terminal.terminals()}
            terminal.prefix(b"z")
            terminal.until("zoom focused pane", lambda: any(p["is_fullscreen"]
                           for p in terminal.terminals()))
            terminal.prefix(b"z")
            terminal.until("restore split layout", lambda: not any(p["is_fullscreen"]
                           for p in terminal.terminals()))
            terminal.prefix(b" ")
            terminal.until("swap layout preserves top bar", top_bars)
            assert {p["id"] for p in terminal.terminals()} == terminals_before

            terminal.prefix(b"c")
            terminal.until("new tab", lambda: len(terminal.tabs()) == 2)
            terminal.until("new tab retains its top bar", top_bars)
            terminal.prefix(b"r")
            terminal.send(b"review [ready]\r")
            terminal.until("name second tab", lambda: any(t["name"] == "review [ready]"
                           and t["active"] for t in terminal.tabs()))
            terminal.prefix(b"\x10")
            terminal.until("Ctrl-p returns to last tab", lambda: any(t["name"] == "work"
                           and t["active"] for t in terminal.tabs()))

            terminal.prefix(b"\x06")
            terminal.until("fzf opens in floating pane", lambda: any(p["is_floating"]
                           for p in terminal.terminals()))
            terminal.send(b"review\r")
            terminal.until("picker focuses selected tab and closes itself", lambda:
                           any(t["name"] == "review [ready]" and t["active"] for t in terminal.tabs())
                           and not any(p["is_floating"] for p in terminal.terminals()))
            terminal.send(b"zellij_test_state=retained\r")

            second = Terminal(binary, env, second_name)
            clients.append(second)
            second.until("second session starts", lambda:
                         PROMPT in second.output and len(second.terminals()) == 1)
            second.prefix(b"d")
            second.until("second session is detached", lambda:
                         not second.action("list-clients").strip().splitlines()[1:])
            terminal.prefix(b"\x17")
            terminal.until("session picker opens", lambda: any(p["is_floating"]
                           for p in terminal.terminals()))
            terminal.send(second_name.encode() + b"\r")
            terminal.until("client switches to the selected live session", lambda:
                           bool(terminal.action("list-clients", session=second_name).strip().splitlines()[1:]))
            assert not any(p["is_floating"] for p in terminal.terminals())

            # Detaching must leave the original shell processes and layout alive.
            ids = {p["id"] for p in terminal.terminals()}
            terminal.prefix(b"d")
            restored = Terminal(binary, env, name)
            clients.append(restored)
            restored.until("reattach preserves original panes", lambda:
                           PROMPT in restored.output
                           and {p["id"] for p in restored.terminals()} == ids)
            assert len(restored.tabs()) == 2
            restored.prefix(b"2")
            restored.send(b'printf "%s" "$zellij_test_state" > "$HOME/retained-state"\r')
            restored.until("the original shell's memory survives detach", lambda:
                           (home / "retained-state").exists()
                           and (home / "retained-state").read_text() == "retained")
            print("PASS: installed Zellij preserves prefix navigation, splits, top bars, fuzzy selection, and detached sessions.")
        finally:
            for session in (name, second_name):
                subprocess.run([binary, "kill-session", session], env=env,
                               capture_output=True, timeout=5)
            for client in clients:
                client.close()


if __name__ == "__main__":
    main()
