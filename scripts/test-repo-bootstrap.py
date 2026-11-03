#!/usr/bin/env python3
"""One acceptance workflow: share a bootstrap, then retrofit and upgrade locally."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


SOURCE = Path(__file__).resolve().parents[1]


def run(command, cwd=None, expected=0):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    assert result.returncode == expected, (command, result.stdout, result.stderr)
    return result.stdout + result.stderr


def git(root, *args):
    return run(["git", "-C", str(root), "-c", "core.hooksPath=/dev/null",
                "-c", "commit.gpgsign=false", "-c", "user.name=Bootstrap acceptance",
                "-c", "user.email=bootstrap@example.invalid", *args]).strip()


def tree(root):
    return {str(path.relative_to(root)): (os.readlink(path) if path.is_symlink() else path.read_bytes())
            for path in root.rglob("*") if path.is_symlink() or path.is_file()}


with tempfile.TemporaryDirectory(prefix="repo-bootstrap-acceptance-") as temporary:
    # macOS commonly exposes its temporary directory through /var -> /private/var.
    workspace = Path(temporary).resolve()
    # A private source copy lets the workflow exercise a real subsequent update.
    source = workspace / "dotfiles"
    (source / "bin").mkdir(parents=True)
    shutil.copy2(SOURCE / "bin/repo-bootstrap", source / "bin/repo-bootstrap")
    shutil.copytree(SOURCE / "ai", source / "ai")
    shutil.copytree(SOURCE / "docs", source / "docs", symlinks=True)
    cli = source / "bin/repo-bootstrap"
    project = workspace / "new repository"

    def install(target, *args, expected=0):
        return run([str(cli), "--repo", str(target), *args], expected=expected)

    install(project, "--init", "--dry-run")
    assert not project.exists(), "preview initialized the target"
    install(project, "--init", "--mode", "tracked")
    nested = project / "not-yet-created"
    assert "nested repository" in install(nested, "--init", "--dry-run", expected=1)
    assert not nested.exists()
    assert (project / ".github/pull_request_template.md").is_file()
    assert (project / ".agents/skills/architecture/SKILL.md").is_file()
    assert (project / ".claude/skills/builder").resolve() == project / ".agents/skills/builder"
    before = tree(project)
    assert "already current" in install(project)
    assert tree(project) == before
    assert not git(project, "diff", "--cached", "--name-only"), "installer staged files"
    git(project, "add", ".agents", ".claude", ".github")
    git(project, "commit", "-qm", "Adopt repository guidance")
    shared = workspace / "colleague checkout"
    run(["git", "clone", "--quiet", str(project), str(shared)])
    assert (shared / ".claude/skills/pr-writer/SKILL.md").is_file()
    # Follow actual local Markdown resource links after cloning, without dotfiles.
    for path in (shared / ".agents/skills").rglob("*.md"):
        text = path.read_text()
        assert "~/.files/" not in text and "~/.local/share/software-standards/" not in text, path
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if "://" not in link and not link.startswith("#"):
                assert (path.parent / link.split("#", 1)[0]).exists(), (path, link)
    run(["python3", "scripts/check_examples.py"], cwd=shared / ".agents/skills/builder")

    # Retrofit an existing linked worktree, retaining its instructions/template.
    existing = workspace / "existing repository"
    existing.mkdir()
    git(existing, "init", "--quiet")
    (existing / "AGENTS.md").write_text("Keep this project's own instructions.\n")
    (existing / "PULL_REQUEST_TEMPLATE.txt").write_text("Required project review fields.\n")
    git(existing, "add", ".")
    git(existing, "commit", "-qm", "Existing project policy")
    worktree = workspace / "retrofit worktree"
    git(existing, "worktree", "add", "--quiet", "--detach", str(worktree))
    before = tree(worktree)
    assert "existing PR template" in install(worktree, expected=1)
    assert tree(worktree) == before, "conflicting retrofit partially wrote files"
    exclude = existing / ".git/info/exclude"
    exclude.write_text(exclude.read_text() + "\n/scratch-notes\n")
    original_exclude = exclude.read_text()
    install(worktree, "--mode", "local")
    run(["python3", "scripts/check_examples.py"], cwd=worktree / ".agents/skills/builder")
    # A smaller local install in a sibling must not expose this one's packages.
    install(existing, "--mode", "local", "--skills", "builder", "--agents", "codex", "--pr-template", "none")
    assert not git(worktree, "status", "--porcelain", "--untracked-files=all")
    assert (worktree / "AGENTS.md").read_text() == "Keep this project's own instructions.\n"
    assert (worktree / "PULL_REQUEST_TEMPLATE.txt").read_text() == "Required project review fields.\n"
    assert exclude.read_text().startswith(original_exclude)
    assert (worktree / ".agents/templates/pull_request_template.md").is_file()

    # An update refreshes unchanged files but protects a locally customized skill.
    builder = worktree / ".agents/skills/builder/SKILL.md"
    builder.write_text(builder.read_text() + "\nLocal construction guidance.\n")
    local_builder = builder.read_bytes()
    upstream = source / "ai/skills/builder/references/construction.md"
    upstream.write_text(upstream.read_text() + "\nUpdated construction clarification.\n")
    before = tree(worktree)
    assert "preserving existing or locally modified" in install(worktree, expected=1)
    assert tree(worktree) == before
    install(worktree, "--conflict", "skip")
    assert builder.read_bytes() == local_builder
    assert (worktree / ".agents/skills/builder/references/construction.md").read_bytes() == upstream.read_bytes()
    install(worktree, "--conflict", "replace")
    backups = list((existing / ".git/repo-bootstrap/backups").glob("replace-*/.agents/skills/builder/SKILL.md"))
    assert len(backups) == 1 and backups[0].read_bytes() == local_builder
    assert "already current" in install(worktree)
    assert not git(worktree, "status", "--porcelain", "--untracked-files=all")

    # Local exclusions must really win; negation must fail before new writes.
    (worktree / ".gitignore").write_text("!/.agents/repo-bootstrap.json\n")
    before = tree(worktree)
    assert "prevent local exclusion" in install(worktree, expected=1)
    assert tree(worktree) == before
    (worktree / ".gitignore").unlink()
    install(worktree, "--mode", "tracked", "--pr-template", "none")
    assert exclude.read_text() == original_exclude
    assert ".agents/" in git(worktree, "status", "--porcelain")
    git(worktree, "add", ".agents", ".claude")
    before = tree(worktree)
    assert "cannot hide tracked" in install(worktree, "--mode", "local", expected=1)
    assert tree(worktree) == before

print("PASS: portable tracked bootstrap and safe local worktree retrofit/update through the real CLI")
