#!/usr/bin/env python3
"""Preserve real WIP snapshots remotely before removing approved worktrees."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    tool = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (
        Path(__file__).resolve().parents[1] / "bin/git-worktree-cleanup"
    )
    with tempfile.TemporaryDirectory(prefix="worktree-wip-push-check-") as folder:
        temporary = Path(folder).resolve()
        root = temporary / "src"
        root.mkdir()
        repo = root / "sandbox"
        denied = root / "personal"
        remote = temporary / "remote.git"
        checkout = repo / ".worktrees/unfinished task"
        private_checkout = denied / ".worktrees/private"
        approved_url = "https://github.com/easypost-sandbox/cleanup-fixture.git"
        calls = temporary / "push-calls"
        edit_during_push = temporary / "edit-during-push"
        wrappers = temporary / "wrappers"
        wrappers.mkdir()
        env = {
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "NO_COLOR": "1", "XDG_CACHE_HOME": str(temporary / "cache"),
            "CODEX_HOME": str(temporary / "codex"),
            "PATH": str(wrappers) + os.pathsep + os.environ["PATH"],
            "WORKTREE_TEST_GIT": shutil.which("git"),
            "WORKTREE_TEST_URL": approved_url,
            "WORKTREE_TEST_REMOTE": str(remote),
            "WORKTREE_TEST_CALLS": str(calls),
            "WORKTREE_TEST_EDIT": str(edit_during_push),
            "WORKTREE_TEST_CHECKOUT": str(checkout),
        }
        for name in ("WORKTREE_CLEANUP_BASE_BRANCH", "WORKTREE_CLEANUP_AGE_HOURS",
                     "GIT_AUTHOR_DATE", "GIT_COMMITTER_DATE"):
            env.pop(name, None)
        git_wrapper = wrappers / "git"
        # Map only publication/verification transport to a real local bare
        # repository. Native get-url still validates the configured GitHub URL,
        # and pushes, rejection hooks, objects, and refs are real Git operations.
        git_wrapper.write_text("#!" + sys.executable + "\n" + """
import os
from pathlib import Path
import subprocess
import sys

args = sys.argv[1:]
command = args[2] if args[:1] == ["-C"] else args[0]
if (command in ("push", "ls-remote") and "--get-url" not in args
        and os.environ["WORKTREE_TEST_URL"] in args):
    args[args.index(os.environ["WORKTREE_TEST_URL"])] = os.environ["WORKTREE_TEST_REMOTE"]
    if command == "push":
        with open(os.environ["WORKTREE_TEST_CALLS"], "a") as log:
            log.write(" ".join(args) + "\\n")
        result = subprocess.run([os.environ["WORKTREE_TEST_GIT"], *args])
        edit = Path(os.environ["WORKTREE_TEST_EDIT"])
        if result.returncode == 0 and edit.exists():
            Path(os.environ["WORKTREE_TEST_CHECKOUT"], "late.txt").write_text(
                "work created while publishing\\n")
            edit.unlink()
        sys.exit(result.returncode)
