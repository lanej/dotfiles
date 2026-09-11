import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.fixture
def sizes():
    path = Path(__file__).with_name("check_size.py")
    spec = importlib.util.spec_from_file_location("skill_size", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_new_long_skill_fails(sizes):
    assert sizes.assess("x\n" * 501, None, {})["failed"]


def test_dense_entrypoint_fails_estimated_token_budget(sizes):
    result = sizes.assess("x" * 16001, None, {})
    assert result["failed"]
    assert result["estimated_tokens"] == 4001


def test_exact_default_limits_pass(sizes):
    assert not sizes.assess("x\n" * 500, None, {})["failed"]
    assert not sizes.assess("x" * 16000, None, {})["failed"]


def test_existing_overage_can_stay_or_shrink_but_not_grow(sizes):
    old = "x\n" * 700
    assert not sizes.assess(old, old, {})["failed"]
    assert not sizes.assess("x\n" * 600, old, {})["failed"]
    assert sizes.assess("x\n" * 701, old, {})["failed"]


def test_shrinking_lines_cannot_hide_token_growth(sizes):
    assert sizes.assess("x" * 20001, "y\n" * 700, {})["failed"]


def test_reviewed_per_file_budget_has_an_explicit_reason(sizes):
    assert not sizes.assess("x\n" * 501, None,
                            {"max_lines": 550, "reason": "Required reference index."})["failed"]
    with pytest.raises(ValueError):
        sizes.assess("x\n" * 501, None, {"max_lines": 550})


@pytest.mark.parametrize("budget", [0, -1, True, "500"])
def test_invalid_budget_cannot_disable_the_check(sizes, budget):
    with pytest.raises(ValueError):
        sizes.assess("x", None, {"max_lines": budget, "reason": "test"})


@pytest.mark.parametrize("path,want", [
    ("claude/skills/pdf/SKILL.md", True),
    ("gemini/skills/pdf/SKILL.md", True),
    ("claude/commands/socrates.md", True),
    ("claude/commands/gh/review-pr.md", True),
    ("claude/agents/reviewer.md", True),
    ("claude/skills/pdf/references/SKILL-format.md", False),
    ("claude/evals/example/record.json", False),
])
def test_only_entrypoints_have_the_entrypoint_budget(sizes, path, want):
    assert sizes.is_entrypoint(path) is want


def test_cli_counts_raw_crlf_bytes_against_the_budget(tmp_path):
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
    for name in ["check_size.py", "check_evidence.py", "size-budgets.json"]:
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
