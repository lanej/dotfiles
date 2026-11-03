#!/usr/bin/env python3
"""Exercise configured Codex title hooks through a private native Zellij session."""

import importlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile


workflow = importlib.import_module("test-zellij")
ROOT, Terminal, PROMPT = workflow.ROOT, workflow.Terminal, workflow.PROMPT


def main():
    binary = shutil.which("zellij")
    assert binary, "Install Zellij before testing Codex pane titles"
    with tempfile.TemporaryDirectory(prefix="zj-titles-", dir="/tmp") as directory:
        work = Path(directory).resolve()
        home, runtime = work / "home", work / "run"
        home.mkdir()
        runtime.mkdir(mode=0o700)
        (home / ".files").symlink_to(ROOT)
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh", "PS1": PROMPT.decode(),
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_STATE_HOME": str(work / "state"), "XDG_CACHE_HOME": str(work / "cache"),
               "XDG_DATA_HOME": str(work / "data"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(work)}
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV"):
            env.pop(key, None)
        env["CODEX_HOME"] = str(home / ".codex")
        subprocess.run([sys.executable, str(ROOT / "bin/sync-codex-tmux-hooks")],
                       env=env, check=True, capture_output=True, timeout=5)
        hooks = json.loads((home / ".codex/hooks.json").read_text())["hooks"]
        config = work / "config.kdl"
        config.write_text('default_mode "locked"\npane_frames true\npane_frame_style "full"\n'
                          'show_startup_tips false\nshow_release_notes false\n'
                          'session_serialization false\n')
        layout = work / "layout.kdl"
        layout.write_text("layout { pane; }\n")
        name = "titles-" + work.name
        terminal = Terminal(binary, env, name, [
            binary, "--config", str(config), "--new-session-with-layout", str(layout),
            "--session", name,
        ])
        try:
            terminal.until("the private shell starts", lambda:
                           PROMPT in terminal.output and len(terminal.terminals()) == 1)
            terminal.action("new-pane", "--direction", "right", "--cwd", str(home),
                            "--", "/bin/sh")
            terminal.until("both private shells start", lambda: len(terminal.terminals()) == 2)
            left, right = sorted(terminal.terminals(), key=lambda pane: pane["pane_x"])
            identity = "01a19d8f-d3f1-7490-a292-603901234567"
            sibling = "01a19d8f-d3f2-7490-a292-603901234567"
            terminal.action("write-chars", "--pane-id", str(left["id"]),
                            "printf '\\033]0;%s\\007' "
                            + shlex.quote(f"codex | {identity[:29]}... | Ready | project") + "\r")
            terminal.action("write-chars", "--pane-id", str(right["id"]),
                            "printf '\\033]0;%s\\007' "
                            + shlex.quote(f"codex | {sibling[:29]}... | Ready | other") + "\r")
            terminal.until("native titles identify the two threads", lambda:
                           identity[:29] in terminal.terminals()[0]["title"])
            # WHY: Shared daemon hints must not redirect this thread into the sibling pane.
            hook_env = {**env, "ZELLIJ_SESSION_NAME": name, "ZELLIJ_PANE_ID": str(right["id"])}

            def title(pane_id):
                return next(pane["title"] for pane in terminal.terminals() if pane["id"] == pane_id)

            def emit(event_name, session_id=identity, **fields):
                payload = {"hook_event_name": event_name, "session_id": session_id,
                           "cwd": str(home / "project"), **fields}
                for group in hooks[event_name]:
                    for hook in group["hooks"]:
                        subprocess.run(["/bin/sh", "-c", hook["command"]], env=hook_env,
                                       input=json.dumps(payload), text=True, check=True, timeout=4)

            emit("SessionStart", source="startup")
            assert title(left["id"]) == "󰚩 01a19d8f  | project"
            emit("UserPromptSubmit")
            assert title(left["id"]) == "󰚩 01a19d8f  | project"
            emit("PermissionRequest")
            assert title(left["id"]) == "󰚩 01a19d8f  | project"
            emit("PostToolUse", tool_name="functions.exec_command")
            assert title(left["id"]) == "󰚩 01a19d8f  | project"
            emit("Stop")
            assert title(left["id"]) == "󰚩 01a19d8f  | project"
            assert sibling[:29] in title(right["id"])
            terminal.until("the configured title is rendered", lambda:
                           "󰚩 01a19d8f  | project".encode() in terminal.output)
            resumed = "01a19d8f-d3f3-7490-a292-603901234567"
            native = f"codex | {resumed[:29]}... | Ready | project"
            terminal.action("write-chars", "--pane-id", str(left["id"]),
                            "printf '\\033]0;%s\\007' " + shlex.quote(native) + "\r")
            terminal.drain()
            emit("SessionStart", session_id=resumed, source="resume")
            assert title(left["id"]) == "󰚩 01a19d8f  | project"
            emit("PostToolUse", tool_name="functions.exec_command")
            current = "01a19d8f-d3f4-7490-a292-603901234567"
            native = f"codex | {current[:29]}... | Ready | project"
            terminal.action("write-chars", "--pane-id", str(left["id"]),
                            "printf '\\033]0;%s\\007' " + shlex.quote(native) + "\r")
            terminal.drain()
            emit("SessionStart", session_id=current, source="resume")
            assert title(left["id"]) == "󰚩 01a19d8f  | project"
            emit("SessionEnd")
            emit("SessionEnd", session_id=resumed)
            assert title(left["id"]) == "󰚩 01a19d8f  | project"
            emit("SessionEnd", session_id=current)
            assert title(left["id"]) == native
            emit("PostToolUse", session_id=current, tool_name="functions.exec_command")
            assert title(left["id"]) == native
            terminal.action("write-chars", "--pane-id", str(left["id"]),
                            "printf '\\033]0;shell | project\\007'\r")
            terminal.until("the original shell title returns", lambda:
                           title(left["id"]) == "shell | project")
            print("PASS: configured title and status glyphs render in the owning pane; "
                  "thread switches and delayed events preserve ownership; shell titles return.")
        finally:
            subprocess.run([binary, "kill-session", name], env=env,
                           capture_output=True, timeout=5)
            terminal.close()


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr or error.stdout or str(error)) from error
