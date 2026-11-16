"""Exercise publication gating through the Claude hook entrypoint."""
import json
from pathlib import Path
import subprocess

BIN = Path(__file__).parent


def hook_response(command):
    result = subprocess.run([str(BIN / "claude-pr-gate-hook")], capture_output=True, text=True,
                            input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}))
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["hookSpecificOutput"] if result.stdout else None


def test_publication_requires_octo():
    for command in (
        "cd ~/src/shop && gh pr create --fill",
        "/opt/bin/gh pr create --title example",
        "gh-pr-create-from PR.md --draft",
        "command /old/bin/gh-pr-create-from PR.md",
        "gh-pr-create-from --check PR.md",
    ):
        response = hook_response(command)
        assert response["permissionDecision"] == "deny"
        assert "octo-manager submit-pr" in response["permissionDecisionReason"]
        assert "actual calling session identity" in response["permissionDecisionReason"]
    for command in (
        "gh pr create --help",
        "gh pr view 123",
        "echo gh-pr-create-from",
        "octo-manager submit-pr --intent-file intent.json --thread-id actual-session",
    ):
        assert hook_response(command) is None