os.execv(os.environ["WORKTREE_TEST_GIT"], ["git", *args])
""")
        git_wrapper.chmod(0o755)

        def git(path, *args, old=False):
            return subprocess.check_output(
                [env["WORKTREE_TEST_GIT"], "-C", str(path), *args],
                env={**env, **({
                    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
                    "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
                } if old else {})}, text=True,
            ).strip()

        def project(path):
            path.mkdir()
            git(path, "init", "-q", "--initial-branch", "trunk")
            git(path, "config", "user.name", "WIP cleanup check")
            git(path, "config", "user.email", "cleanup@example.invalid")
            git(path, "config", "commit.gpgsign", "false")
            (path / ".gitignore").write_text(".worktrees/\nnode_modules/\n")
            (path / "source.txt").write_text("original source\n")
            (path / "removed.txt").write_text("remove in WIP\n")
            git(path, "add", ".")
            git(path, "commit", "-qm", "Initialize WIP fixture", old=True)

        def scan(*args, status=0):
            result = subprocess.run(
                ["/bin/bash", str(tool), *args, str(root)], cwd=temporary,
                env=env, text=True, capture_output=True, timeout=60,
            )
            assert result.returncode == status, result.stdout + result.stderr
            return result.stdout + result.stderr

        project(repo)
        project(denied)
        git(temporary, "init", "-q", "--bare", str(remote))
        git(repo, "remote", "add", "origin", approved_url)
        git(denied, "remote", "add", "origin", approved_url)
        git(denied, "remote", "set-url", "--push", "origin",
            "https://github.com/personal-owner/private-fixture.git")
        git(repo, "worktree", "add", "--detach", str(checkout))
        git(denied, "worktree", "add", "--detach", str(private_checkout))
        (private_checkout / "private.txt").write_text("leave this work alone\n")
        # Start with an unmerged detached commit, then mixed tracked/untracked
        # edits and a disposable ignored dependency.
        (checkout / "unmerged.txt").write_text("detached committed work\n")
        git(checkout, "add", "unmerged.txt")
        git(checkout, "commit", "-qm", "Unmerged work", old=True)
        original_head = git(checkout, "rev-parse", "HEAD")
        (checkout / "source.txt").write_text("unfinished source\n")
        (checkout / "new.txt").write_text("untracked source\n")
        (checkout / "removed.txt").unlink()
        (checkout / "node_modules").mkdir()
        (checkout / "node_modules/disposable").write_bytes(b"x" * 65536)
        original_status = git(checkout, "status", "--porcelain")

        preview = scan("--wip-push")
        assert preview.count("DISK USAGE") == 1 and "PUSH TO" in preview, preview
        assert "wip-push" in preview and "commit WIP" in preview, preview
        assert "no easypost-sandbox push remote" in preview, preview
        assert "1 worktree(s) would be removed" in preview, preview
        assert git(checkout, "rev-parse", "HEAD") == original_head
        assert git(checkout, "status", "--porcelain") == original_status
        assert git(repo, "for-each-ref", "refs/heads/wip/cleanup/") == ""
        assert not calls.exists()

        # A URL can expand once into the allowed owner, then expand elsewhere
        # when that literal is used for publication. Such a chain must stay out.
        git(denied, "remote", "set-url", "--push", "origin", "shortcut:cleanup-fixture.git")
        git(denied, "config", "url.https://github.com/easypost-sandbox/.insteadOf", "shortcut:")
        git(denied, "config", "url.https://github.com/personal-owner/.insteadOf",
            "https://github.com/easypost-sandbox/")
        rewritten = scan("--wip-push")
        assert "push URL rewrites elsewhere" in rewritten, rewritten
        assert "1 worktree(s) would be removed" in rewritten, rewritten
        assert not calls.exists()

        rejection = remote / "hooks/pre-receive"
        rejection.write_text("#!/bin/sh\nexit 1\n")
        rejection.chmod(0o755)
        failed = scan("--wip-push", "-y", status=1)
        assert "WIP push failed" in failed and "Removed 0 worktree(s)" in failed, failed
        assert checkout.is_dir()
        first_branch = git(checkout, "symbolic-ref", "--short", "HEAD")
        first_head = git(checkout, "rev-parse", "HEAD")
        assert first_branch.startswith("wip/cleanup/") and first_head != original_head
        assert git(checkout, "status", "--porcelain") == ""
        assert git(checkout, "show", "HEAD:source.txt") == "unfinished source"
        assert git(checkout, "show", "HEAD:new.txt") == "untracked source"
        assert "removed.txt" not in git(checkout, "ls-tree", "--name-only", "HEAD").splitlines()
        assert git(remote, "for-each-ref", "refs/heads/") == ""

        rejection.unlink()
        edit_during_push.touch()
        changed = scan("--wip-push", "-a", "0", "-y", status=1)
        assert "Retaining" in changed and "dirty" in changed, changed
        assert checkout.is_dir() and (checkout / "late.txt").is_file()
        published_branch = git(checkout, "symbolic-ref", "--short", "HEAD")
        assert git(remote, "rev-parse", f"refs/heads/{published_branch}") == first_head

        result = scan("--wip-push", "-a", "0", "-y")
        assert "Removed 1 worktree(s)" in result, result
        assert not checkout.exists()
        assert str(checkout) not in git(repo, "worktree", "list", "--porcelain")
        branches = git(remote, "for-each-ref", "--format=%(refname)", "refs/heads/").splitlines()
        assert len(branches) == 2
        final_ref = next(ref for ref in branches if not ref.endswith(published_branch))
        assert git(remote, "show", f"{final_ref}:late.txt") == "work created while publishing"
        assert git(remote, "show", f"{final_ref}:unmerged.txt") == "detached committed work"
        assert git(remote, "show", f"{final_ref}:source.txt") == "unfinished source"
        assert git(remote, "show", f"{final_ref}:new.txt") == "untracked source"
        assert "removed.txt" not in git(remote, "ls-tree", "--name-only", final_ref).splitlines()
        assert git(repo, "rev-parse", final_ref) == git(remote, "rev-parse", final_ref)
        assert git(repo, "rev-parse", f"refs/heads/{first_branch}") == first_head
        assert private_checkout.is_dir()
        assert (private_checkout / "private.txt").read_text() == "leave this work alone\n"
        assert len(calls.read_text().splitlines()) == 3
        assert git(repo, "status", "--porcelain") == ""
    print("PASS: WIP cleanup validates push ownership, retains failed or changed "
          "checkouts, and verifies real remote snapshots before removal.")


if __name__ == "__main__":
    main()
