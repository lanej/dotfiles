"""Exercise the gate against real files, receipts, and Git diffs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).with_name("check_evidence.py")


@pytest.fixture
def gate():
    assert SCRIPT.exists(), "Missing skill-evidence freshness gate"
    spec = importlib.util.spec_from_file_location("skill_evidence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def put(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def evidence(tmp_path):
    source = "claude/commands/example.md"
    dependency = "claude/commands/example/shared.txt"
    receipt = {
        "version": 1,
        "sources": {source: put(tmp_path, source, "ask before deletion\n"),
                    dependency: put(tmp_path, dependency, "report only\n")},
        "artifacts": {},
        "checks": [{"name": "Report-only authority survives", "passed": True,
                    "evidence": "Candidate produces a report and leaves every file unchanged."}],
    }
    for role, content in [("baseline", "Deleted a file without authorization."),
                          ("candidate", "Produced a report; hashes unchanged."),
                          ("review", "Observed failure corrected. No user approval inferred.")]:
        path = f"claude/evals/example/run-1/{role}.md"
        receipt["artifacts"][role] = {"path": path, "sha256": put(tmp_path, path, content)}
    path = tmp_path / "claude/evals/example/run-1/evidence.json"
    path.write_text(json.dumps(receipt))
    return tmp_path, source, dependency, path, receipt


def test_current_sources_and_reviewed_evidence_pass(gate, evidence):
    root, source, _, _, _ = evidence
    assert gate.check(root, [source]) == []


@pytest.mark.parametrize("changed", ["source", "dependency", "candidate", "review"])
def test_source_dependency_or_artifact_change_invalidates_receipt(gate, evidence, changed):
    root, source, dependency, _, receipt = evidence
    target = {"source": source, "dependency": dependency}.get(changed)
    if target is None:
        target = receipt["artifacts"][changed]["path"]
    put(root, target, "changed after review")
    errors = gate.check(root, [source])
    assert errors and source in "\n".join(errors)


@pytest.mark.parametrize("change", ["failed", "empty", "string", "missing-review", "same-output"])
def test_incomplete_or_failed_review_cannot_pass(gate, evidence, change):
    root, source, _, path, receipt = evidence
    if change == "failed":
        receipt["checks"][0]["passed"] = False
    elif change == "empty":
        receipt["checks"] = []
    elif change == "string":
        receipt["checks"][0]["passed"] = "true"
    elif change == "missing-review":
        del receipt["artifacts"]["review"]
    else:
        receipt["artifacts"]["candidate"] = receipt["artifacts"]["baseline"]
    path.write_text(json.dumps(receipt))
    assert gate.check(root, [source])


def test_unrelated_change_does_not_require_backfilling_all_skills(gate, tmp_path):
    put(tmp_path, "claude/skills/old/SKILL.md", "unrelated existing skill")
    assert gate.check(tmp_path, ["docs/tmux.md"]) == []


@pytest.mark.parametrize("source", ["AGENTS.md", "CLAUDE.md", "GEMINI.md", "docs/skill-maintenance.md",
    "claude/CLAUDE.md", "claude/skills/new/SKILL.md", "claude/skills/new/scripts/helper.py",
    "claude/agents/reviewer.md", "claude/commands/socrates/spec-scaffold.tpl",
    "gemini/skills/new/SKILL.md"])
def test_governed_change_requires_evidence(gate, tmp_path, source):
    put(tmp_path, source, "new instructions or supporting resource")
    assert gate.check(tmp_path, [source])


def test_deletion_needs_an_explicit_absent_source_and_review(gate, evidence):
    root, source, _, path, receipt = evidence
    (root / source).unlink()
    assert gate.check(root, [source])
    receipt["sources"][source] = None
    path.write_text(json.dumps(receipt))
    assert gate.check(root, [source]) == []


def test_fresh_receipt_can_coexist_with_preserved_stale_run(gate, evidence):
    root, source, _, path, receipt = evidence
    old = json.loads(path.read_text())
    old["sources"][source] = "0" * 64
    path.with_name("unused.txt").write_text("irrelevant")
    old_path = root / "claude/evals/example/run-0/evidence.json"
    old_path.parent.mkdir()
    old_path.write_text(json.dumps(old))
    assert gate.check(root, [source]) == []


def test_symlinked_evidence_outside_repository_is_rejected(gate, evidence, tmp_path_factory):
    root, source, _, path, receipt = evidence
    outside = tmp_path_factory.mktemp("outside") / "result.md"
    outside.write_text("claimed result")
    target = root / receipt["artifacts"]["review"]["path"]
    target.unlink()
    target.symlink_to(outside)
    receipt["artifacts"]["review"]["sha256"] = hashlib.sha256(outside.read_bytes()).hexdigest()
    path.write_text(json.dumps(receipt))
    assert gate.check(root, [source])


def test_git_diff_checks_both_sides_of_a_rename(gate, tmp_path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args], text=True).strip()
    git("init", "-q")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    put(tmp_path, "claude/commands/old.md", "existing command")
    git("add", ".")
    git("commit", "-qm", "baseline")
    base = git("rev-parse", "HEAD")
    git("mv", "claude/commands/old.md", "claude/commands/new.md")
    git("commit", "-qm", "rename")
    changed = gate.changed_paths(tmp_path, base, "HEAD")
    assert set(changed) == {"claude/commands/old.md", "claude/commands/new.md"}
    assert len(gate.check(tmp_path, changed)) == 2
