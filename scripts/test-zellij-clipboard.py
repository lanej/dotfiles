#!/usr/bin/env python3
"""Exercise installed scrollback selection, OSC 52 copy and targeted paste.

Requires Neovim >=0.10, Zellij 0.45.1 and the local status plugin toolchain.
The PTY checks actual OSC 52 contents; it does not emulate a desktop clipboard.
"""

import base64
import importlib
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time


workflow = importlib.import_module("test-zellij")
ROOT, Terminal, PROMPT = workflow.ROOT, workflow.Terminal, workflow.PROMPT


def main():
    for command in ("zellij", "nvim", "cargo"):
        assert shutil.which(command), f"Install {command} before testing clipboard support"
    with tempfile.TemporaryDirectory(prefix="zj-copy-", dir="/tmp") as directory:
        work = Path(directory).resolve()
        home, runtime, temporary = work / "home", work / "run", work / "tmp"
        for path in (home, runtime, temporary):
            path.mkdir(mode=0o700)
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh", "PS1": PROMPT.decode(),
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(work / "cache"), "XDG_DATA_HOME": str(work / "data"),
               "XDG_STATE_HOME": str(work / "state"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temporary),
               "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"],
               "NVIM_APPNAME": "clipboard-check", "CLIPBOARD_NVIM_SOCKET": str(work / "nvim.sock")}
        workflow.preserve_rust_homes(env)
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "NVIM", "NVIM_LISTEN_ADDRESS",
                    "ENV", "BASH_ENV", "TERM_PROGRAM"):
            env.pop(key, None)
        subprocess.run(["make", "--no-print-directory", "zellij", "vim-config"],
                       cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        # Live reload must only edit this private install, not make's symlink
        # into the checked-in configuration.
        config = home / ".config/zellij/config.kdl"
        config.unlink()
        shutil.copyfile(ROOT / "zellij/config.kdl", config)
        # Keep one obsolete URL key for the installed rejection check.
        config.write_text(config.read_text().replace("    tmux {\n", '''    tmux {
        bind "q" {
            MessagePlugin "file:~/.config/zellij/plugins/lane-status.wasm" {
                name "clipboard-paste"
            }
            SwitchToMode "Locked"
        }
''', 1))
        init = home / ".config/clipboard-check/init.lua"
        init.parent.mkdir()
        init.write_text('''
vim.opt.runtimepath:prepend(vim.env.HOME .. "/.config/nvim")
vim.opt.swapfile = false
vim.opt.shadafile = "NONE"
require("zellij-clipboard").setup()
vim.fn.serverstart(vim.env.CLIPBOARD_NVIM_SOCKET)
''')
        source = work / "selection.txt"
        source.write_text("select α one   end\nselect β two   end\n")
        # Hold only the asynchronous read boundary. Copying and buffer reads
        # still use the installed helper; focus can change before it completes.
        delayed = work / "delayed"
        delayed.mkdir()
        started, release = work / "read-started", work / "read-release"
        installed = home / ".local/bin/zellij-clipboard"
        wrapper = delayed / "zellij-clipboard"
        wrapper.write_text(f'''#!{sys.executable}
import os, pathlib, sys, time
if sys.argv[1] == "read":
    pathlib.Path({str(started)!r}).touch()
    deadline = time.monotonic() + 10
    while not pathlib.Path({str(release)!r}).exists():
        if time.monotonic() > deadline:
            sys.exit("Timed out waiting for the clipboard workflow")
        time.sleep(0.01)
os.execv({str(installed)!r}, [{str(installed)!r}, *sys.argv[1:]])
''')
        wrapper.chmod(0o755)
        env["PATH"] = str(delayed) + os.pathsep + env["PATH"]
        name = "clipboard-" + work.name
        terminal = Terminal(shutil.which("zellij"), env, name)
        other = None
        try:
            terminal.grant_status_permissions()
            terminal.until("shell ready", lambda: PROMPT in terminal.output and len(terminal.terminals()) == 1)
            terminal.send((shlex.join(["cat", str(source)]) + "\r").encode())
            terminal.until("source text reaches scrollback", lambda: "select β two" in terminal.action("dump-screen"))
            terminal.prefix(b"e")
            terminal.until("installed scrollback editor", lambda: Path(env["CLIPBOARD_NVIM_SOCKET"]).exists())

            def buffer():
                return subprocess.check_output([str(installed), "read", "--session", name], env=env)

            def copied(text, after):
                matches = re.findall(rb"\x1b\]52;[cp];([A-Za-z0-9+/=]*)(?:\x07|\x1b\\)", terminal.output[after:])
                if not matches:
                    return False
                actual = base64.b64decode(matches[-1])
                assert actual == text, (actual, text)
                assert buffer() == text
                return True

            terminal.send("/^select α one\r0".encode())
            before = len(terminal.output)
            terminal.send("fαv4ly".encode())
            terminal.until("character selection copies Unicode", lambda: copied("α one".encode(), before))
            before = len(terminal.output)
            terminal.send(b"0Vjy")
            terminal.until("line selection keeps its final newline", lambda: copied(source.read_bytes(), before))
            before = len(terminal.output)
            terminal.send(b"07l\x16j7ly")
            block = "α one   \nβ two   ".encode()
            terminal.until("rectangle keeps columns and trailing spaces", lambda: copied(block, before))
            terminal.send(b":q!\r")
            terminal.until("scrollback editor closes", lambda: not Path(env["CLIPBOARD_NVIM_SOCKET"]).exists())

            receiver, received, ready = work / "receiver.py", work / "received", work / "ready"
            receiver.write_text('''
import os, pathlib, sys, termios, tty
original = termios.tcgetattr(0)
try:
    tty.setraw(0)
    sys.stdout.write("\\x1b[?2004hclipboard-receiver-ready")
    sys.stdout.flush()
    pathlib.Path(sys.argv[2]).touch()
    data = b""
    while b"\\x04" not in data:
        data += os.read(0, 4096)
        pathlib.Path(sys.argv[1]).write_bytes(data)
finally:
    termios.tcsetattr(0, termios.TCSADRAIN, original)
''')
            other_received, other_ready = work / "other-received", work / "other-ready"
            terminal.send((shlex.join([sys.executable, str(receiver), str(other_received), str(other_ready)]) + "\r").encode())
            terminal.until("non-requesting pane ready", other_ready.exists)
            original_pane = next(p["id"] for p in terminal.terminals())
            other = Terminal(shutil.which("zellij"), env, name)
            other.until("second client attaches to its own focus", lambda:
                        b"clipboard-receiver-ready" in other.output)

            def client_panes():
                return [row.split()[1] for row in terminal.action("list-clients").splitlines()[1:]
                        if row.strip()]

            def until(description, predicate):
                def observed():
                    # A full client PTY can block native renders to both clients.
                    other.drain(0.02)
                    return predicate()
                return terminal.until(description, observed)

            terminal.prefix(b"c")
            until("destination tab ready", lambda: len(terminal.tabs()) == 2)
            terminal.prefix(b"r")
            terminal.send(b"copy-destination\r")
            until("destination tab named", lambda:
                  any(t["name"] == "copy-destination" for t in terminal.tabs()))
            terminal.send((shlex.join([sys.executable, str(receiver), str(received), str(ready)]) + "\r").encode())
            until("destination accepts bracketed paste", ready.exists)
            active_tab = next(t["tab_id"] for t in terminal.tabs() if t["name"] == "copy-destination")
            destination = next(p["id"] for p in terminal.terminals()
                               if p["tab_id"] == active_tab)
            assert sorted(client_panes()) == sorted([f"terminal_{original_pane}", f"terminal_{destination}"])
            terminal.prefix(b"Z")
            until("paste remains available without the bar", lambda:
                  any(p["id"] == destination and p["is_fullscreen"] for p in terminal.terminals()))
            terminal.prefix(b"q")
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                terminal.drain(); other.drain()
            assert not started.exists(), "Obsolete URL binding started a paste"
            assert not received.exists() and not other_received.exists()
            terminal.prefix(b"p")
            until("paste captured its destination", started.exists)
            terminal.prefix(b"0")
            release.touch()
            until("paste reaches original pane", lambda: received.exists() and received.read_bytes().endswith(b"\x1b[201~"))
            # Observe both clients long enough to catch an unintended second
            # asynchronous reader before ending the non-requesting receiver.
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                terminal.drain(); other.drain()
            terminal.action("write", "--pane-id", f"terminal_{original_pane}", "4")
            until("non-requesting pane stayed untouched", lambda:
                  other_received.exists() and other_received.read_bytes().endswith(b"\x04"))
            assert other_received.read_bytes() == b"\x04", other_received.read_bytes()
            expected = b"\x1b[200~" + block + b"\x1b[201~"
            assert received.read_bytes() == expected, received.read_bytes()
            assert client_panes() == [f"terminal_{original_pane}"] * 2

            # Reload the file with both clients away from the receiver's tab.
            # Removing frames provides an observable reload acknowledgement.
            terminal.prefix(b"1")
            other.prefix(b"1")
            assert client_panes() == [f"terminal_{destination}"] * 2
            terminal.prefix(b"Z")
            config.write_text(config.read_text().replace("pane_frames true", "pane_frames false"))
            until("disk config reload removes frames", lambda:
                  any(p["id"] == destination and p["pane_content_y"] == p["pane_y"]
                      for p in terminal.terminals()))
            other.prefix(b"p")
            until("second client's paste survives inactive-receiver reload", lambda:
                  received.read_bytes().count(b"\x1b[200~") >= 2)
            assert received.read_bytes() == expected * 2, received.read_bytes()

            # The hidden receiver must keep one stable native identity when
            # its containing tab closes. Both clients then focus one pane, so
            # another paste also detects duplicate delivery.
            def clipboard_receivers():
                return [p["id"] for p in terminal.panes() if p["is_plugin"] and p["is_suppressed"]
                        and p.get("plugin_url", "").endswith("/lane-status.wasm")]

            receivers = clipboard_receivers()
            assert len(receivers) == 1, receivers
            clipboard_receiver = receivers[0]
            terminal.prefix(b"0")
            until("first client returns to receiver's tab", lambda:
                  sorted(client_panes()) == sorted([f"terminal_{original_pane}", f"terminal_{destination}"]))
            terminal.prefix(b"x")
            until("receiver plugin's tab closes", lambda: len(terminal.tabs()) == 1)
            assert clipboard_receivers() == [clipboard_receiver], clipboard_receivers()
            until("surviving bar renders the new tab position", lambda:
                  b"0:copy-destination" in terminal.output)
            terminal.prefix(b"Z")
            terminal.prefix(b"p")
            until("paste survives receiver replacement", lambda:
                  received.read_bytes().count(b"\x1b[200~") >= 3)
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                terminal.drain(); other.drain()

            # Errors from the hidden receiver belong in this client's visible
            # bar and must not send any bytes to the waiting application.
            terminal.prefix(b"Z")
            until("destination leaves fullscreen", lambda:
                  any(p["id"] == destination and not p["is_fullscreen"] for p in terminal.terminals()))
            subprocess.run([str(installed), "clear", "--session", name], env=env, check=True)
            before, other_before = len(terminal.output), len(other.output)
            terminal.prefix(b"p")
            notice = b"paste: zellij-clipboard: The session buffer is empty"
            until("missing buffer notice reaches requesting client's bar", lambda:
                  notice in terminal.output[before:])
            other.drain()
            assert notice not in other.output[other_before:]
            assert received.read_bytes() == expected * 3, received.read_bytes()
            terminal.action("write", "--pane-id", f"terminal_{destination}", "4")
            until("destination finished reading", lambda: received.read_bytes().endswith(b"\x04"))
            assert received.read_bytes() == expected * 3 + b"\x04", received.read_bytes()
            assert not any(p["is_floating"] for p in terminal.panes())
            print("Installed scrollback copy and client-scoped paste passed: another client's pane stays untouched, "
                  "focus changes preserve the target, disk reload and tab closure preserve the single hidden "
                  "receiver, missing-buffer notices stay client-scoped, and obsolete URL messages do not paste.")
        finally:
            subprocess.run([shutil.which("zellij"), "kill-session", name], env=env, capture_output=True)
            if other is not None:
                other.close()
            terminal.close()


if __name__ == "__main__":
    main()
