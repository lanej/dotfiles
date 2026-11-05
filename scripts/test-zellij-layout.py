#!/usr/bin/env python3
"""Exercise balancing keys, native layout cycling, and surviving live panes."""

import fcntl
import json
import os
from pathlib import Path
import runpy
import shutil
import struct
import subprocess
import sys
import tempfile
import termios

ROOT = Path(__file__).resolve().parent.parent
workflow = runpy.run_path(str(ROOT / "scripts/test-zellij.py"))
Terminal = workflow["Terminal"]


def geometry(panes):
    return {p["id"]: tuple(p[k] for k in ("pane_x", "pane_y", "pane_columns", "pane_rows"))
            for p in panes}


def main():
    binary = shutil.which("zellij")
    assert binary, "Install the pinned Zellij runtime before make test-zellij-layout"
    with tempfile.TemporaryDirectory(prefix="zj-layout-", dir="/tmp") as directory:
        work = Path(directory).resolve()
        home, runtime, temporary = work / "home", work / "run", work / "tmp"
        for path in (home, runtime, temporary):
            path.mkdir(mode=0o700)
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh", "PS1": "zellij-ready> ",
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(work / "cache"), "XDG_DATA_HOME": str(work / "data"),
               "XDG_RUNTIME_DIR": str(runtime), "ZELLIJ_SOCKET_DIR": str(runtime),
               "TMPDIR": str(temporary), "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"]}
        workflow["preserve_rust_homes"](env)
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV"):
            env.pop(key, None)
        subprocess.run(["make", "--no-print-directory", "zellij-status", "zellij"], cwd=ROOT,
                       env=env, check=True, capture_output=True, text=True)
        subprocess.run([binary, "setup", "--check"], env=env, check=True, capture_output=True)
        # Observe completion of the real installed background entrypoint. No CLI is mocked.
        helper = home / ".local/bin/zellij-balance"
        helper.unlink()
        helper.write_text(f'''#!{sys.executable}
import json, os, subprocess, sys
from pathlib import Path
env = dict(os.environ)
if (Path.home() / 'without-jq').exists():
    env['PATH'] = str(Path.home() / 'no-jq-bin')
result = subprocess.run([{str(ROOT / 'bin/zellij-balance')!r}, *sys.argv[1:]], env=env, capture_output=True, text=True)
with (Path.home() / 'balance-results').open('a') as log:
    log.write(json.dumps(dict(origin=os.environ.get('ZELLIJ_ORIGIN_PANE_ID'), code=result.returncode, error=result.stderr)) + '\\n')
sys.exit(result.returncode)
''')
        helper.chmod(0o755)
        name = "balance-" + work.name
        terminal = Terminal(binary, env, name)
        other = None
        try:
            terminal.grant_status_permissions()
            terminal.until("shell ready", lambda: b"zellij-ready> " in terminal.output)
            for count in (2, 3):
                terminal.action("new-pane", "--direction", "right", "--cwd", str(home), "--", "/bin/sh")
                terminal.until("explicit-command columns", lambda: len(terminal.terminals()) == count)
            panes = terminal.terminals()
            ids = {p["id"] for p in panes}
            source_tab = panes[0]["tab_id"]
            left, middle, right = [p["id"] for p in sorted(panes, key=lambda p: p["pane_x"])]

            def current():
                return [p for p in terminal.panes() if not p["is_plugin"] and p["tab_id"] == source_tab]

            def rows():
                path = home / "balance-results"
                return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

            def invoke(key, client=None, failure=None):
                before = len(rows())
                (client or terminal).prefix(key)
                terminal.until("background balancing finishes", lambda: len(rows()) > before)
                result = rows()[-1]
                if failure:
                    assert result["code"] != 0 and failure in result["error"], result
                else:
                    assert result["code"] == 0, result
                assert {p["id"] for p in current()} == ids, ("balancing created or closed a pane", current())
                return result

            def resize(width):
                fcntl.ioctl(terminal.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 32, width, 0, 0))
                terminal.until("terminal resized", lambda: max(p["pane_x"] + p["pane_columns"] for p in current()) == width)

            def widths():
                return [p["pane_columns"] for p in sorted(current(), key=lambda p: p["pane_x"])]

            def content():
                return next(p["pane_content_columns"] for p in current() if p["id"] == left)

            no_jq = home / "no-jq-bin"
            no_jq.mkdir()
            for command in ("bash", "mktemp", "rm", "sleep", "zellij"):
                (no_jq / command).symlink_to(shutil.which(command))
            (home / "without-jq").touch()
            before = geometry(current())
            invoke(b"=", failure="jq is required")
            assert geometry(current()) == before
            (home / "without-jq").unlink()

            pids = {}
            for pid in ids:
                terminal.action("write-chars", "--pane-id", f"terminal_{pid}",
                                f'token=keep-{pid}; echo $$ > "$HOME/pid-{pid}"; echo HISTORY-{pid}; seq 1 70\r')
                terminal.until("original PID", lambda: (home / f"pid-{pid}").exists())
                pids[pid] = (home / f"pid-{pid}").read_text().strip()
            assert len(set(pids.values())) == 3
            assert widths() == [60, 30, 30]
            invoke(b"=")
            assert widths() == [42, 36, 42], widths()
            invoke(b"g")
            assert content() == 46, content()
            settled = geometry(current())
            invoke(b"G")  # One overshoot and reverse must preserve the nearest reachable state.
            assert geometry(current()) == settled

            resize(500)
            terminal.action("apply-tiled-swap-layout", "equalize")
            terminal.until("native preset", lambda: widths() == [250, 250, 250])
            settled = geometry(current())
            assert content() >= 120
            invoke(b"g")
            assert geometry(current()) == settled, "ordinary g ignored its content-width guard"
            invoke(b"G")
            assert content() == 173, content()
            # Here 188 is closer to 180 than 166, but the cap must win.
            resize(480)
            terminal.action("apply-tiled-swap-layout", "equalize")
            terminal.until("reset halves", lambda: content() == 238)
            invoke(b"G")
            assert content() == 166, content()

            # A target of 179 must also reject a nearer native step above 180.
            resize(469)
            terminal.action("apply-tiled-swap-layout", "equalize")
            terminal.until("below-threshold halves", lambda: content() in (232, 233))
            invoke(b"G")
            assert content() <= 180, content()

            resize(240)
            terminal.action("apply-tiled-swap-layout", "equalize")
            terminal.until("nested rows", lambda: widths() == [120, 120, 120])
            top = min((p for p in current() if p["id"] != left), key=lambda p: p["pane_y"])["id"]
            for _ in range(2):
                terminal.action("resize", "increase", "down", "--pane-id", f"terminal_{top}")
            fixed = geometry(current())[left]
            invoke(b"=")  # invoking pane remains the right-hand shell
            assert geometry(current())[left] == fixed
            assert sorted(p["pane_rows"] for p in current() if p["id"] != left) == [15, 16]

            # Two clients invoke the same tab concurrently from different origins.
            terminal.action("apply-tiled-swap-layout", "columns")
            other = Terminal(binary, env, name)
            other.grant_status_permissions()
            other.until("second client ready", lambda: b"zellij-ready> " in other.output)
            other.prefix(b"h")
            other.prefix(b"h")
            before = len(rows())
            terminal.prefix(b"=")
            other.prefix(b"=")
            terminal.until("both serialized invocations finish", lambda: len(rows()) == before + 2)
            replies = rows()[before:]
            assert all(r["code"] == 0 for r in replies), replies
            assert len({r["origin"] for r in replies}) == 2, replies
            assert {p["id"] for p in current()} == ids
            # Another client's active tab must never redirect the helper.
            other.prefix(b"c")
            terminal.until("other tab", lambda: len(terminal.tabs()) == 2)
            unrelated = {p["id"]: geometry([p])[p["id"]] for p in terminal.terminals() if p["tab_id"] != source_tab}
            invoke(b"g")
            assert {p["id"]: geometry([p])[p["id"]] for p in terminal.terminals() if p["tab_id"] != source_tab} == unrelated
            other.prefix(b"d")
            other.close()
            other = None

            terminal.prefix(b"z")
            terminal.until("zoomed", lambda: any(p["is_fullscreen"] for p in current()))
            settled = geometry(current())
            invoke(b"=", failure="zoomed")
            assert geometry(current()) == settled
            terminal.prefix(b"z")
            terminal.until("unzoomed", lambda: not any(p["is_fullscreen"] for p in current()))
            # Native layout cycling remains a separate, explicitly rearranging control.
            terminal.action("apply-tiled-swap-layout", "stacked")
            settled = geometry(current())
            invoke(b"=", failure="stacked")
            assert geometry(current()) == settled
            for _ in range(5):
                terminal.prefix(b" ")
                if json.loads(terminal.action("current-tab-info", "--json"))["active_swap_layout_name"] == "equalize":
                    break
            else:
                raise AssertionError("Native layout cycle did not offer equalize")
            terminal.until("preset restored", lambda: len({p["pane_y"] for p in current()}) == 2)
            fcntl.ioctl(terminal.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
            terminal.until("native preset fits a smaller terminal", lambda:
                           sorted(geometry(current()).values()) ==
                           [(0, 1, 40, 23), (40, 1, 40, 12), (40, 13, 40, 11)])

            terminal.send(b'printf "%s|%s\\n" "$token" "$$" > "$HOME/focus-proof"\r')
            terminal.until("focus proof", lambda: (home / "focus-proof").exists())
            assert (home / "focus-proof").read_text().strip() == f"keep-{right}|{pids[right]}"
            for pid in ids:
                terminal.action("write-chars", "--pane-id", f"terminal_{pid}",
                                f'printf "%s|%s\\n" "$token" "$$" > "$HOME/proof-{pid}"\r')
                terminal.until("live state proof", lambda: (home / f"proof-{pid}").exists())
                assert (home / f"proof-{pid}").read_text().strip() == f"keep-{pid}|{pids[pid]}"
                assert f"HISTORY-{pid}" in terminal.action("dump-screen", "--full", "--pane-id", f"terminal_{pid}")
            # Fixed internal neighbors must not redirect resizing to another edge.
            resize(120)
            fixed_layout = work / "fixed-neighbor.kdl"
            fixed_layout.write_text('''layout {
                tab split_direction="vertical" {
                    pane size="67%" command="/bin/sh"
                    pane command="/bin/sh"
                    pane size=60 command="/bin/sh"
                }
            }''')
            source_tab = int(terminal.action("new-tab", "--layout", str(fixed_layout)))
            terminal.until("fixed-neighbor columns", lambda: widths() == [40, 20, 60])
            ids = {p["id"] for p in current()}
            settled = geometry(current())
            invoke(b"=")
            assert geometry(current()) == settled, current()
            print("PASS: balancing keys preserve topology, IDs, PIDs, memory, history and focus; "
                  "golden skip/cap, nearest steps, nested groups and concurrent origins verified.")
        finally:
            subprocess.run([binary, "kill-session", name], env=env, capture_output=True, timeout=5)
            if other is not None:
                other.close()
            terminal.close()


if __name__ == "__main__":
    main()
