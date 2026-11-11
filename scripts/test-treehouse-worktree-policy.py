#!/usr/bin/env python3
"""Exercise native Treehouse allocation and reuse through patched Git hooks."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
POLICY = Path(os.environ.get("GIT_WORKTREE_POLICY_BINARY", ROOT / "bin/git-worktree-policy"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git", required=True, type=Path, help="patched runtime's bin/git")
    args = parser.parse_args()
    if not args.git.is_file() or not os.access(args.git, os.X_OK):
        parser.error("--git must name an executable patched Git runtime")
    git_binary = args.git.absolute()
    treehouse = shutil.which("treehouse")
    assert treehouse, "install native Treehouse before running this detector"
    with tempfile.TemporaryDirectory(prefix="treehouse-policy-", dir="/tmp") as temporary:
        root = Path(temporary).resolve()
        home, repo = root / "home", root / "project"
        home.mkdir()
        repo.mkdir()
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("GIT_", "TREEHOUSE_"))}
        env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
                   XDG_STATE_HOME=str(home / ".local/state"),
                   PATH=str(git_binary.parent) + os.pathsep + os.environ["PATH"],
                   GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(ROOT / "git/gitconfig"),
                   GIT_TERMINAL_PROMPT="0", TREEHOUSE_NO_UPDATE_CHECK="1")

        activation = home / ".config/dotfiles/worktree-policy.gitconfig"
        activation.parent.mkdir(parents=True)
        activation.write_text("".join(f'[hook "worktree-policy-{event}"]\n enabled = true\n' for event in ("pre", "post", "checkout")))
        (home / ".local/bin").mkdir(parents=True)
        (home / ".local/bin/git-worktree-policy").symlink_to(POLICY)
        (home / ".local/bin/git-worktree-policy-hook").symlink_to(ROOT / "bin/git-worktree-policy-hook")

        def run(*argv, cwd=repo, check=True):
            result = subprocess.run([str(arg) for arg in argv], cwd=cwd, env=env,
                                    capture_output=True, text=True, timeout=90)
            if check and result.returncode:
                raise AssertionError(f"{argv}: {result.returncode}\n{result.stdout}\n{result.stderr}")
            return result

        def git(*argv, **kwargs):
            return run(git_binary, *argv, **kwargs)

        def get(branch, check=True):
            return run(treehouse, "get", "--root", ".pool", "--lease", "--json",
                       "--no-fetch", "--base", "main", "--branch", branch,
                       "--lease-holder", "native-policy-detector", check=check)

        def status():
            return json.loads(run(POLICY, "refresh").stdout)

        git("init", "--initial-branch=main")
        git("config", "user.name", "Native Policy Test")
        git("config", "user.email", "native-policy@example.invalid")
        (repo / ".gitignore").write_text(".pool/\n")
        (repo / "tracked.txt").write_text("preserved checkout data\n")
        git("add", ".gitignore", "tracked.txt")
        git("commit", "-m", "initial")
        custom_hooks = root / "existing hooks"
        custom_hooks.mkdir()
        hook_log = root / "existing-hook-events"
        hook = custom_hooks / "post-checkout"
        hook.write_text(f'#!/bin/sh\nprintf "checkout\\n" >> "{hook_log}"\n')
        hook.chmod(0o755)
        git("config", "core.hooksPath", str(custom_hooks))
        before_hooks = hook.read_bytes()
        git("checkout", "main")
        assert hook_log.read_text().splitlines() == ["checkout"]
        git("config", "worktree.limit", "2")
        first = json.loads(get("feature/first").stdout)
        first_path = Path(first["path"])
        external = root / "external checkout"
        previous_events = len(hook_log.read_text().splitlines())
        git("worktree", "add", "--detach", external)
        inventory_file = repo / ".git/worktree-policy/inventory.json"
        assert json.loads(inventory_file.read_text())["linked_count"] == 2
        assert len(hook_log.read_text().splitlines()) == previous_events + 1
        assert hook.read_bytes() == before_hooks
        assert not (repo / ".git/hooks/post-checkout").exists()
        assert status()["linked_count"] == 2
        denied = get("feature/blocked", check=False)
        assert denied.returncode != 0 and "refusing add" in denied.stderr, denied
        assert status()["linked_count"] == 2
        assert git("show-ref", "--verify", "refs/heads/feature/blocked", check=False).returncode != 0
        assert (external / "tracked.txt").read_text() == "preserved checkout data\n"
        run(treehouse, "return", first_path, "--root", ".pool",
            "--if-lease-id", first["lease_id"],
            "--if-lease-holder", first["lease_holder"])
        second = json.loads(get("feature/reused").stdout)
        assert Path(second["path"]) == first_path, "full repository prevented native pool reuse"
        assert second["lease_id"] != first["lease_id"]
        assert status()["linked_count"] == 2
        git("config", "--unset", "worktree.limit")
        git("config", "worktree.maxBytes", "1")
        (external / "ignored-build.bin").write_bytes(b"x" * 65536)
        denied = get("feature/disk-blocked", check=False)
        assert denied.returncode != 0 and "repository allocated bytes" in denied.stderr, denied
        assert status()["linked_count"] == 2
        git("config", "--unset", "worktree.maxBytes")
        run(POLICY, "configure", "--global", "--max-bytes", "1")
        denied = get("feature/global-disk-blocked", check=False)
        assert denied.returncode != 0 and "global allocated bytes" in denied.stderr, denied
        assert status()["linked_count"] == 2
        inventory = json.loads(run(POLICY, "status", "--all").stdout)
        assert inventory["totals"]["linked_count"] == 2
        assert inventory["totals"]["disk_bytes"] >= 65536
        run(POLICY, "configure", "--global", "--max-bytes", "off")
        third = json.loads(get("feature/limits-disabled").stdout)
        assert Path(third["path"]) != first_path
        assert status()["linked_count"] == 3
        for lease in (second, third):
            run(treehouse, "return", lease["path"], "--root", ".pool",
                "--if-lease-id", lease["lease_id"],
                "--if-lease-holder", lease["lease_holder"])
        assert (external / "ignored-build.bin").stat().st_size == 65536
        assert (repo / "tracked.txt").read_text() == "preserved checkout data\n"
        fixture = root / "dotfiles"
        fixture.mkdir()
        for name in ("Makefile", "scripts", "config", "bootstrap", "git", "bin", "design-system"):
            (fixture / name).symlink_to(ROOT / name)
        git("init", "-q", fixture)
        machine = home / "machine.toml"
        machine.write_text('[tools]\nworktree-policy = false\n')
        env["DOTFILES_CONFIG"] = str(machine)
        run("make", "--no-print-directory", "configure", "SELECTED_TARGETS=git", cwd=fixture)
        assert git("config", "--file", activation, "--get", "hook.worktree-policy-pre.enabled").stdout.strip() == "false"
        installed = home / ".local/bin/git-worktree-policy"
        assert installed.resolve() == ROOT / "bin/git-worktree-policy"
        assert not (home / ".local/libexec/git-worktree-policy").exists()
        disabled_repo = root / "disabled policy repo"
        git("init", "-q", disabled_repo)
        git("worktree", "add", "--orphan", root / "disabled-policy-linked", cwd=disabled_repo)
        machine.write_text('[tools]\nworktree-policy = true\n')
        run("make", "--no-print-directory", "configure", "SELECTED_TARGETS=git", cwd=fixture)
        missing = git("worktree", "add", "--orphan", root / "missing-policy-linked", cwd=disabled_repo, check=False)
        assert missing.returncode != 0 and "native policy is unavailable" in missing.stderr
    print("Native Treehouse allocation, full-pool reuse, and optional disk gates passed")


if __name__ == "__main__":
    main()
