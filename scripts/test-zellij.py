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
        command_prompt = Path(env["HOME"]) / ".local/share/zellij/plugins/command-prompt.wasm"
        config = Path(env["HOME"]) / ".config/zellij/config.kdl"
        if config.exists() and not command_prompt.exists():
            # Other feature detectors need neither this optional plugin's build
            # nor its consent dialog. Keep the real binding, but omit its startup
            # node in their private config. Its own detector installs and tests it.
            contents = config.read_text()
            without_prompt = re.sub(r"(?m)^\s*command-prompt\s*$", "", contents)
            if without_prompt != contents:
                if config.is_symlink():
                    config.unlink()
                config.write_text(without_prompt)
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

    def prefix(self, key):
        self.send(b"\x06" + key)

    def grant_status_permissions(self):
        if (Path(self.env["HOME"]) / ".config/zellij/config.kdl").resolve().name == "config-legacy.kdl":
            return
        # Exercise the actual first-use dialog instead of injecting a cached
        # grant. Further sessions in this private HOME share the saved grant.
        self.until("status permission request or remembered grant", lambda:
                   b"(y/n)" in self.output.lower()
                   or re.search(rb"!\d+ \xe2\x97\x8f\d+", self.output))
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


def check_move_picker(terminal, home, clients):
    terminal.prefix(b"v")
    terminal.until("split before moving", lambda: len(terminal.terminals()) == 2)
    source = next(p for p in terminal.terminals() if p["is_focused"])
    source_id, source_tab = source["id"], source["tab_id"]
    pane_target = f"terminal_{source_id}"
    terminal.until("source shell ready", lambda: PROMPT.decode().strip() in
                   terminal.action("dump-screen", "--pane-id", pane_target))
    terminal.send(b"move_state=retained; printf '%s' \"$$\" > \"$HOME/move-pid\"; mkdir -p work; cd work; printf 'MOVE-HISTORY\\n'; seq 1 80\r")
    terminal.until("source process and scrollback ready", lambda:
                   (home / "move-pid").exists() and "80\n" in
                   terminal.action("dump-screen", "--pane-id", pane_target))
    pid = (home / "move-pid").read_text()

    def source_pane():
        return next(p for p in terminal.terminals() if p["id"] == source_id)

    def popup():
        return next((p for p in terminal.terminals() if p["is_floating"] and
                     p["id"] != source_id), None)

    def picker_screen():
        pane = popup()
        return terminal.action("dump-screen", "--pane-id", f"terminal_{pane['id']}") if pane else ""

    def open_picker():
        terminal.prefix(b"m")
        terminal.until("prefix m opens the destination menu", lambda:
                       "Move pane to tab" in picker_screen() and "New Tab" in picker_screen())

    # Cancellation must leave the original pane, layout and live shell alone.
    original_ids = {p["id"] for p in terminal.terminals()}
    open_picker()
    terminal.send(b"\x1b")
    terminal.until("cancel closes picker", lambda: popup() is None)
    assert {p["id"] for p in terminal.terminals()} == original_ids
    assert source_pane()["tab_id"] == source_tab and len(terminal.tabs()) == 1

    open_picker()
    # A second attached client's different focus cannot select the source.
    other = Terminal(terminal.binary, terminal.env, terminal.name)
    clients.append(other)
    other.until("second client attached", lambda: PROMPT in other.output)
    other.prefix(b"c")
    terminal.until("second client opens its own tab", lambda: len(terminal.tabs()) == 2)
    bystander_ids = {p["id"] for p in terminal.terminals()} - {popup()["id"]}
    terminal.send(b"\r")
    terminal.until("New Tab transfers the original pane", lambda:
                   source_pane()["tab_id"] != source_tab and len(terminal.tabs()) == 3 and popup() is None)
    assert {p["id"] for p in terminal.terminals()} == bystander_ids
    assert "MOVE-HISTORY\n" in terminal.action("dump-screen", "--full", "--pane-id", pane_target)
    assert source_pane()["pane_cwd"] == str(home / "work")
    terminal.send(b"printf '%s:%s' \"$$\" \"$move_state\" > \"$HOME/move-after\"\r")
    terminal.until("live shell identity and memory survive", lambda:
                   (home / "move-after").exists() and
                   (home / "move-after").read_text() == pid + ":retained")
    other.prefix(b"d")
    other.until("other client detaches", lambda:
                len(terminal.action("list-clients").splitlines()) == 2)

    # Destination IDs, rather than names or positions, identify the tab.
    target_name = "destination [literal]; $(false)"
    terminal.action("rename-tab", target_name, "--tab-id", str(source_tab))
    terminal.action("move-tab", "right", "--tab-id", str(source_tab))
    assert next(t for t in terminal.tabs() if t["tab_id"] == source_tab)["position"] != source_tab
    open_picker()
    terminal.send(b"destination")
    terminal.until("destination filtered", lambda: "1/4" in picker_screen())
    terminal.send(b"\r")
    terminal.until("existing tab receives original pane", lambda:
                   source_pane()["tab_id"] == source_tab and popup() is None)
    assert "MOVE-HISTORY\n" in terminal.action("dump-screen", "--full", "--pane-id", pane_target)
    assert source_pane()["id"] == source_id
    assert {p["id"] for p in terminal.terminals()} == bystander_ids
    assert next(t for t in terminal.tabs() if t["tab_id"] == source_tab)["name"] == target_name
    terminal.send(b"printf '%s:%s' \"$$\" \"$move_state\" > \"$HOME/move-final\"\r")
    terminal.until("existing-tab transfer preserves process", lambda:
                   (home / "move-final").exists() and
                   (home / "move-final").read_text() == pid + ":retained")
    open_picker()
    terminal.send(b"destination")
    terminal.until("current tab filtered", lambda: "1/" in picker_screen())
    terminal.send(b"\r")
    terminal.until("current tab selection closes picker", lambda: popup() is None)
    assert source_pane()["tab_id"] == source_tab
    # A single working pane can move too; the popup is not the source pane.
    for pane in terminal.terminals():
        if pane["tab_id"] == source_tab and pane["id"] != source_id:
            terminal.action("close-pane", "--pane-id", f"terminal_{pane['id']}")
    open_picker()
    terminal.send(b"\r")
    terminal.until("single working pane moves to New Tab", lambda:
                   source_pane()["tab_id"] != source_tab and popup() is None)
    source_tab = source_pane()["tab_id"]
    assert "MOVE-HISTORY\n" in terminal.action("dump-screen", "--full", "--pane-id", pane_target)

    terminal.action("new-tab", "--name", "stale destination", "--no-focus")
    stale_tab = next(t["tab_id"] for t in terminal.tabs() if t["name"] == "stale destination")
    open_picker()
    terminal.send(b"stale")
    terminal.until("stale destination selected", lambda: "1/" in picker_screen())
    terminal.action("close-tab", "--tab-id", str(stale_tab))
    terminal.send(b"\r")
    terminal.until("closed destination is rejected", lambda: "destination tab closed" in picker_screen())
    assert source_pane()["tab_id"] == source_tab
    terminal.send(b"\r")
    terminal.until("error popup closes", lambda: popup() is None)

    terminal.action("new-tab", "--name", "high-ID destination", "--no-focus")
    target = next(t for t in terminal.tabs() if t["name"] == "high-ID destination")
    assert target["tab_id"] >= len(terminal.tabs())
    open_picker()
    terminal.send(b"high-ID")
    terminal.until("high-ID destination selected", lambda: "1/" in picker_screen())
    terminal.send(b"\r")
    terminal.until("gapped ID destination receives the live pane", lambda:
                   source_pane()["tab_id"] == target["tab_id"] and popup() is None)
    terminal.send(b"printf '%s:%s' \"$$\" \"$move_state\" > \"$HOME/move-gapped\"\r")
    terminal.until("gapped-ID transfer preserves process", lambda:
                   (home / "move-gapped").exists() and
                   (home / "move-gapped").read_text() == pid + ":retained")
    assert "MOVE-HISTORY\n" in terminal.action("dump-screen", "--full", "--pane-id", pane_target)
    print("PASS: Ctrl-f m moves the original live pane to new/existing tabs, cancels safely, and isolates clients.")


