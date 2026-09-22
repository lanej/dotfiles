#!/usr/bin/env python3
"""One regression workflow: install the real pin and enforce review in a Git worktree."""
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
    cli = str(root / "bin/ui-review")
    version = subprocess.check_output([cli, "--version"], env=env, text=True).strip()
    assert version == pin["version"], version
    decision = subprocess.check_output([cli, "hook"], input=json.dumps({"cwd": str(project)}), env=env, text=True)
    assert not decision.strip() or json.loads(decision) == {}, decision
    subprocess.run([cli, "init", "--project", str(project)], env=env, check=True)
    config_path = project / ".ui-review/config.json"
    config = json.loads(config_path.read_text())
    config["enforceOnStop"] = True
    config_path.write_text(json.dumps(config))
    decision = json.loads(subprocess.check_output([cli, "hook"], input=json.dumps({"cwd": str(project)}), env=env, text=True))
    assert decision.get("decision") == "block", decision

    git(project, "init", "-q")
    git(project, "commit", "--allow-empty", "-qm", "Application before review setup")
    # Nest the worktree below the configured checkout to detect accidental fallback.
    worktree = project / ".worktrees/feature checkout"
    git(project, "worktree", "add", "--detach", str(worktree))
    nested = worktree / "src"
    nested.mkdir()
    unconfigured = subprocess.check_output([cli, "hook"], input=json.dumps({"cwd": str(nested)}), env=env, text=True)
    assert not unconfigured.strip() or json.loads(unconfigured) == {}, unconfigured

    git(project, "add", ".ui-review/config.json", ".ui-review/rules.json", ".ui-review/.gitignore", "DESIGN.md")
    git(project, "commit", "-qm", "Commit review setup for worktrees")
    git(worktree, "checkout", "--detach", git(project, "rev-parse", "HEAD"))
    raw = subprocess.check_output([cli, "hook"], input=json.dumps({"cwd": str(nested)}), env=env, text=True)
    assert raw.strip(), "The wrapper silently skipped an opted-in worktree from its src directory"
    worktree_decision = json.loads(raw)
    assert worktree_decision.get("decision") == "block", worktree_decision
    assert worktree_decision.get("reason") == decision["reason"], worktree_decision
    print("PASS: pinned install launches; nested worktree hook finds committed setup and respects checkout boundaries.")
