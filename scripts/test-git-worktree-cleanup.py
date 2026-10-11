#!/usr/bin/env python3
"""Sweep real repositories, removing idle merged worktrees and retaining work."""
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
    env = {
        **os.environ,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
        "NO_COLOR": "1",
    }
    env.pop("WORKTREE_CLEANUP_BASE_BRANCH", None)
    env.pop("WORKTREE_CLEANUP_AGE_HOURS", None)

    def git(repo, *args):
        return subprocess.check_output(
            ["git", "-c", "user.name=Cleanup check",
             "-c", "user.email=cleanup@example.invalid",
             "-c", "commit.gpgsign=false", *args],
            cwd=repo, env=env, text=True,
        ).strip()

    def project(repo, branch):
        repo.mkdir(parents=True)
        git(repo, "init", "-q", "--initial-branch", branch)
        (repo / ".gitignore").write_text(".worktrees/\nnode_modules/\nevidence/\n")
        git(repo, "add", ".gitignore")
        git(repo, "commit", "-qm", "Initialize cleanup fixture")
        git(repo, "update-ref", f"refs/remotes/origin/{branch}", "HEAD")
        git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", f"refs/remotes/origin/{branch}")

    def run(cwd, *args, run_env=env):
        result = subprocess.run(
            ["/bin/bash", str(tool), *args], cwd=cwd, env=run_env,
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    with tempfile.TemporaryDirectory(prefix="worktree-cleanup-check-") as folder:
        temporary = Path(folder).resolve()
        root = temporary / "src"
        app = root / "group/team app"
        # Discover this repository through a disposable linked checkout, not
        # through its primary checkout. Later removals must use the primary.
        library = temporary / "z-library-primary"
        project(app, "main")
        project(library, "trunk")
        disposable = app / ".worktrees/merged"
        git(app, "worktree", "add", "-b", "completed-task", str(disposable))
        dirty = app / ".worktrees/unfinished"
        git(app, "worktree", "add", "--detach", str(dirty))
        (dirty / ".gitignore").write_text("unfinished edit\n")
        evidence = app / ".worktrees/evidence"
        git(app, "worktree", "add", "--detach", str(evidence))
        (evidence / "evidence").mkdir()
        (evidence / "evidence/report.txt").write_text("retain ignored evidence")
        locked = app / ".worktrees/pinned"
        git(app, "worktree", "add", "--detach", str(locked))
        git(app, "worktree", "lock", "--reason", "Keep this checkout", str(locked))
        dependencies = root / "library linked checkout"
        git(library, "worktree", "add", "--detach", str(dependencies))
        (dependencies / "node_modules").mkdir()
        (dependencies / "node_modules/disposable-cache").write_bytes(b"x" * 65536)
        completed = library / ".worktrees/completed"
        git(library, "worktree", "add", "--detach", str(completed))
        active = library / ".worktrees/background"
        git(library, "worktree", "add", "--detach", str(active))
        trigger = temporary / "start-background"
        ready = temporary / "background-ready"
        wrappers = temporary / "wrappers"
        wrappers.mkdir()
        git_wrapper = wrappers / "git"
        git_wrapper.write_text("#!" + sys.executable + "\n" + """
import os
from pathlib import Path
import sys
import time

args = sys.argv[1:]
trigger = Path(os.environ["WORKTREE_TEST_TRIGGER"])
if len(args) >= 3 and args[-3:-1] == ["worktree", "remove"] and not trigger.exists():
    trigger.touch()
    deadline = time.monotonic() + 5
    while not Path(os.environ["WORKTREE_TEST_READY"]).exists():
        if time.monotonic() > deadline:
            raise RuntimeError("Background fixture did not start")
        time.sleep(0.01)
os.execv(os.environ["WORKTREE_TEST_GIT"], ["git", *args])
""")
        git_wrapper.chmod(0o755)
        tool_env = {
            **env,
            "PATH": str(wrappers) + os.pathsep + env["PATH"],
            "WORKTREE_TEST_GIT": shutil.which("git"),
            "WORKTREE_TEST_TRIGGER": str(trigger),
            "WORKTREE_TEST_READY": str(ready),
            "WORKTREE_TEST_ACTIVE": str(active),
        }
        process = subprocess.Popen(
            [sys.executable, "-c", """
import os
from pathlib import Path
import time
while not Path(os.environ["WORKTREE_TEST_TRIGGER"]).exists():
    time.sleep(0.01)
os.chdir(os.environ["WORKTREE_TEST_ACTIVE"])
Path(os.environ["WORKTREE_TEST_READY"]).touch()
time.sleep(120)
"""], cwd=temporary, env=tool_env,
        )
        try:
            preview = run(root)
            assert "Repositories checked: 2" in preview, preview
            assert "4 worktree(s) would be removed" in preview, preview
            assert "Estimated reclaimable space" in preview, preview
            assert disposable.is_dir() and dependencies.is_dir() and completed.is_dir()
            assert "ignored files" in preview, preview
            # Start a process during the first removal, after planning and any
            # initial activity snapshot. The later candidate must stay alive.
            result = run(temporary, "-y", str(root), run_env=tool_env)
            assert "Removed 3 worktree(s)" in result, result
            assert "active process" in result, result
            assert not disposable.exists() and not dependencies.exists() and not completed.exists(), result
            assert dirty.is_dir() and active.is_dir() and locked.is_dir()
            assert (dirty / ".gitignore").read_text() == "unfinished edit\n"
            assert (evidence / "evidence/report.txt").read_text() == "retain ignored evidence"
            assert git(app, "show-ref", "--verify", "refs/heads/completed-task")
            assert git(app, "status", "--porcelain") == ""
            assert git(library, "status", "--porcelain") == ""
        finally:
            process.terminate()
            process.wait(timeout=5)
    print("PASS: repository sweep previews and removes eligible checkouts; "
          "deduplicates repositories and preserves active, dirty, locked, and ignored work.")


if __name__ == "__main__":
    main()
