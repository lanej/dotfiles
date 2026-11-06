#!/usr/bin/env python3
"""Exercise installed scrollback selection, OSC 52 copy and targeted paste.

Requires Neovim >=0.10, Git, the pinned Zellij 0.46 runtime and the local status plugin toolchain.
Fetches only Baleia at the revision in nvim/lazy-lock.json.
The PTY checks actual OSC 52 contents; it does not emulate a desktop clipboard.
"""

import base64
import importlib
import json
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
    for command in ("zellij", "nvim", "cargo", "git"):
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
        subprocess.run(["make", "--no-print-directory", "zellij-status", "zellij", "vim-config"],
                       cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        # Use the real locked renderer without bootstrapping unrelated plugins.
        baleia = work / "baleia.nvim"
        revision = json.loads((ROOT / "nvim/lazy-lock.json").read_text())["baleia.nvim"]["commit"]
        subprocess.run(["git", "init", "--quiet", str(baleia)], check=True)
        subprocess.run(["git", "-C", str(baleia), "fetch", "--quiet", "--depth=1",
                        "https://github.com/m00qek/baleia.nvim.git", revision], check=True)
        subprocess.run(["git", "-C", str(baleia), "checkout", "--quiet", "--detach", "FETCH_HEAD"], check=True)
        env["CLIPBOARD_BALEIA"] = str(baleia)
        init = home / ".config/clipboard-check/init.lua"
        init.parent.mkdir()
        init.write_text('''
vim.opt.runtimepath:prepend(vim.env.HOME .. "/.config/nvim")
vim.opt.swapfile = false
vim.opt.shadafile = "NONE"
vim.opt.runtimepath:append(vim.env.CLIPBOARD_BALEIA)
require("zellij-scrollback").register_filetype()
require("zellij-scrollback").setup()
require("zellij-clipboard").setup()
vim.fn.serverstart(vim.env.CLIPBOARD_NVIM_SOCKET)
''')
        source = work / "selection.txt"
        source.write_text("\x1b[31mselect α one   end\x1b[0m\n\x1b[32mselect β two   end\x1b[0m\n")
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

            def rendered():
                expression = "json_encode([&filetype, getline(1, '$')])"
                result = subprocess.check_output(
                    ["nvim", "--server", env["CLIPBOARD_NVIM_SOCKET"], "--remote-expr", expression], env=env)
                filetype, lines = json.loads(result)
                return (filetype == "zellij-scrollback" and "select α one   end" in lines
                        and "select β two   end" in lines and not any("\x1b" in line for line in lines))

            # Baleia renders asynchronously; the RPC socket alone is not readiness.
            terminal.until("production filetype and ANSI rendering", rendered)
            terminal.send("/^select α one\r0".encode())
            before = len(terminal.output)
            terminal.send(b"07l\x16j7ly")
            block = "α one   \nβ two   ".encode()
            terminal.until("rendered rectangle copies Unicode and trailing spaces", lambda: copied(block, before))
            terminal.send(b":q\r")
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

            terminal.action("write", "--pane-id", f"terminal_{destination}", "4")
            until("destination finished reading", lambda: received.read_bytes().endswith(b"\x04"))
            assert received.read_bytes() == expected + b"\x04", received.read_bytes()
            print("Rendered scrollback copies Unicode and whitespace via OSC 52 and the session buffer; "
                  "one bracketed paste reaches the captured pane after focus changes, "
                  "leaving the other client's pane untouched.")
        finally:
            subprocess.run([shutil.which("zellij"), "kill-session", name], env=env, capture_output=True)
            if other is not None:
                other.close()
            terminal.close()


if __name__ == "__main__":
    main()
