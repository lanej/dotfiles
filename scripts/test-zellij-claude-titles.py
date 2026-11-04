#!/usr/bin/env python3
"""Exercise configured Claude hooks from inside a private native Zellij pane."""

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
    assert binary, "Install Zellij before testing Claude pane titles"
    assert shutil.which("tmux"), "Install tmux before testing nested pane ownership"
    with tempfile.TemporaryDirectory(prefix="zj-claude-titles-", dir="/tmp") as directory:
        work = Path(directory).resolve()
        home, runtime = work / "home", work / "run"
        home.mkdir()
        runtime.mkdir(mode=0o700)
        (home / ".files").symlink_to(ROOT)
        (home / ".claude").mkdir()
        (home / ".claude/settings.json").symlink_to(ROOT / ".claude/settings.json")
        env = {**os.environ, "HOME": str(home), "SHELL": "/bin/sh", "PS1": PROMPT.decode(),
               "TERM": "xterm-256color", "XDG_CONFIG_HOME": str(home / ".config"),
               "XDG_STATE_HOME": str(work / "state"), "XDG_CACHE_HOME": str(work / "cache"),
               "XDG_DATA_HOME": str(work / "data"), "XDG_RUNTIME_DIR": str(runtime),
               "ZELLIJ_SOCKET_DIR": str(runtime), "TMPDIR": str(work)}
        for key in ("ZELLIJ", "ZELLIJ_SESSION_NAME", "ZELLIJ_PANE_ID", "ZELLIJ_CONFIG_DIR",
                    "ZELLIJ_CONFIG_FILE", "TMUX", "TMUX_PANE", "ENV", "BASH_ENV",
                    "AGENT_STATUS_BIN", "PASEO_TERMINAL_ID"):
            env.pop(key, None)
        subprocess.run([sys.executable, str(ROOT / "scripts/make/zellij-config.py"), str(home)],
                       env=env, check=True, capture_output=True, timeout=5)
        runner = work / "emit.py"
        runner.write_text('''import json, os, re, subprocess, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text())
hooks = json.loads((Path.home() / ".claude/settings.json").read_text())["hooks"]
match = payload.get("source", "") if payload["hook_event_name"] == "SessionStart" else payload.get("tool_name", "")
for group in hooks.get(payload["hook_event_name"], []):
    if not re.search(group.get("matcher", ""), match):
        continue
    for hook in group["hooks"]:
        subprocess.run(["/bin/sh", "-c", hook["command"]], input=json.dumps(payload),
                       text=True, check=True, timeout=4, capture_output=True)
Path(sys.argv[2]).write_text("done")
''')
        config = work / "config.kdl"
        config.write_text('default_mode "locked"\npane_frames true\npane_frame_style "full"\n'
                          'show_startup_tips false\nshow_release_notes false\n'
                          'session_serialization false\n')
        layout = work / "layout.kdl"
        layout.write_text("layout { pane; }\n")
        name = "claude-" + work.name
        terminal = Terminal(binary, env, name, [
            binary, "--config", str(config), "--new-session-with-layout", str(layout),
            "--session", name,
        ])
        socket = str(work / "nested.sock")
        try:
            terminal.until("the private shell starts", lambda:
                           PROMPT in terminal.output and len(terminal.terminals()) == 1)
            terminal.action("new-pane", "--direction", "right", "--cwd", str(home),
                            "--", "/bin/sh")
            terminal.until("both private shells start", lambda: len(terminal.terminals()) == 2)
            left, right = sorted(terminal.terminals(), key=lambda pane: pane["pane_x"])
            identity = "2a63178e-d3f1-4490-a292-603901234567"
            terminal.action("write-chars", "--pane-id", str(left["id"]),
                            "printf '\\033]0;Claude Code\\007'\r")
            terminal.action("rename-pane", "--pane-id", f"terminal_{right['id']}", "my shell")
            terminal.until("the native Claude title arrives", lambda:
                           "Claude Code" in terminal.terminals()[0]["title"])
            sequence = 0

            def title(pane_id):
                return next(pane["title"] for pane in terminal.terminals() if pane["id"] == pane_id)

            def emit(event_name, session_id=identity, nested=False, **fields):
                nonlocal sequence
                sequence += 1
                payload = work / f"event-{sequence}.json"
                complete = work / f"complete-{sequence}"
                payload.write_text(json.dumps({"hook_event_name": event_name,
                    "session_id": session_id, "cwd": str(home / "project"), **fields}))
                command = [sys.executable, str(runner), str(payload), str(complete)]
                if nested:
                    command = ["tmux", "-S", socket, "-f", "/dev/null", "new-session",
                               "-d", "-s", "nested", shlex.join(command)]
                # WHY: Hooks must inherit the actual pane and its process ancestry.
                terminal.action("write-chars", "--pane-id", str(left["id"]),
                                shlex.join(command) + "\r")
                terminal.until("registered hooks finish", complete.exists)

            emit("SessionStart", source="startup", agent_type="custom-main-agent")
            assert title(left["id"]) == "✳ 2a63178e  | project"
            emit("UserPromptSubmit")
            assert title(left["id"]) == "✳ 2a63178e  | project"
            emit("PreToolUse", tool_name="AskUserQuestion")
            assert title(left["id"]) == "✳ 2a63178e  | project"
            emit("PostToolUse", tool_name="AskUserQuestion")
            emit("PermissionRequest", tool_name="Read")
            assert title(left["id"]) == "✳ 2a63178e  | project"
            emit("PostToolUse", tool_name="Read")
            assert title(left["id"]) == "✳ 2a63178e  | project"
            emit("StopFailure")
            assert title(left["id"]) == "✳ 2a63178e  | project"
            emit("UserPromptSubmit")
            emit("PostToolUseFailure", tool_name="Read", is_interrupt=True)
            assert title(left["id"]) == "✳ 2a63178e  | project"
            emit("Stop")
            assert title(left["id"]) == "✳ 2a63178e  | project"
            emit("UserPromptSubmit", agent_id="subagent-1")
            emit("UserPromptSubmit", nested=True)
            assert title(left["id"]) == "✳ 2a63178e  | project"
            assert title(right["id"]) == "my shell"
            terminal.until("the configured title renders", lambda:
                           "✳ 2a63178e  | project".encode() in terminal.output)
            resumed = "2a63178e-d3f2-4490-a292-603901234567"
            emit("SessionStart", session_id=resumed, source="resume")
            emit("SessionEnd")
            assert title(left["id"]) == "✳ 2a63178e  | project"
            emit("SessionEnd", session_id=resumed)
            assert title(left["id"]) == "Claude Code"
            emit("PostToolUse", session_id=resumed, tool_name="Read")
            assert title(left["id"]) == "Claude Code"
            emit("SessionStart", session_id=resumed, source="resume")
            terminal.action("rename-pane", "--pane-id", f"terminal_{left['id']}", "my handoff")
            emit("UserPromptSubmit", session_id=resumed)
            emit("SessionEnd", session_id=resumed)
            assert title(left["id"]) == "my handoff"
            print("PASS: configured Claude titles render in the owning pane; lifecycle glyphs, "
                  "nested tmux, subagents, session changes, and user names preserve ownership.")
        finally:
            subprocess.run(["tmux", "-S", socket, "kill-server"], env=env,
                           capture_output=True, timeout=5)
            subprocess.run([binary, "kill-session", name], env=env,
                           capture_output=True, timeout=5)
            terminal.close()


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr or error.stdout or str(error)) from error
