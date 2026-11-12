#!/usr/bin/env python3
"""Exercise submission rewriting and preservation through the hook entrypoint."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HOOK = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "bin/codex-octo-submit"


def main():
    with tempfile.TemporaryDirectory(prefix="octo-hook-") as folder:
        home = Path(folder)
        (home / ".codex").mkdir()
        binary = home / ".local/bin/octo-manager"
        binary.parent.mkdir(parents=True)
        binary.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n")
        binary.chmod(0o755)
        env = {**os.environ, "HOME": str(home), "CODEX_HOME": str(home / ".codex")}
        hooks = home / ".codex/hooks.json"
        existing = {"matcher": "Bash", "hooks": [{"type": "command", "command": "my-hook", "timeout": 3}], "custom": True}
        hooks.write_text(json.dumps({"hooks": {"PreToolUse": [existing]}, "custom": {"preserve": True}}))
        def run(args, data=None):
            result = subprocess.run(["python3", str(HOOK), *args], input=None if data is None else json.dumps(data), text=True, capture_output=True, env=env, timeout=10)
            assert result.returncode == 0, result.stderr
            return result.stdout
        run(["--install"])
        installed = hooks.read_bytes()
        run(["--install"])
        assert hooks.read_bytes() == installed
        document = json.loads(installed)
        assert document["hooks"]["PreToolUse"][0] == existing
        assert document["custom"] == {"preserve": True}
        event = {"hook_event_name": "PreToolUse", "session_id": "session-123", "cwd": str(home), "tool_use_id": "call-456", "tool_input": {"command": "gh pr create --title 'fix: preserve spaces' --body 'Observed outcome.' --draft", "timeout_ms": 1000}}
        output = json.loads(run([], event))["hookSpecificOutput"]
        assert output["permissionDecision"] == "allow"
        changed = output["updatedInput"]
        assert changed["timeout_ms"] == 1000
        command = shlex.split(changed["command"])
        received = subprocess.check_output(command, text=True).splitlines()
        assert received == ["submit-pr", "--title", "fix: preserve spaces", "--body", "Observed outcome.", "--draft", "--thread-id", "session-123", "--cwd", str(home), "--endpoint", "local", "--request-id", "session-123:call-456"]
        def response(command):
            event["tool_input"]["command"] = command
            text = run([],event)
            return json.loads(text)["hookSpecificOutput"] if text else None
        assert response("git status --short") is None
        assert response("echo gh pr create") is None
        assert response("gh-pr-create-from --check description.md") is None
        assert response("gh pr create --fill")["permissionDecision"] == "deny"
        assert response("cd repo && gh pr create --title a --body b")["permissionDecision"] == "deny"
        assert response("gh pr create --title '$TITLE' --body body")["permissionDecision"] == "deny"
        assert response("octo-manager submit-pr --intent-file intent.json --thread-id stale --cwd /stale")["permissionDecision"] == "allow"
        description = home / "description.md"
        description.write_text("fix: example\n\nThis changes the example.")
        assert response("gh-pr-create-from description.md --base main")["permissionDecision"] == "allow"
        binary.unlink()
        assert response("gh pr create --title a --body b")["permissionDecision"] == "deny"
    print("Codex Octo submission hook: passed")


if __name__ == "__main__":
    main()