def check_tab_swap(terminal, home, clients):
    source = terminal.terminals()[0]
    source_tab = source["tab_id"]
    terminal.action("rename-tab", "swap source", "--tab-id", str(source_tab))
    terminal.action("new-tab", "--name", "discarded", "--no-focus")
    discarded = next(t["tab_id"] for t in terminal.tabs() if t["name"] == "discarded")
    for name in ("outside", "intervening", "swap destination"):
        terminal.action("new-tab", "--name", name, "--no-focus")
    terminal.action("close-tab", "--tab-id", str(discarded))
    terminal.until("four live named tabs", lambda: len(terminal.tabs()) == 4 and
                   len(terminal.terminals()) == 4)
    terminal.action("move-tab", "right", "--tab-id", str(source_tab))
    tabs = sorted(terminal.tabs(), key=lambda tab: tab["position"])
    assert [t["name"] for t in tabs] == ["outside", "swap source", "intervening", "swap destination"]
    assert all(t["tab_id"] != t["position"] for t in tabs)
    original_order = [t["tab_id"] for t in tabs]
    destination = tabs[-1]["tab_id"]
    original_panes = {p["id"]: p["tab_id"] for p in terminal.terminals()}
    # Record every original shell, not merely a restored-looking terminal title.
    for pane_id in original_panes:
        target = f"terminal_{pane_id}"
        terminal.until("tab shell ready", lambda: PROMPT.decode().strip() in
                       terminal.action("dump-screen", "--pane-id", target))
        terminal.action("write-chars", "--pane-id", target,
                        f"swap_state=retained; printf '%s' \"$$\" > \"$HOME/swap-before-{pane_id}\"\n")
    terminal.until("original shell PIDs saved", lambda:
                   all((home / f"swap-before-{pid}").exists() for pid in original_panes))
    other = Terminal(terminal.binary, terminal.env, terminal.name)
    clients.append(other)
    other.until("destination viewer attached", lambda: PROMPT in other.output)
    other.prefix(b"3")
    terminal.until("viewer selects destination", lambda:
                   len(next(t for t in terminal.tabs() if t["tab_id"] == destination)["other_focused_clients"]) == 1)

    def client_tabs():
        other.drain()
        return {client: tab["tab_id"] for tab in terminal.tabs()
                for client in tab["other_focused_clients"]}

    expected_clients = client_tabs()
    assert len(expected_clients) == 2 and set(expected_clients.values()) == {source_tab, destination}

    def popup():
        return next((p for p in terminal.terminals() if p["id"] not in original_panes), None)

    def picker_screen():
        pane = popup()
        return terminal.action("dump-screen", "--pane-id", f"terminal_{pane['id']}") if pane else ""

    def open_picker():
        terminal.prefix(b"W")
        terminal.until("Ctrl-f W shows fuzzy swap menu", lambda: "Swap tab positions" in picker_screen())

    def order():
        other.drain()
        return [t["tab_id"] for t in sorted(terminal.tabs(), key=lambda t: t["position"])]

    open_picker()
    terminal.send(b"\x1b")
    terminal.until("cancel closes helper", lambda: popup() is None)
    assert order() == original_order and client_tabs() == expected_clients
    open_picker()
    terminal.send(b"swap source")
    terminal.until("current tab filtered", lambda: "1/4" in picker_screen())
    terminal.send(b"\r")
    terminal.until("current selection closes helper", lambda: popup() is None)
    assert order() == original_order and client_tabs() == expected_clients
    open_picker()
    terminal.send(b"swap destination")
    terminal.until("nonadjacent destination filtered", lambda: "1/4" in picker_screen())
    terminal.send(b"\r")
    # Independent endpoint oracle: insertion would leave the intervening ID at
    # position one. Also catch a final go-to-tab that steals the second client.
    expected_order = [original_order[0], destination, original_order[2], source_tab]
    terminal.until("endpoint swap finishes and closes helper", lambda:
                   popup() is None and order() == expected_order)
    assert client_tabs() == expected_clients
    assert {p["id"]: p["tab_id"] for p in terminal.terminals()} == original_panes
    for pane_id in original_panes:
        terminal.action("write-chars", "--pane-id", f"terminal_{pane_id}",
                        f"printf '%s:%s' \"$$\" \"$swap_state\" > \"$HOME/swap-after-{pane_id}\"\n")
    terminal.until("all shell processes and private state survive", lambda:
                   all((home / f"swap-after-{pid}").exists() and
                       (home / f"swap-after-{pid}").read_text() ==
                       (home / f"swap-before-{pid}").read_text() + ":retained"
                       for pid in original_panes))
    # Input still belongs to the original requester and destination viewer.
    terminal.send(b"printf '%s' \"$$\" > \"$HOME/swap-requester\"\r")
    other.send(b"printf '%s' \"$$\" > \"$HOME/swap-viewer\"\r")
    destination_pane = next(pid for pid, tab in original_panes.items() if tab == destination)
    terminal.until("both clients retain their original live tabs", lambda:
                   (home / "swap-requester").exists() and (home / "swap-viewer").exists() and
                   (home / "swap-requester").read_text() == (home / f"swap-before-{source['id']}").read_text() and
                   (home / "swap-viewer").read_text() == (home / f"swap-before-{destination_pane}").read_text())
    print("PASS: Ctrl-f W exchanges endpoint positions, preserves intervening tabs, clients and live panes, and cancels safely.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--move-pane", action="store_true", help="Exercise only the pane destination picker")
    parser.add_argument("--swap-tab", action="store_true", help="Exercise only the fuzzy tab swap picker")
    args = parser.parse_args()
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
        preserve_rust_homes(env)
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "FZF_DEFAULT_OPTS",
                    "FZF_DEFAULT_OPTS_FILE", "FZF_DEFAULT_COMMAND", "ENV", "BASH_ENV"):
            env.pop(key, None)
        subprocess.run(["make", "--no-print-directory", "zellij-status", "zellij"], cwd=ROOT, env=env,
                       check=True, capture_output=True, text=True)
        subprocess.run([binary, "setup", "--check"], env=env, check=True,
                       capture_output=True, text=True)
        name = "work-" + temporary.name
        second_name = "other-" + temporary.name
        clients = []
        try:
            terminal = Terminal(binary, env, name)
            clients.append(terminal)
            terminal.grant_status_permissions()
            # CLI probes during first-client setup can race server initialization.
            # An actual rendered shell prompt proves that setup has completed.
            terminal.until("first shell starts", lambda:
                           PROMPT in terminal.output and len(terminal.terminals()) == 1)

            if args.swap_tab:
                check_tab_swap(terminal, home, clients)
                return

            if args.move_pane:
                check_move_picker(terminal, home, clients)
                return

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
            left_pane = next(p for p in terminal.terminals()
                             if p["tab_name"] == "review [ready]")
            terminal.until("left preview shell starts", lambda:
                           PROMPT.decode().strip() in terminal.action(
                               "dump-screen", "--pane-id", f"terminal_{left_pane['id']}"))
            terminal.send(b"printf '\\033[31mLEFT SCREEN: a long visible line that wraps in the miniature, with wrapped-end\\033[0m\\n'\r")
            terminal.until("left preview output is visible", lambda:
                           "wrapped-end\n" in terminal.action(
                               "dump-screen", "--pane-id", f"terminal_{left_pane['id']}"))
            terminal.prefix(b"v")
            terminal.until("preview tab has two panes", lambda:
                           len([p for p in terminal.terminals()
                                if p["tab_name"] == "review [ready]"]) == 2)
            right_pane = max(
                (p for p in terminal.terminals() if p["tab_name"] == "review [ready]"),
                key=lambda p: p["pane_x"],
            )
            terminal.until("right preview shell starts", lambda:
                           PROMPT.decode().strip() in terminal.action(
                               "dump-screen", "--pane-id", f"terminal_{right_pane['id']}"))
            terminal.send(b"printf '\\033[1;38;2;80;190;120;48;5;4mRIGHT SCREEN\\033[0m\\n'\r")
            terminal.until("right preview output is visible", lambda:
                           "RIGHT SCREEN\n" in terminal.action(
                               "dump-screen", "--pane-id", f"terminal_{right_pane['id']}"))
            terminal.prefix(b"\x10")
            terminal.until("Ctrl-p returns to last tab", lambda: any(t["name"] == "work"
                           and t["active"] for t in terminal.tabs()))

            def picker_screen(ansi=False):
                pane = next((p for p in terminal.terminals() if p["is_floating"]), None)
                return terminal.action("dump-screen", "--pane-id", f"terminal_{pane['id']}",
                                       *(["--ansi"] if ansi else [])) if pane else ""

            def picker_has_result(name):
                screen = picker_screen()
                return "1/2" in screen and name in screen

            terminal.prefix(b"\x06")
            # Pane creation precedes fzf entering raw mode. Wait for its actual
            # render so query keys cannot be consumed by the starting terminal.
            terminal.until("fzf opens in floating pane", lambda: "Tabs (attention" in picker_screen())
            terminal.send(b"review")
            # fzf filters asynchronously. Accept only after its visible result
            # count and selected row reflect the query, not the initial list.
            terminal.until("fzf filters to the requested tab", lambda:
                           picker_has_result("review [ready]"))

            preview_sample = {}

            def preview_shows_both_panes():
                screen = picker_screen()
                left_row = next((line for line in screen.splitlines() if "LEFT SCREEN:" in line), "")
                right_row = next((line for line in screen.splitlines() if "RIGHT SCREEN" in line), "")
                bottom_row = screen.rstrip().splitlines()[-1] if screen.strip() else ""
                left_start = bottom_row.find("└") + 1
                left_end = bottom_row.find("┘", left_start)
                left_text = "".join(line[left_start:left_end] for line in screen.splitlines())
                left_output = left_text.rpartition("LEFT SCREEN:")[2]
                colored = picker_screen(ansi=True)
                preview_sample.update(
                    screen=screen,
                    colored_lines=[line for line in colored.splitlines() if "SCREEN" in line],
                )
                attributes = r"(?:\x1b\[(?:[1-9]|2[1-9]|59)m)*"
                red = re.search(r"\x1b\[(?:31|38;5;1)m(?:\x1b\[49m)?"
                                + attributes + "LEFT SCREEN:", colored)
                green_on_blue = re.search(
                    r"\x1b\[38;2;80;190;120m\x1b\[(?:44|48;5;4)m"
                    + attributes + "RIGHT SCREEN", colored)
                return (left_row and right_row and "wrapped-end" in left_output
                        and left_row.index("LEFT SCREEN:") < right_row.index("RIGHT SCREEN")
                        and bottom_row.count("└") == 2 and bottom_row.count("┘") == 2
                        and red and green_on_blue)

            try:
                terminal.until("tab preview fits both panes in their split positions",
                               preview_shows_both_panes)
            except AssertionError as error:
                raise AssertionError(
                    f"{error}\nPicker snapshot:\n{preview_sample.get('screen', '')}"
                    f"\nColored preview lines:\n{preview_sample.get('colored_lines', [])!r}"
                ) from error
            terminal.send(b"\r")
            terminal.until("picker focuses selected tab and closes itself", lambda:
                           any(t["name"] == "review [ready]" and t["active"] for t in terminal.tabs())
                           and not any(p["is_floating"] for p in terminal.terminals()))
            terminal.send(b"zellij_test_state=retained\r")

            second = Terminal(binary, env, second_name)
            clients.append(second)
            second.until("second session starts", lambda:
                         PROMPT in second.output and len(second.terminals()) == 1)
            second.prefix(b"r")
            second.send(b"session-preview\r")
            second.until("name the session preview tab", lambda:
                         second.tabs()[0]["name"] == "session-preview")
            legacy = (home / ".config/zellij/config.kdl").resolve().name == "config-legacy.kdl"
            if not legacy:
                # Exercise the installed prefix, not a CLI substitute for F9.
                def manager_pane():
                    return next((p for p in terminal.panes()
                                 if p["plugin_url"] == "session-manager"
                                 and p["is_floating"] and p["is_focused"]
                                 and not p["is_suppressed"]), None)

                def manager_screen():
                    pane = manager_pane()
                    # Plugin grids are client-specific; an explicit pane-id dump
                    # has no client context and returns an empty plain-text grid.
                    return terminal.action("dump-screen") if pane else ""

                def manager_focused():
                    return second_name in manager_screen()

                terminal.prefix(b"I")
                terminal.until("prefix I opens the native inbox", manager_focused)
                source = second.terminals()[0]
                source_id = f"terminal_{source['id']}"
                terminal.send(second_name.encode() + b"\x1b[B")
                terminal.until("manager offers live preview typing", lambda:
                               "Alt ENTER" in manager_screen())
                terminal.send(b"\x1b\r")
                terminal.send(b"printf 'LIVE-VIEW-%s\\n' INPUT\r")
                terminal.until("live preview routes input to the selected shell", lambda:
                               "LIVE-VIEW-INPUT" in second.action("dump-screen", "--pane-id", source_id))
                terminal.send(b"\x1b\r")
                terminal.send(b"release-probe")
                terminal.until("Alt-Enter gives typing back to the manager", lambda:
                               "release-probe" in manager_screen())
                assert "release-probe" not in second.action("dump-screen", "--pane-id", source_id)
                terminal.send(b"\x03")

                terminal.prefix(b"I")
                terminal.until("prefix I closes the native inbox", lambda:
                               manager_pane() is None and
                               any(p["is_focused"] for p in terminal.terminals()))
                terminal.prefix(b"I")
                terminal.until("prefix I reopens the native inbox", manager_focused)
                terminal.send(b"\x1b")
                terminal.until("Escape returns from the native inbox", lambda:
                               manager_pane() is None and
                               any(p["is_focused"] for p in terminal.terminals()))

            second.prefix(b"d")
            second.until("second session is detached", lambda:
                         not second.action("list-clients").strip().splitlines()[1:])
            terminal.prefix(b"\x17")
            terminal.until("session picker opens", lambda: "Running sessions" in picker_screen())
            terminal.send(second_name.encode())
            terminal.until("fzf filters to the requested session", lambda:
                           picker_has_result(second_name))
            terminal.until("session preview lists the selected session's tab", lambda:
                           "session-preview" in picker_screen())
            terminal.send(b"\r")
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
            legacy = (home / ".config/zellij/config.kdl").resolve().name == "config-legacy.kdl"
            restored.prefix(b"2" if legacy else b"1")
            restored.until("return to the retained shell's tab", lambda:
                           any(t["name"] == "review [ready]" and t["active"] for t in restored.tabs()))
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
