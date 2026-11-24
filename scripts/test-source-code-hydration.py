#!/usr/bin/env python3
"""Exercise worktree hydration through Git's real checkout hook."""
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[1]


def run(*args, cwd, expected=0, env):
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    assert result.returncode == expected, (args, result.stdout, result.stderr)
    return result.stdout + result.stderr


with tempfile.TemporaryDirectory(prefix="source-code-hydration-") as temporary:
    root = Path(temporary).resolve()
    home = root / "home"
    commands = home / ".local/bin"
    commands.mkdir(parents=True)
    repo = root / "repo"
    repo.mkdir()
    env = {**os.environ, "HOME": str(home), "GIT_CONFIG_GLOBAL": str(SOURCE / "git/gitconfig"), "GIT_CONFIG_NOSYSTEM": "1"}

    def git(*args, cwd=repo, expected=0):
        return run("git", "-c", "commit.gpgsign=false", "-c", "user.name=Hydration test",
                   "-c", "user.email=hydration@example.invalid", *args, cwd=cwd, expected=expected, env=env)

    def hydrate(path, *args, expected=0):
        return run(sys.executable, str(SOURCE / "bin/source-code"), "hydrate", "--repo", str(path),
                   *args, cwd=repo, env=env, expected=expected)

    git("init", "-q")
    (repo / "README.md").write_text("fixture\n")
    git("add", "README.md")
    git("commit", "-qm", "fixture")
    # Global Git configuration is safe before the optional integration is installed.
    assert git("config", "--get", "hook.source-code-checkout.enabled").strip() == "false"
    unconfigured = root / "unconfigured"
    git("worktree", "add", "-qb", "unconfigured", str(unconfigured))
    git("worktree", "remove", str(unconfigured))
    run("bash", str(SOURCE / "scripts/make/config.sh"), "source-code-config", str(SOURCE), str(home),
        "uv", "Darwin", cwd=repo, env=env)
    assert git("config", "--get", "hook.source-code-checkout.enabled").strip() == "true"
    # An unrelated repository receives no installation.
    hydrate(repo)
    assert not (repo / ".agents").exists()
    config = '''schema_version = 1
stage = "alpha"
authority = "owned"
adoption = "hold"
mode = "shadow"
skill_storage = "linked"
skills = ["builder"]
agents = "both"
pr_template = "none"
detect_languages = false
[checks.go]
enabled = false
[checks.protobuf]
enabled = false
'''
    (repo / "source-code.toml").write_text(config)
    run(sys.executable, str(SOURCE / "bin/source-code"), "setup", "--repo", str(repo),
        "--authority", "owned", "--adoption", "hold", cwd=repo, env=env)
    hooks = root / "hooks"
    hooks.mkdir()
    hook = hooks / "post-checkout"
    hook.write_text('#!/bin/sh\nexec "' + str(SOURCE / "bin/source-code-worktree-hook") + '" post-checkout "$@"\n')
    hook.chmod(0o755)
    supported = subprocess.run(["git", "hook", "list", "post-checkout"], cwd=repo, env=env,
                               text=True, capture_output=True).returncode == 0
    if not supported:
        git("config", "core.hooksPath", str(hooks))
    work = root / "work"
    git("worktree", "add", "-qb", "task", str(work))
    assert (work / ".agents/source-code.md").is_file()
    assert (work / ".claude/skills/builder/SKILL.md").is_file()
    assert json.loads((work / ".source-code.json").read_text())["stage"] == "alpha"
    assert git("status", "--porcelain", cwd=work) == ""
    before = (work / "source-code.toml").read_bytes()
    hydrate(work)
    assert before == (work / "source-code.toml").read_bytes()
    # A partially missing host installation must be restored by hydration.
    (work / ".claude/skills/builder").unlink()
    (work / ".claude/rules/source-code.md").unlink()
    hydrate(work)
    assert (work / ".claude/skills/builder/SKILL.md").is_file()
    assert (work / ".claude/rules/source-code.md").is_file()
    assert before == (work / "source-code.toml").read_bytes()
    # Target configuration wins over the primary checkout's shadow configuration.
    # Explicitly suppress global hooks when preparing manual hydration cases.
    git("config", "hook.source-code-checkout.enabled", "false")
    git("config", "hook.source-code-worktree.enabled", "false")
    second = root / "second"
    git("-c", "core.hooksPath=/dev/null", "worktree", "add", "-qb", "second", str(second))
    (second / "source-code.toml").write_text(config.replace('stage = "alpha"', 'stage = "production"'))
    hydrate(second, "--dry-run")
    assert not (second / ".agents").exists()
    hydrate(second)
    assert json.loads((second / ".source-code.json").read_text())["stage"] == "production"
    # A conflict fails before installing any guidance and retains authored content.
    third = root / "third"
    git("-c", "core.hooksPath=/dev/null", "worktree", "add", "-qb", "third", str(third))
    (third / "AGENTS.override.md").write_text("custom guidance\n")
    hydrate(third, expected=1)
    assert (third / "AGENTS.override.md").read_text() == "custom guidance\n"
    assert not (third / ".agents/repo-bootstrap.json").exists()
    git("config", "hook.source-code-checkout.enabled", "true")
    git("config", "hook.source-code-worktree.enabled", "true")
    deferred = root / "deferred"
    git("worktree", "add", "--no-checkout", "-qb", "deferred", str(deferred))
    # Exercise the patched lifecycle callback after a checkout-free creation.
    run(str(SOURCE / "bin/source-code-worktree-hook"), "post-worktree", "add", "fixture", "", str(deferred),
        cwd=repo, env=env)
    assert not (deferred / ".agents").exists()
    git("checkout", "HEAD", cwd=deferred)
    assert (deferred / ".agents/source-code.md").is_file()
    git("config", "hook.source-code-checkout.enabled", "false")
    git("config", "hook.source-code-worktree.enabled", "false")
    lifecycle = root / "lifecycle"
    git("-c", "core.hooksPath=/dev/null", "worktree", "add", "-qb", "lifecycle", str(lifecycle))
    run(str(SOURCE / "bin/source-code-worktree-hook"), "post-worktree", "add", "fixture", "", str(lifecycle),
        cwd=repo, env={**env, "GIT_DIR": str(repo / ".git"), "GIT_WORK_TREE": str(repo)})
    assert (lifecycle / ".agents/source-code.md").is_file()
    for path in (work, second, third, deferred, lifecycle):
        git("worktree", "remove", "--force", str(path))
print("source-code worktree hydration acceptance passed")
