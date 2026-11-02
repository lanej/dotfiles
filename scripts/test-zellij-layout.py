#!/usr/bin/env python3
"""Observe the native equalize layout, pane geometry, and surviving shell state."""

import fcntl
import json
import os
from pathlib import Path
import runpy
import shutil
import struct
import subprocess
import tempfile
import termios


ROOT = Path(__file__).resolve().parent.parent
Terminal = runpy.run_path(str(ROOT / "scripts/test-zellij.py"))["Terminal"]


def geometry(panes):
    return [(p["id"], p["pane_x"], p["pane_y"], p["pane_columns"],
             p["pane_rows"], p["is_focused"])
            for p in sorted(panes, key=lambda p: (p["pane_x"], p["pane_y"]))]


def main():
    binary = shutil.which("zellij")
    assert binary, "Install Zellij >=0.45.1 before make test-zellij-layout"
    with tempfile.TemporaryDirectory(prefix="zj-layout-", dir="/tmp") as directory:
        temporary = Path(directory).resolve()
        home = temporary / "home"
        home.mkdir()
        runtime = temporary / "run"
        runtime.mkdir(mode=0o700)
        temp_files = temporary / "tmp"
        temp_files.mkdir(mode=0o700)
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh", "PS1": "zellij-ready> ",
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(temporary / "cache"),
               "XDG_DATA_HOME": str(temporary / "data"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temp_files),
               "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"]}
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV"):
            env.pop(key, None)
        subprocess.run(["make", "--no-print-directory", "zellij"], cwd=ROOT, env=env,
                       check=True, capture_output=True, text=True)
        subprocess.run([binary, "setup", "--check"], env=env, check=True,
                       capture_output=True, text=True)
        name = "layout-" + temporary.name
        terminal = Terminal(binary, env, name)
        try:
            terminal.until("first shell starts", lambda:
                           b"zellij-ready> " in terminal.output and len(terminal.terminals()) == 1)
            terminal.prefix(b"v")
            terminal.until("right shell", lambda: len(terminal.terminals()) == 2)
            # Explicit command/cwd launch metadata must not cause a new shell
            # during equalization. This is where layout override is unsafe.
            terminal.action("new-pane", "--direction", "down", "--cwd", str(home), "--", "/bin/sh")
            terminal.until("explicit-command lower shell", lambda: len(terminal.terminals()) == 3)
            original = geometry(terminal.terminals())
            original_ids = [p[0] for p in original]
            initial_pids = {}
            for pane_id in original_ids:
                if not next(p for p in terminal.terminals() if p["id"] == pane_id)["is_focused"]:
                    terminal.action("focus-pane-id", f"terminal_{pane_id}")
                terminal.send((f"token=keep-{pane_id}; printf '%s\\n' \"$$\" > \"$HOME/pid-{pane_id}\"; "
                               f"printf 'scrollback-{pane_id}\\n'; "
                               "i=0; while [ \"$i\" -lt 40 ]; do printf 'history line\\n'; i=$((i+1)); done\r").encode())
                path = home / f"pid-{pane_id}"
                terminal.until("record original shell PID", path.exists)
                initial_pids[pane_id] = path.read_text().strip()
            focused_id = original_ids[-1]
            terminal.action("resize", "increase", "left", "--pane-id", f"terminal_{focused_id}")
            terminal.action("resize", "increase", "up", "--pane-id", f"terminal_{focused_id}")
            assert geometry(terminal.terminals()) != original

            # Use the user's native cycle control. Stable Zellij cannot select
            # an arbitrary named swap layout directly, so '=' stays unbound.
            for _ in range(5):
                terminal.prefix(b" ")
                if json.loads(terminal.action("current-tab-info", "--json"))["active_swap_layout_name"] == "equalize":
                    break
            else:
                raise AssertionError("Native layout cycle did not offer equalize")
            def sized(expected):
                panes = geometry(terminal.terminals())
                return (len(panes) == 3 and {p[0] for p in panes} == set(original_ids)
                        and [p[1:5] for p in panes] == expected
                        and [p[0] for p in panes if p[5]] == [focused_id])
            terminal.until("native equalize keeps original panes and focus", lambda: sized([
                (0, 1, 60, 31), (60, 1, 60, 16), (60, 17, 60, 15),
            ]))
            # Native percentage constraints keep all panes inside a smaller
            # terminal; fixed-cell overrides did not survive this transition.
            fcntl.ioctl(terminal.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
            terminal.until("equalized panes adapt to a narrower terminal", lambda: sized([
                (0, 1, 40, 23), (40, 1, 40, 12), (40, 13, 40, 11),
            ]))

            for pane_id in original_ids:
                if not next(p for p in terminal.terminals() if p["id"] == pane_id)["is_focused"]:
                    terminal.action("focus-pane-id", f"terminal_{pane_id}")
                terminal.send((f"printf '%s|%s\\n' \"$token\" \"$$\" > \"$HOME/proof-{pane_id}\"\r").encode())
                proof = home / f"proof-{pane_id}"
                terminal.until("original shell state survives", lambda: proof.exists() and
                               proof.read_text().strip() == f"keep-{pane_id}|{initial_pids[pane_id]}")
                assert f"scrollback-{pane_id}" in terminal.action(
                    "dump-screen", "--full", "--pane-id", str(pane_id))
            print("Equalize: original pane IDs, focus, shell PIDs, memory and scrollback retained; "
                  "native layout geometry fits a 120→80 column terminal resize.")
        finally:
            subprocess.run([binary, "kill-session", name], env=env, capture_output=True, timeout=5)
            terminal.close()


if __name__ == "__main__":
    main()
