#!/usr/bin/env python3
"""Verify notices, inbox and history through the installed Zellij keybindings."""
import codecs
import importlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

import pyte

workflow = importlib.import_module("test-zellij")
status = importlib.import_module("test-zellij-status")
ROOT, Terminal, PROMPT = workflow.ROOT, workflow.Terminal, workflow.PROMPT


def main():
    for name in ("zellij", "fzf", "cargo", "python3"):
        assert shutil.which(name), f"Install {name} before testing notifications"
    with tempfile.TemporaryDirectory(prefix="zj-notify-", dir="/tmp") as directory:
        work = Path(directory)
        home, runtime, temporary = work / "home", work / "run", work / "tmp"
        for path in (home, runtime, temporary):
            path.mkdir(mode=0o700)
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh", "PS1": PROMPT.decode(),
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(work / "cache"), "XDG_DATA_HOME": str(work / "data"),
               "XDG_STATE_HOME": str(work / "state"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime),
               "TMPDIR": str(temporary),
               "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"]}
        workflow.preserve_rust_homes(env)
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV", "NO_COLOR"):
            env.pop(key, None)
        subprocess.run(["make", "--no-print-directory", "zellij-status", "zellij"],
                       cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        program = work / "agent.py"
        program.write_text(r'''import os
from pathlib import Path
import sys
import termios

settings = termios.tcgetattr(0)
settings[3] &= ~termios.ECHO
termios.tcsetattr(0, termios.TCSANOW, settings)
Path(sys.argv[1]).write_text(str(os.getpid()))
def report(value):
    print("\x1b]7501;state=" + value + ":app=fixture\x07", end="", flush=True)
report("working")
print("\x1b[2J\x1b[HRelease checks\n\nRunning integration tests…", flush=True)
for line in sys.stdin:
    value = line.strip()
    report(value)
    if value.startswith("blocked"):
        print("\n\x1b[38;2;235;203;139mDeploy this build?\x1b[0m\n  1  Deploy\n  2  Keep staging", flush=True)
    elif value == "done":
        print("\n\x1b[38;2;163;190;140mBuild passed. Ready to deploy.\x1b[0m", flush=True)
''')
        name = "notifications-" + work.name
        client = Terminal(shutil.which("zellij"), env, name)
        clients = [client]
        screen = status.Display(120, 32)
        stream = pyte.Stream(screen)
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        offset = 0

        def view():
            nonlocal offset
            stream.feed(decoder.decode(bytes(client.output[offset:])))
            offset = len(client.output)
            return "\n".join(screen.display)

        def history():
            result = subprocess.run([str(ROOT / "bin/zellij-notify"), "list"],
                                    env=env, check=True, capture_output=True, text=True)
            return json.loads(result.stdout)

        def capture(label):
            destination = os.environ.get("ZELLIJ_NOTIFICATION_SCREENSHOTS")
            if destination:
                view()
                path = Path(destination)
                path.mkdir(parents=True, exist_ok=True)
                (path / (label + ".json")).write_text(json.dumps([
                    [{"char": screen.buffer[y][x].data, "fg": screen.buffer[y][x].fg,
                      "bg": screen.buffer[y][x].bg, "bold": screen.buffer[y][x].bold}
                     for x in range(screen.columns)] for y in range(screen.lines)]))

        try:
            client.grant_status_permissions()
            client.until("notification bar ready", lambda: "!0 ●0 ✓0" in view())
            client.prefix(b"B")
            client.until("empty history remains readable", lambda:
                         "No notifications" in view() and "›" in view())
            capture("empty-history")
            client.send(b"\x1b")
            client.until("empty history closes", lambda: "Notification history" not in view())
            agent = client.terminals()[0]["id"]
            pid = work / "agent-pid"
            client.send((shlex.join(["python3", str(program), str(pid)]) + "\r").encode())
            client.until("agent working", lambda: pid.exists() and "●1" in view())
            original_pid = pid.read_text()
            client.prefix(b"c")
            client.until("background the agent", lambda: len(client.tabs()) == 2)
            client.until("the new tab has initialized its notification bar", lambda:
                         "1:Tab #1" in view() and "!0 ●1 ✓0" in screen.display[0])
            def focused_pane():
                active = next(tab["tab_id"] for tab in client.tabs() if tab["active"])
                return next(p["id"] for p in client.terminals()
                            if p["is_focused"] and p["tab_id"] == active)
            focused = focused_pane()
            client.action("paste", "--pane-id", f"terminal_{agent}", "blocked:kind=question\n")
            client.until("background question enters history", lambda:
                         any(row["level"] == "warn" for row in history()))
            client.until("urgent count and a notice are visible", lambda:
                         " │ !1 ●0 ✓0" in view().splitlines()[0])
            capture("notice")
            assert focused_pane() == focused
            client.send(b"echo notice-kept-keyboard-focus\r")
            client.until("notice left application input alone", lambda:
                         "notice-kept-keyboard-focus" in view())
            client.send(b"zellij-notify send --title Deploy 'Version ready'\r")
            client.until("script notifications enter the same journal", lambda:
                         any(row["title"] == "Deploy" and row["message"] == "Version ready"
                             for row in history()))
            client.action("paste", "--pane-id", f"terminal_{agent}", "done\n")
            client.until("completion is separate from urgency", lambda: "!0 ●0 ✓1" in view())
            client.until("completion retained in history", lambda:
                         any(row["level"] == "success" for row in history()))
            before = len(history())
            client.action("paste", "--pane-id", f"terminal_{agent}", "done\n")
            client.drain(0.3)
            assert len(history()) == before, "Same state produced duplicate history"
            client.prefix(b"B")
            client.until("history opens through its real key", lambda:
                         "Notification history" in view() and "Release checks" in view())
            capture("history")
            glyphs = [(cell.data, cell.fg) for y in range(3, screen.lines)
                      for cell in screen.buffer[y].values()]
            assert ("✓", "a3be8c") in glyphs, "Completion glyph lost its green color"
            assert ("·", "88c0d0") in glyphs, "Info glyph lost its blue color"
            assert ("!", "ebcb8b") in glyphs, "Attention glyph lost its yellow color"
            assert ("B", "a3be8c") in glyphs, "Pane preview lost its source text color"
            client.send(b"Version ready")
            client.until("history search finds a script notice", lambda:
                         "Version ready" in view() and "zellij-ready>" in view())
            client.send(b"\x15Pane")
            client.until("source title is searchable", lambda:
                         "Release checks" in view() and "Keep staging" in view())
            client.send(b"\r")
            client.until("history selection visits the original pane", lambda:
                         focused_pane() == agent)
            assert pid.read_text() == original_pid, "History jump restarted the source process"
            client.prefix(b"b")
            client.until("native inbox is exposed", lambda:
                         "Inbox" in view() or "inbox" in view())
            capture("inbox")
            client.send(b"\x1b")
            client = Terminal(shutil.which("zellij"), env, name + "-narrow", columns=80)
            clients.append(client)
            screen = status.Display(80, 32)
            stream = pyte.Stream(screen)
            decoder = codecs.getincrementaldecoder("utf-8")("replace")
            offset = 0
            client.grant_status_permissions()
            client.until("narrow bar is ready", lambda: "!0 ●0" in view())
            client.prefix(b"B")
            client.until("narrow history opens with a full source preview", lambda:
                         "Notification history" in view() and "Release checks" in view())
            capture("history-narrow")
            client.send(b"\x1b")
            print("PASS: installed notices preserve keyboard focus, urgency excludes completions, repeated state is deduplicated, history jumps without restarting the source, and the native inbox opens.")
        finally:
            for session in (name, name + "-narrow"):
                subprocess.run([client.binary, "kill-session", session], env=env,
                               capture_output=True, timeout=5)
            for terminal in clients:
                terminal.close()


if __name__ == "__main__":
    main()
