#!/usr/bin/env python3
"""One regression workflow: install the real pin and verify review in a Git worktree."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent.parent
pin = json.loads((root / "claude/ui-review/tool.json").read_text())
with tempfile.TemporaryDirectory(prefix="viewrule-integration-") as temporary:
    project = Path(temporary) / "app"
    project.mkdir()
    env = {**os.environ, "VIEWRULE_INSTALL_ROOT": str(Path(temporary) / "install")}
    env.pop("VIEWRULE_DEV_DIR", None)
    cli = str(root / "bin/ui-review")
    # A stale Stop registration must be harmless even before installation.
    decision = subprocess.check_output([cli, "--project", str(project), "hook"], input="invalid old payload", env=env, text=True)
    assert json.loads(decision) == {}, decision

    def git(cwd, *args):
        return subprocess.check_output([
            "git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
            "-c", "user.name=Viewrule integration", "-c", "user.email=viewrule@example.invalid",
            *args,
        ], cwd=cwd, env=env, text=True).strip()

    install = ["python3", str(root / "scripts/install-viewrule.py"), "--skip-browser"]
    if env.get("VIEWRULE_ARCHIVE"):
        install += ["--archive", env["VIEWRULE_ARCHIVE"]]
    subprocess.run(install, env=env, check=True)
    version = subprocess.check_output([cli, "--version"], env=env, text=True).strip()
    assert version == pin["version"], version
    decision = subprocess.check_output([cli, "hook"], input=json.dumps({"cwd": str(project)}), env=env, text=True)
    assert not decision.strip() or json.loads(decision) == {}, decision
    subprocess.run([cli, "init", "--project", str(project)], env=env, check=True)
    config_path = project / ".ui-review/config.json"
    config = json.loads(config_path.read_text())
    config["enforceOnStop"] = True
    config["sourcePaths"] = ["src"]
    config["sourceChecks"][0]["targets"] = ["src"]
    config_path.write_text(json.dumps(config))
    decision = json.loads(subprocess.check_output([cli, "hook"], input=json.dumps({"cwd": str(project)}), env=env, text=True))
    assert decision == {}, decision
    (project / "DESIGN.md").write_text("# Design\n\nThe application helps operators compare shipment status and choose the next action.\n")
    verification = subprocess.run([cli, "verify", "--project", str(project)], env=env, text=True, capture_output=True)
    assert verification.returncode == 1, verification.stderr or verification.stdout
    missing_review = json.loads(verification.stdout)
    assert missing_review["status"] == "fail" and "missing, failing, or stale" in missing_review["reason"], missing_review

    git(project, "init", "-q")
    git(project, "commit", "--allow-empty", "-qm", "Application before review setup")
    # Nest the worktree below the configured checkout to detect accidental fallback.
    worktree = project / ".worktrees/feature checkout"
    git(project, "worktree", "add", "--detach", str(worktree))
    nested = worktree / "src"
    nested.mkdir()
    unconfigured = subprocess.run([cli, "verify"], cwd=nested, env=env, text=True, capture_output=True)
    assert unconfigured.returncode == 1, unconfigured.stderr or unconfigured.stdout
    unconfigured_review = json.loads(unconfigured.stdout)
    assert unconfigured_review["status"] == "fail" and "config.json" in unconfigured_review["reason"], unconfigured_review

    git(project, "add", ".ui-review/config.json", ".ui-review/rules.json", ".ui-review/.gitignore", "DESIGN.md")
    git(project, "commit", "-qm", "Commit review setup for worktrees")
    git(worktree, "checkout", "--detach", git(project, "rev-parse", "HEAD"))
    verification = subprocess.run([cli, "verify"], cwd=nested, env=env, text=True, capture_output=True)
    assert verification.returncode == 1, verification.stderr or verification.stdout
    assert json.loads(verification.stdout) == missing_review, verification.stdout
    # An unrelated staged file needs no UI evidence; a declared source change does.
    (worktree / "notes.txt").write_text("Backend planning\n")
    git(worktree, "add", "notes.txt")
    skipped = subprocess.run([cli, "pre-commit", "--project", str(worktree)], cwd=worktree, env=env, text=True, capture_output=True)
    assert skipped.returncode == 0, skipped.stderr or skipped.stdout
    assert json.loads(skipped.stdout)["status"] == "skip", skipped.stdout
    (nested / "page.html").write_text("<main>Shipment status</main>\n")
    git(worktree, "add", "src/page.html")
    gate = subprocess.run([cli, "pre-commit", "--project", str(worktree)], cwd=worktree, env=env, text=True, capture_output=True)
    assert gate.returncode == 1, gate.stderr or gate.stdout
    assert json.loads(gate.stdout)["status"] == "fail", gate.stdout
    print("PASS: pinned install launches; legacy Stop calls are harmless; nested worktree verification and scoped Git gates use committed setup.")
