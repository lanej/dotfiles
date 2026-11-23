#!/usr/bin/env python3
"""Exercise the installed tmux-style workflow through a real Zellij terminal.

Requires Zellij >=0.45.1 and fzf. Sessions, HOME and XDG directories are isolated;
only this check's named sessions are terminated. No user's shell files are read.
"""

import argparse
import fcntl
import json
import os
from pathlib import Path
import pty
import re
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


def preserve_rust_homes(env):
    # Installing the real status plugin still needs the caller's toolchain and
    # cache after application state moves into this workflow's private HOME.
    for key, default in (("CARGO_HOME", ".cargo"), ("RUSTUP_HOME", ".rustup")):
        env[key] = os.environ.get(key, str(Path.home() / default))


class Terminal:
    def __init__(self, binary, env, name, command=None, *, install_navigation=True, columns=120):
        self.binary, self.env, self.name = binary, env, name
        self.output = bytearray()
        config = Path(env["HOME"]) / ".config/zellij/config.kdl"
        for plugin in ("command-prompt", "copy-hop"):
            installed = Path(env["HOME"]) / f".local/share/zellij/plugins/{plugin}.wasm"
            if config.exists() and not installed.exists():
                # rationale(tests): Each detector loads only the optional plugin it exercises.
                contents = config.read_text()
                without_plugin = re.sub(rf"(?m)^\s*{re.escape(plugin)}\s*$", "", contents)
                if without_plugin != contents:
                    if config.is_symlink():
                        config.unlink()
                    config.write_text(without_plugin)
        if install_navigation:
            navigation = Path.home() / ".local/share/zellij/plugins/pane-navigation.wasm"
            assert navigation.exists(), "Install pane navigation with scripts/install-zellij-navigation.py"
            installed = Path(env["HOME"]) / ".local/share/zellij/plugins/pane-navigation.wasm"
            installed.parent.mkdir(parents=True, exist_ok=True)
            if not installed.exists():
                shutil.copyfile(navigation, installed)
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            # Set the slave's size before Zellij can query it. Doing this in the
            # parent after fork races the child's startup on a zero-sized PTY.
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 32, columns, 0, 0))
            os.chdir(env["HOME"])
            command = command or [binary, "attach", "--create", name]
            os.execvpe(command[0], command, env)
        # A later PTY child must not keep earlier masters open across exec.
        os.set_inheritable(self.fd, False)

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

    def settle_ordinary_navigation(self):
        """Allow the three-second discovery grace for a known ordinary attachment."""
        self.drain(3.1)

    def prefix(self, key):
        self.send(b"\x06" + key)

    def grant_status_permissions(self):
        if (Path(self.env["HOME"]) / ".config/zellij/config.kdl").resolve().name == "config-legacy.kdl":
            return
        # Exercise the actual first-use dialog instead of injecting a cached
        # grant. Further sessions in this private HOME share the saved grant.
        self.until("status permission request or remembered grant", lambda:
                   b"(y/n)" in self.output.lower()
                   or re.search(rb" \d+:[^\s\x1b]", self.output))
        if b"(y/n)" in self.output.lower():
            self.prefix(b"k")
            self.send(b"y")

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
                error = subprocess.CalledProcessError(
                    command.returncode, command.args, stdout, stderr
                )
                error.add_note(f"Zellij stdout: {stdout}\nZellij stderr: {stderr}")
                raise error
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
        try:
            details.extend(self.startup_diagnostics())
        except Exception as error:
            # Diagnostics must never replace the workflow's original failure.
            details.append(f"Could not collect startup diagnostics: {error}")
        output = self.output[-4000:].decode(errors="replace")
        details.append(f"Terminal output:\n{output or '<empty>'}")
        raise AssertionError("\n".join(details))

    def startup_diagnostics(self):
        details = []
        sample_pids = set()
        artifacts = None
        artifact_root = os.environ.get("ZELLIJ_TEST_ARTIFACTS")
        if artifact_root:
            try:
                Path(artifact_root).mkdir(parents=True, exist_ok=True)
                artifacts = Path(tempfile.mkdtemp(prefix="startup-", dir=artifact_root))
                (artifacts / "terminal-output.bin").write_bytes(self.output)
                (artifacts / "context.json").write_text(json.dumps({
                    "session": self.name, "client_pid": self.pid,
                    "executable": self.binary, "captured_at": time.time(),
                }, indent=2) + "\n")
                details.append(f"Complete failure artifacts: {artifacts}")
            except OSError as error:
                details.append(f"Could not preserve failure artifacts: {error}")
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
            snapshot = ("Process snapshot (PID PPID STAT COMMAND):\n" +
                        "\n".join(" ".join(row) for row in related))
            details.append(snapshot)
            sample_pids = {row[0] for row in related
                           if row[0] == str(self.pid) or "--server " in row[3]}
            if artifacts:
                (artifacts / "processes.txt").write_text(snapshot + "\n")
            if process.stderr:
                details.append(process.stderr)
        except (OSError, subprocess.TimeoutExpired) as error:
            details.append(f"Could not inspect test processes: {error}")
        if os.uname().sysname == "Darwin" and shutil.which("sample"):
            for pid in sorted(sample_pids):
                sample_path = (artifacts or Path(self.env["HOME"])) / f"process-{pid}.sample"
                try:
                    sample = subprocess.run(
                        ["sample", pid, "1", "1", "-file", str(sample_path)],
                        capture_output=True, text=True, timeout=5,
                    )
                    details.append(f"Process sample {pid}:\n{sample.stdout}{sample.stderr}")
                    if sample_path.exists():
                        if artifacts:
                            details.append(f"Complete process sample: {sample_path}")
                        else:
                            details.append(sample_path.read_text(errors="replace")[:16000])
                except (OSError, subprocess.TimeoutExpired) as error:
                    details.append(f"Could not sample process {pid}: {error}")
        log = Path(self.env["TMPDIR"]) / f"zellij-{os.getuid()}" / "zellij-log" / "zellij.log"
        try:
            if artifacts:
                shutil.copyfile(log, artifacts / "zellij.log")
            with log.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                handle.seek(max(0, handle.tell() - 16000))
                details.append("Zellij log:\n" + handle.read(16000).decode(errors="replace"))
        except OSError as error:
            details.append(f"Could not read isolated Zellij log: {error}")
        if artifacts:
            # macOS uses Library/Caches while Linux uses XDG_CACHE_HOME. Both
            # locations belong to this test's private home, and the session name
            # excludes other sessions created by the same workflow.
            cache_roots = (Path(self.env["XDG_CACHE_HOME"]),
                           Path(self.env["HOME"]) / "Library" / "Caches")
            metadata_count = 0
            for cache in cache_roots:
                for metadata in cache.glob(
                        f"*/contract_version_*/session_info/{self.name}/session-metadata.kdl"):
                    try:
                        shutil.copyfile(metadata, artifacts / f"session-metadata-{metadata_count}.kdl")
                        metadata_count += 1
                    except OSError as error:
                        details.append(f"Could not preserve session metadata: {error}")
            details.append(f"Saved {metadata_count} isolated session metadata file(s)")
            try:
                (artifacts / "diagnostics.txt").write_text("\n".join(details) + "\n")
            except OSError as error:
                details.append(f"Could not preserve diagnostic summary: {error}")
        return details

    def close(self):
        os.close(self.fd)
        for termination in (None, signal.SIGTERM):
            if termination is not None:
                os.kill(self.pid, termination)
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                try:
                    waited, _ = os.waitpid(self.pid, os.WNOHANG)
                except ChildProcessError:
                    return
                if waited:
                    return
                time.sleep(0.05)
        os.kill(self.pid, signal.SIGKILL)
        os.waitpid(self.pid, 0)
