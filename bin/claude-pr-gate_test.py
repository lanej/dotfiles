"""One regression detector for PRs opening only from a checked description."""
import json
import os
from pathlib import Path
import subprocess

BIN = Path(__file__).parent


def hook_denies(command):
    result = subprocess.run([str(BIN / "claude-pr-gate-hook")], capture_output=True, text=True,
                            input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}))
    assert result.returncode == 0
    return bool(result.stdout) and json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_prs_open_only_from_a_checked_description(tmp_path):
    assert hook_denies("cd ~/src/shop && gh pr create --fill")
    assert not hook_denies("gh pr create --help")
    assert not hook_denies("gh-pr-create-from PR.md --draft")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "gh").write_text('#!/bin/sh\necho "$@" > "$GH_LOG"; cat "$6" >> "$GH_LOG"\n')
    (fake_bin / "gh").chmod(0o755)
    env = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}", "GH_LOG": str(tmp_path / "gh.log")}

    def open_pr(text, *args):
        (tmp_path / "PR.md").write_text(text)
        return subprocess.run([str(BIN / "gh-pr-create-from"), str(tmp_path / "PR.md"), *args],
                              capture_output=True, text=True, env=env)

    leaky = open_pr("fix(ui): raise button contrast\n\n## Why\nSee /Users/josh/Desktop/audit.pdf\n")
    assert leaky.returncode == 1 and "/Users/" in leaky.stderr
    assert not (tmp_path / "gh.log").exists()

    good = open_pr("fix(ui): raise button contrast\n\n## Why\nFails WCAG AA.\nFixes #87\n", "--head", "fix/contrast")
    assert good.returncode == 0, good.stderr
    log = (tmp_path / "gh.log").read_text()
    assert log.startswith("pr create --title fix(ui): raise button contrast --body-file ")
    assert "--head fix/contrast" in log and "Fixes #87" in log and "fix(ui)" not in log.split("\n", 1)[1]
