#!/usr/bin/env python3
"""Exercise zero-based tab labels and directory titles through the installed UI."""

import base64
import codecs
import errno
import fcntl
import importlib
import json
import os
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
import time

import pyte

workflow = importlib.import_module("test-zellij")
Display = importlib.import_module("test-zellij-status").Display
ROOT, Terminal, PROMPT = workflow.ROOT, workflow.Terminal, workflow.PROMPT


def main():
    for name in ("zellij", "cargo", "fzf", "zsh", "git"):
        assert shutil.which(name), f"Install {name} before testing tab labels"
    scratch = tempfile.TemporaryDirectory(prefix="zj-labels-", dir="/tmp")
    with scratch as directory:
        work = Path(directory).resolve()
        home, runtime, temporary = work / "home", work / "run", work / "tmp"
        for path in (home, runtime, temporary):
            path.mkdir(mode=0o700)
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh", "PS1": PROMPT.decode(),
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_CACHE_HOME": str(work / "cache"), "XDG_DATA_HOME": str(work / "data"),
               "XDG_STATE_HOME": str(work / "state"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(temporary),
               "PATH": str(home / ".local/bin") + os.pathsep + os.environ["PATH"]}
        workflow.preserve_rust_homes(env)
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV",
                    "FZF_DEFAULT_OPTS", "FZF_DEFAULT_OPTS_FILE", "FZF_DEFAULT_COMMAND",
                    "SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY"):
            env.pop(key, None)
        subprocess.run(["make", "--no-print-directory", "zellij-status", "zellij"], cwd=ROOT,
                       env=env, check=True, capture_output=True, text=True)
        project = home / "project"
        project.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "topic", str(project)], check=True)
        subprocess.run(["git", "-C", str(project), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit", "-qm", "Initial",
                        "--allow-empty"], check=True)
        binary = shutil.which("zellij")
        name = "labels-" + work.name
        terminal = Terminal(binary, env, name)
        other = None
        screen, decoder = Display(480, 32), codecs.getincrementaldecoder("utf-8")("replace")
        stream, offset = pyte.Stream(screen), 0

        def top_line():
            nonlocal offset
            stream.feed(decoder.decode(bytes(terminal.output[offset:])))
            offset = len(terminal.output)
            return screen.display[0]

        def active():
            return next(tab for tab in terminal.tabs() if tab["active"])

        def picker_screen():
            pane = next((pane for pane in terminal.terminals() if pane["is_floating"]), None)
            return terminal.action("dump-screen", "--pane-id", f"terminal_{pane['id']}") if pane else ""

        try:
            terminal.grant_status_permissions()
            terminal.until("first tab starts at zero", lambda:
                           PROMPT in terminal.output and "0:Tab #0" in top_line())
            # Resize after startup (Terminal sets its initial PTY size in the
            # child), keeping all eleven full labels visible for this workflow.
            fcntl.ioctl(terminal.fd, termios.TIOCSWINSZ, struct.pack("HHHH", 32, 480, 0, 0))
            # One session crosses the direct-key boundary, rather than separate
            # cases that repeat the same labeling workflow.
            for count in range(2, 12):
                terminal.prefix(b"c")
                terminal.until("create tabs through the eleventh", lambda:
                               len(terminal.tabs()) == count)
            eleventh = active()["tab_id"]
            terminal.until("eleventh tab displays position ten", lambda: "10:Tab #10" in top_line())
            terminal.prefix(b"0")
            terminal.until("zero key selects first tab", lambda: active()["position"] == 0)
            terminal.prefix(b"9")
            terminal.until("nine key selects tenth tab", lambda: active()["position"] == 9)
            terminal.prefix(b"\x06")
            terminal.until("tab picker opens", lambda: "Tabs (attention" in picker_screen())
            terminal.send(b"10:")
            terminal.until("picker exposes tab ten", lambda:
                           "1/11" in picker_screen() and "10: Tab #10" in picker_screen())
            terminal.send(b"\r")
            terminal.until("picker selects stable eleventh tab", lambda: active()["tab_id"] == eleventh
                           and not any(pane["is_floating"] for pane in terminal.terminals()))
            terminal.action("move-tab", "left", "--tab-id", str(eleventh))
            terminal.until("reordered fallback follows position rather than stable ID", lambda:
                           active()["tab_id"] == eleventh and active()["position"] == 9 and "9:Tab #9" in top_line())

            terminal.prefix(b"0")
            terminal.until("leave the reordered tab", lambda: active()["position"] == 0)
            terminal.prefix(b"\x06")
            terminal.until("reordered picker opens", lambda: "Tabs (attention" in picker_screen())
            terminal.send(b"9:")
            terminal.until("picker exposes the new position", lambda:
                           "1/11" in picker_screen() and "9: Tab #9" in picker_screen())
            terminal.send(b"\r")
            terminal.until("reordered selection retains the stable ID", lambda:
                           active()["tab_id"] == eleventh
                           and not any(pane["is_floating"] for pane in terminal.terminals()))
            terminal.prefix(b"v")
            terminal.until("split has two tiled terminals", lambda:
                           len([pane for pane in terminal.terminals() if pane["tab_id"] == eleventh]) == 2)
            hook = home / ".local/share/zsh/zellij-auto-title.zsh"
            terminal.send(("cd " + shlex.quote(str(project)) + "; exec zsh -f\rsource "
                           + shlex.quote(str(hook)) + "\r").encode())
            terminal.until("directory/git hook titles the generated split tab", lambda:
                           active()["name"] == "project  topic" and "9:project  topic" in top_line())
            terminal.send(b"printf '\\033]2;application work\\007'; read application_done\r")
            terminal.until("application title appears in its pane while the tab keeps the project", lambda:
                           any(p["title"] == "application work" for p in terminal.terminals())
                           and active()["name"] == "project  topic" and "9:project  topic" in top_line())
            terminal.send(b"done\r")
            terminal.until("prompt restores the directory pane title", lambda:
                           "9:project  topic" in top_line())
            ownership_probe = home / "ownership.json"
            terminal.send(('zellij-status view "$ZELLIJ_SESSION_NAME" > '
                           + shlex.quote(str(ownership_probe)) + "\r").encode())
            terminal.until("session socket override identifies title ownership", lambda:
                           ownership_probe.exists() and json.loads(ownership_probe.read_text())
                           ["auto_titles"].get(str(eleventh)) == "project  topic")
            missing_override_probe = home / "ownership-without-override.json"
            terminal.send(('env -u ZELLIJ_SOCKET_DIR zellij-status view "$ZELLIJ_SESSION_NAME" > '
                           + shlex.quote(str(missing_override_probe)) + "\r").encode())
            terminal.until("missing custom socket override grants no ownership", lambda:
                           missing_override_probe.exists()
                           and json.loads(missing_override_probe.read_text())["auto_titles"] == {})
            token = base64.urlsafe_b64encode(name.encode()).decode()
            preview = subprocess.run([str(home / ".local/bin/zellij-picker"), "--preview-session", token],
                                     env={**env, "ZELLIJ_SESSION_NAME": name}, check=True,
                                     capture_output=True, text=True, timeout=10)
            assert "9: project  topic" in preview.stdout, preview.stdout
            source = next(pane for pane in terminal.terminals()
                          if pane["tab_id"] == eleventh and pane["is_focused"])
            terminal.action("rename-pane", "agent work", "--pane-id", f"terminal_{source['id']}")
            terminal.send(b"cd ..\r")
            terminal.until("shell hook preserves explicit pane title", lambda: any(p["title"] == "agent work" for p in terminal.terminals()) and "9:project  topic" in top_line())

            def frame_title_color():
                top_line()  # Feed the latest terminal output into the screen.
                row, left = source["pane_y"], source["pane_x"]
                column = screen.display[row].find("agent work", left, left + source["pane_columns"])
                return screen.buffer[row][column].fg if column >= 0 else None

            def frame_border_colors():
                top_line()
                row, left = source["pane_y"], source["pane_x"]
                return {screen.buffer[row][column].fg
                        for column in range(left, left + source["pane_columns"])
                        if screen.buffer[row][column].data in "─┌┐╭╮"}

            terminal.until("focused pane title and full border are purple", lambda:
                           frame_title_color() == "b48ead" and frame_border_colors() == {"b48ead"})
            terminal.prefix(b"h")
            terminal.until("unfocused pane title stays readable with a background-colored border", lambda:
                           frame_title_color() == "d8dee9" and frame_border_colors() == {"2e3440"})
            terminal.prefix(b"l")
            terminal.until("returning to the pane restores the purple title and full border", lambda:
                           frame_title_color() == "b48ead" and frame_border_colors() == {"b48ead"})
            terminal.prefix(b"z")
            terminal.until("zoom uses the expand glyph on a gold tab", lambda:
                           "󰊓 9:" in top_line() and "FULLSCREEN" not in top_line()
                           and screen.buffer[0][top_line().index("󰊓")].bg == "ebcb8b")
            terminal.prefix(b"z")
            terminal.until("restoring the split clears the zoom glyph", lambda: "󰊓" not in top_line())
            other = Terminal(binary, {**env, "SSH_CONNECTION": "192.0.2.2 4000 192.0.2.1 22"}, name)
            other.grant_status_permissions()
            other.until("remote client sees the SSH lock", lambda: "".encode() in other.output)
            assert "" not in top_line(), "Remote attachment marked the local client as SSH"
            other.prefix(b"9")
            other.until("second attachment is ready", lambda: b"agent work" in other.output)
            other.prefix(b"h")
            terminal.until("both clients retain the same automatic tab title", lambda:
                           len([pane for pane in terminal.terminals()
                                if pane["tab_id"] == eleventh and pane["is_focused"]]) == 2
                           and "9:project  topic" in top_line())
            preview = subprocess.run([str(home / ".local/bin/zellij-picker"), "--preview-session", token],
                                     env={**env, "ZELLIJ_SESSION_NAME": name}, check=True,
                                     capture_output=True, text=True, timeout=10)
            assert "9: project  topic" in preview.stdout, preview.stdout
            # Use the real chooser's complete-snapshot read, including its
            # lifecycle ownership payload and attachment-readiness handling.
            # Caller stdin must not become a second, ownership-free request.
            clients = subprocess.run([str(home / ".local/bin/zellij-picker"), "client-snapshot"],
                                     env={**env, "ZELLIJ_SESSION_NAME": name}, check=False,
                                     input="\n", capture_output=True, text=True, timeout=10)
            assert clients.returncode == 0, f"Client snapshot read failed:\n{clients.stderr}\n{clients.stdout}"
            rows = list(json.loads(clients.stdout).values())
            assert {row.get("tab") for row in rows} == {"9: project  topic"}, rows
            other.prefix(b"d")
            peer = next(p for p in terminal.terminals() if p["tab_id"] == eleventh and p["id"] != source["id"])
            terminal.action("rename-pane", "--pane-id", f"terminal_{peer['id']}", "oldest survivor")
            terminal.action("new-pane", "--direction", "right", "--name", "project  topic", "--", "/bin/sh")
            duplicate = terminal.until("second project pane opens", lambda: next(
                (p for p in terminal.terminals() if p["tab_id"] == eleventh and p["title"] == "project  topic"), None))
            terminal.action("close-pane", "--pane-id", f"terminal_{source['id']}")
            terminal.until("remaining project pane keeps the label", lambda:
                           all(p["id"] != source["id"] for p in terminal.terminals()) and active()["name"] == "project  topic")
            terminal.action("close-pane", "--pane-id", f"terminal_{duplicate['id']}")
            terminal.until("last provider exits and oldest pane supplies the title", lambda:
                           active()["name"] == "oldest survivor" and "9:oldest survivor" in top_line())
            terminal.prefix(b"r")
            terminal.until("rename field is empty", lambda: active()["name"] == "" and "9: " in top_line())
            subprocess.run([str(home / ".local/bin/zellij-status"), "refresh-view", name],
                           env=env, check=True, capture_output=True, timeout=10)
            assert active()["name"] == "", "A background refresh filled in the manual rename field"
            terminal.send(b"manual work\r")
            terminal.send(("cd " + shlex.quote(str(project)) + "\r").encode())
            terminal.until("directory change preserves explicit tab title", lambda:
                           active()["name"] == "manual work" and "9:manual work" in top_line())
            print("PASS: tab positions, direct keys, picker, reorder, directory/git titles, and explicit names agree.")
        finally:
            subprocess.run([binary, "kill-session", name], env=env, capture_output=True, timeout=5)
            if other is not None:
                other.close()
            terminal.close()
            # Native shutdown acknowledges before every shell/helper finishes
            # writing. Retry only that teardown race, with a strict bound;
            # permission errors and persistent writers must still fail.
            deadline = time.monotonic() + 5
            while True:
                try:
                    scratch.cleanup()
                    break
                except OSError as error:
                    if error.errno != errno.ENOTEMPTY or time.monotonic() >= deadline:
                        raise
                    time.sleep(0.1)


if __name__ == "__main__":
    main()
