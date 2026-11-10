#!/usr/bin/env python3
"""Exercise the policy through real Git hooks in isolated repositories."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "bin/git-worktree-policy"


def main():
    with tempfile.TemporaryDirectory(prefix="git-worktree-policy-") as temporary:
        root = Path(temporary).resolve()
        repo = root / "main repo"
        repo.mkdir()
        env = {**os.environ, "HOME": str(root), "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
               "XDG_STATE_HOME": str(root / "state")}
        for key in list(env):
            if key.startswith("GIT_") and key not in ("GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", "GIT_TERMINAL_PROMPT"):
                del env[key]

        def run(*args, cwd=repo, check=True, extra_env=None):
            result = subprocess.run([str(arg) for arg in args], cwd=cwd, env={**env, **(extra_env or {})},
                                    capture_output=True, text=True, timeout=30)
            if check and result.returncode:
                raise AssertionError(f"{args}: {result.returncode}\n{result.stdout}\n{result.stderr}")
            return result

        def git(*args, **kwargs):
            return run("git", *args, **kwargs)

        def state():
            return json.loads(run(POLICY, "refresh").stdout)

        git("init", "--initial-branch=main")
        git("config", "user.name", "Policy Test")
        git("config", "user.email", "policy@example.invalid")
        git("commit", "--allow-empty", "-m", "initial")
        hooks = repo / ".git/hooks"
        previous = hooks / "post-checkout"
        log = root / "forwarded"
        previous.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" >> "{log}"\nexit 7\n')
        previous.chmod(0o755)
        run(POLICY, "install")
        installed = previous.read_bytes()
        run(POLICY, "install")
        assert previous.read_bytes() == installed
        assert state()["linked_count"] == 0
        assert run(POLICY, "preflight").returncode == 0
        git("config", "worktree.limit", "1")
        first = root / "linked with spaces"
        result = git("worktree", "add", "-b", "first", first, check=False)
        assert result.returncode == 7, result
        assert log.read_text().splitlines()[-1] == "1"
        snapshot = json.loads((repo / ".git/worktree-policy/inventory.json").read_text())
        assert snapshot["linked_count"] == 1
        assert snapshot["worktrees"][1]["worktree"] == str(first)
        assert "limit is 1" in result.stderr
        assert run(POLICY, "preflight", check=False).returncode == 1
        assert run(POLICY, "preflight", cwd=first, check=False).returncode == 1
        native = run(POLICY, "hook", "pre-worktree", "add", "", "", str(root / "blocked"), check=False)
        assert native.returncode == 1 and "refusing add" in native.stderr
        assert not (root / "blocked").exists()
        assert run(POLICY, "hook", "pre-worktree", "remove", "first", str(first), "").returncode == 0
        checkout = git("checkout", "main", check=False)
        assert checkout.returncode != 0, checkout
        assert state()["linked_count"] == 1
        original = hooks / "post-checkout.worktree-policy-original"
        original.chmod(0o644)
        assert git("checkout", "main").returncode == 0
        original.chmod(0o755)
        second = root / "no checkout\nwith newline"
        git("worktree", "add", "--no-checkout", "-b", "second", second)
        assert state()["linked_count"] == 2
        assert any(row["worktree"] == str(second) for row in state()["worktrees"])
        moved = root / "moved"
        git("worktree", "move", second, moved)
        run(POLICY, "hook", "post-worktree", "move", "second", str(second), str(moved))
        assert any(row["worktree"] == str(moved) for row in state()["worktrees"])
        git("worktree", "remove", "--force", moved)
        run(POLICY, "hook", "post-worktree", "remove", "second", str(moved), "")
        assert state()["linked_count"] == 1
        shutil.rmtree(first)
        git("worktree", "prune", "--expire", "now")
        run(POLICY, "hook", "post-worktree", "prune", "first", str(first), "")
        assert state()["linked_count"] == 0
        git("config", "worktree.limit", "0")
        assert run(POLICY, "preflight", check=False).returncode == 1
        git("config", "--unset", "worktree.limit")
        assert run(POLICY, "hook", "pre-worktree", "add", "", "", str(first)).returncode == 0
        git("config", "worktree.limit", "invalid")
        assert run(POLICY, "preflight", check=False).returncode == 1
        # WHY: Invalid policy must never turn ordinary checkout into an admission gate.
        checkout = git("checkout", "main", check=False)
        assert checkout.returncode != 0 and "nonnegative integer" in checkout.stderr
        git("config", "--unset", "worktree.limit")
        budget_tree = root / "budget tree"
        git("worktree", "add", "--no-checkout", "-b", "budget", budget_tree)
        payload = budget_tree / "ignored build output"
        payload.write_bytes(os.urandom(32768))
        outside = root / "outside payload"
        outside.write_bytes(os.urandom(1024 * 1024))
        (budget_tree / "external symlink").symlink_to(outside)
        os.link(payload, budget_tree / "hardlink")
        git("config", "worktree.maxBytes", "1B")
        assert "repository allocated bytes" in run(POLICY, "preflight", check=False).stderr
        moved_budget = root / "temporarily moved tree"
        budget_tree.rename(moved_budget)
        denied = run(POLICY, "preflight", check=False)
        assert denied.returncode == 1 and "No such file" in denied.stderr
        original.chmod(0o644)
        checkout = git("checkout", "main")
        assert "No such file" in checkout.stderr
        original.chmod(0o755)
        moved_budget.rename(budget_tree)
        other = root / "other repo"
        git("init", "--initial-branch=main", other)
        assert run(POLICY, "preflight", cwd=other).returncode == 0
        git("config", "--unset", "worktree.maxBytes")
        git("config", "worktree.limit", "1")
        assert run(POLICY, "preflight", check=False).returncode == 1
        assert run(POLICY, "preflight", cwd=other).returncode == 0
        git("config", "--unset", "worktree.limit")
        run(POLICY, "configure", "--global", "--max-bytes", "1KiB")
        denied = run(POLICY, "preflight", cwd=other, check=False)
        assert denied.returncode == 1 and "global allocated bytes" in denied.stderr
        run(POLICY, "configure", "--global", "--max-bytes", "off", "--max-worktrees", "1")
        assert run(POLICY, "preflight", cwd=other, check=False).returncode == 1
        report = json.loads(run(POLICY, "status", "--all", cwd=root).stdout)
        assert report["complete"] and len(report["repositories"]) == 2
        assert report["totals"]["linked_count"] == 1
        assert payload.stat().st_blocks * 512 <= report["totals"]["disk_bytes"] < outside.stat().st_blocks * 512
        run(POLICY, "configure", "--global", "--max-worktrees", "off")
        assert run(POLICY, "preflight", cwd=other).returncode == 0
        missing = root / "temporarily unavailable"
        other.rename(missing)
        report = json.loads(run(POLICY, "status", "--all", check=False).stdout)
        assert not report["complete"]
        absent = [record for record in report["repositories"] if not record["available"]]
        assert len(absent) == 1 and absent[0]["common_gitdir"] == str(other / ".git")
        run(POLICY, "configure", "--global", "--max-worktrees", "10")
        assert "cannot evaluate global budget" in run(POLICY, "preflight", check=False).stderr
        assert payload.exists() and outside.exists()
        run(POLICY, "refresh", cwd=missing)
        other.symlink_to(missing, target_is_directory=True)
        redirected = json.loads(run(POLICY, "status", "--all", check=False).stdout)
        historical = next(record for record in redirected["repositories"] if record["common_gitdir"] == str(other / ".git"))
        assert not historical["available"] and "resolves elsewhere" in historical["error"]
        assert not redirected["complete"]
        assert next(record for record in redirected["repositories"] if record["common_gitdir"] == str(missing / ".git"))["available"]
        retired = json.loads(run(POLICY, "forget", other / ".git").stdout)
        assert retired["forgotten_common_gitdir"] == str(other / ".git")
        assert not Path(retired["removed_registry_record"]).exists()
        assert run(POLICY, "preflight").returncode == 0
        reconciled = json.loads(run(POLICY, "status", "--all").stdout)
        assert reconciled["complete"] and reconciled["totals"]["linked_count"] == 1
        registered = reconciled["repositories"]
        assert {record["common_gitdir"] for record in registered} == {str(repo / ".git"), str(missing / ".git")}
        assert (missing / ".git/config").exists() and payload.exists()
        assert run(POLICY, "forget", other / ".git", check=False).returncode == 1
        run(POLICY, "configure", "--global", "--max-worktrees", "off")
        other.unlink()
        missing.rename(other)
        run(POLICY, "forget", missing / ".git")
        run(POLICY, "refresh", cwd=other)
        active_hooks = previous.read_bytes()
        active_config = (repo / ".git/config").read_bytes()
        run(POLICY, "forget", repo / ".git")
        assert previous.read_bytes() == active_hooks
        assert (repo / ".git/config").read_bytes() == active_config
        assert payload.exists() and (repo / ".git/worktree-policy/inventory.json").exists()
        assert len(json.loads(run(POLICY, "status", "--all").stdout)["repositories"]) == 1
        run(POLICY, "hook", "post-worktree", "add", "budget", "", str(budget_tree))
        assert len(json.loads(run(POLICY, "status", "--all").stdout)["repositories"]) == 2
        custom = root / "custom hooks"
        custom.mkdir()
        git("config", "core.hooksPath", "../custom hooks")
        result = run(POLICY, "install", check=False)
        assert result.returncode == 1 and "core.hooksPath" in result.stderr
        assert not list(custom.iterdir())
        assert git("config", "--get", "core.hooksPath").stdout.strip() == "../custom hooks"
        git("config", "--unset", "core.hooksPath")
        git("config", "extensions.worktreeConfig", "true")
        git("config", "--worktree", "core.hooksPath", str(custom))
        assert run(POLICY, "install", check=False).returncode == 1
        assert not list(custom.iterdir())
        git("config", "user.name", "Policy Test", cwd=other)
        git("config", "user.email", "policy@example.invalid", cwd=other)
        git("commit", "--allow-empty", "-m", "initial", cwd=other)
        git("config", "extensions.worktreeConfig", "true", cwd=other)
        git("config", "--worktree", "policy.keep", "main setting", cwd=other)
        other_linked = root / "inactive linked worktree"
        git("worktree", "add", "-b", "inactive", other_linked, cwd=other)
        git("config", "--worktree", "policy.keep", "linked setting", cwd=other_linked)
        linked_config = Path(git("rev-parse", "--path-format=absolute", "--git-path", "config.worktree", cwd=other_linked).stdout.strip())
        config_files = (other / ".git/config", other / ".git/config.worktree", linked_config)
        before = {path: path.read_bytes() for path in config_files}
        run(POLICY, "install", cwd=other)
        assert {path: path.read_bytes() for path in config_files} == before
        assert git("checkout", "main", cwd=other).returncode == 0
        git("config", "--worktree", "core.hooksPath", "../custom hooks", cwd=other_linked)
        (other / ".git/hooks/post-worktree").unlink()
        before = {path: path.read_bytes() for path in config_files}
        installed_hooks = {path: path.read_bytes() for path in (other / ".git/hooks").iterdir() if path.is_file()}
        rejected = run(POLICY, "install", cwd=other, check=False)
        assert rejected.returncode == 1 and "core.hooksPath" in rejected.stderr
        assert {path: path.read_bytes() for path in config_files} == before
        assert {path: path.read_bytes() for path in (other / ".git/hooks").iterdir() if path.is_file()} == installed_hooks
        env_repo = root / "environment invoking repo"
        env_other = root / "environment other repo"
        for directory in (env_repo, env_other):
            git("init", "--initial-branch=main", directory)
            git("config", "user.name", "Policy Test", cwd=directory)
            git("config", "user.email", "policy@example.invalid", cwd=directory)
            git("commit", "--allow-empty", "-m", "initial", cwd=directory)
        env_a = root / "environment invoking linked"
        env_b = root / "environment other linked one"
        env_c = root / "environment other linked two"
        git("worktree", "add", "--no-checkout", "-b", "a", env_a, cwd=env_repo)
        for branch, directory in (("b", env_b), ("c", env_c)):
            git("worktree", "add", "--no-checkout", "-b", branch, directory, cwd=env_other)
        (env_a / "build").write_bytes(os.urandom(32768))
        (env_b / "build").write_bytes(os.urandom(131072))
        (env_c / "build").write_bytes(os.urandom(65536))
        run(POLICY, "install", cwd=env_repo)
        run(POLICY, "refresh", cwd=env_other)
        clean = json.loads(run(POLICY, "status", "--all", cwd=env_repo).stdout)
        hook_env = {"GIT_COMMON_DIR": str(env_repo / ".git"),
                    "GIT_DIR": str(env_repo / ".git"), "GIT_WORK_TREE": str(env_repo),
                    "GIT_INDEX_FILE": str(env_repo / ".git/nondefault-index")}
        contaminated = json.loads(run(POLICY, "status", "--all", cwd=env_repo, extra_env=hook_env).stdout)
        assert contaminated["totals"] == clean["totals"]
        by_directory = {record["common_gitdir"]: record for record in contaminated["repositories"]}
        assert by_directory[str(env_repo / ".git")]["inventory"]["linked_count"] == 1
        assert by_directory[str(env_other / ".git")]["inventory"]["linked_count"] == 2
        assert by_directory[str(env_other / ".git")]["disk_bytes"] > by_directory[str(env_repo / ".git")]["disk_bytes"]
        cached = json.loads((env_other / ".git/worktree-policy/inventory.json").read_text())
        assert cached["linked_count"] == 2
        assert {row["worktree"] for row in cached["worktrees"][1:]} == {str(env_b), str(env_c)}
        run(POLICY, "configure", "--global", "--max-worktrees", str(clean["totals"]["linked_count"]))
        denied = run(POLICY, "preflight", cwd=env_repo, extra_env=hook_env, check=False)
        assert denied.returncode == 1 and "global linked worktrees" in denied.stderr
        denied = run(POLICY, "hook", "pre-worktree", "add", "", "", str(root / "environment blocked"),
                     cwd=env_repo, extra_env=hook_env, check=False)
        assert denied.returncode == 1 and "global linked worktrees" in denied.stderr
        run(POLICY, "configure", "--global", "--max-worktrees", "off", "--max-bytes", str(clean["totals"]["disk_bytes"]))
        denied = run(POLICY, "preflight", cwd=env_repo, extra_env=hook_env, check=False)
        assert denied.returncode == 1 and "global allocated bytes" in denied.stderr
        git("config", "extensions.worktreeConfig", "true", cwd=env_repo)
        global_policy = root / "deliberate global git policy"
        included_policy = root / "conditional hook policy"
        git("config", "--file", included_policy, "core.hooksPath", str(custom))
        linked_gitdir = git("rev-parse", "--absolute-git-dir", cwd=env_a).stdout.strip()
        git("config", "--file", global_policy, f"includeIf.gitdir:{linked_gitdir}.path", included_policy)
        rejected = run(POLICY, "install", cwd=env_repo,
                       extra_env={**hook_env, "GIT_CONFIG_GLOBAL": str(global_policy)}, check=False)
        assert rejected.returncode == 1 and "core.hooksPath" in rejected.stderr and linked_gitdir in rejected.stderr
        print("git-worktree-policy: real stock-Git fallback, forwarding, inventory, and admission checks passed")


if __name__ == "__main__":
    main()
