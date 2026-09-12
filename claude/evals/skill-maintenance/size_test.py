"""One regression detector for the entrypoint size budget."""
from pathlib import Path
import shutil
import subprocess
import sys


def test_entrypoint_budget_requires_trimming_new_and_growing_files(tmp_path):
    """Trim source and installed instructions, including a linked skill tree."""
    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args], text=True).strip()
    git("init", "-q")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "core.autocrlf", "false")
    folder = tmp_path / "claude/evals/skill-maintenance"
    folder.mkdir(parents=True)
    for name in ["check_size.py", "size-budgets.json"]:
        shutil.copyfile(Path(__file__).with_name(name), folder / name)
    skill = tmp_path / "claude/skills/example/SKILL.md"
    skill.parent.mkdir(parents=True)
    # CRLF must count: this existing skill is ~4043 tokens, below 500 lines.
    skill.write_bytes((b"x" * 31 + b"\r\n") * 490)
    git("add", "claude/skills/example/SKILL.md")
    git("commit", "-qm", "baseline")

    home = tmp_path / "home"
    installed = home / ".claude"
    installed.mkdir(parents=True)
    (installed / "skills").symlink_to(tmp_path / "claude/skills", target_is_directory=True)
    applied = installed / "CLAUDE.md"
    applied.write_text("x\n" * 501)
    command = [sys.executable, str(folder / "check_size.py"), "--base", "HEAD",
               "--installed-home", str(home)]
    skill.write_bytes((b"x" * 31 + b"\r\n") * 491)
    agents = tmp_path / "AGENTS.md"
    agents.write_text("x\n" * 501)
    git("add", "AGENTS.md")
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL AGENTS.md: 501 lines" in result.stdout
    assert f"FAIL installed {applied}: 501 lines" in result.stdout
    assert (f"FAIL installed {installed / 'skills/example/SKILL.md'}: "
            "491 lines, ~4051 tokens") in result.stdout

    # Restore the existing skill's size and bring new instructions within budget.
    skill.write_bytes((b"x" * 31 + b"\r\n") * 490)
    agents.write_text("x\n" * 500)
    applied.write_text("x\n" * 500)
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
