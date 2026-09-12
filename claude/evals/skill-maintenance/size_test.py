"""One regression detector for the entrypoint size budget."""
from pathlib import Path
import shutil
import subprocess
import sys


def test_entrypoint_budget_rejects_new_overage_but_accepts_existing(tmp_path):
    """A 490-line file is 16,170 bytes, not its normalized 15,680 bytes."""
    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args], text=True).strip()
    git("init", "-q")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "core.autocrlf", "false")
    git("commit", "--allow-empty", "-qm", "baseline")
    base = git("rev-parse", "HEAD")
    folder = tmp_path / "claude/evals/skill-maintenance"
    folder.mkdir(parents=True)
    for name in ["check_size.py", "size-budgets.json"]:
        shutil.copyfile(Path(__file__).with_name(name), folder / name)
    skill = tmp_path / "claude/skills/example/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_bytes((b"x" * 31 + b"\r\n") * 490)
    git("add", "claude/skills/example/SKILL.md")
    result = subprocess.run([sys.executable, str(folder / "check_size.py"), "--base", base],
                            capture_output=True, text=True)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "490 lines, ~4043 tokens" in result.stdout
    # The identical pre-existing overage must subsequently be grandfathered.
    git("commit", "-qm", "existing overage")
    result = subprocess.run([sys.executable, str(folder / "check_size.py"), "--base", "HEAD"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
