#!/usr/bin/env python3
"""Sweep real repositories, removing idle merged worktrees and retaining work."""
import os
from pathlib import Path
import pty
import select
import shutil
import subprocess
import sys
import tempfile
import threading


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
        (repo / ".gitignore").write_text(".worktrees/\nnode_modules/\nevidence/\nvendor/\n")
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
        env["XDG_CACHE_HOME"] = str(temporary / "cache")
        root = temporary / "src"
        app = root / "group/team app"
        # Discover this repository through a disposable linked checkout, not
        # through its primary checkout. Later removals must use the primary.
        library = temporary / "z-library-primary"
        project(app, "main")
        project(library, "trunk")
        nested = app / "vendor/nested-project"
        project(nested, "main")
        nested_checkout = nested / ".worktrees/retained"
        git(nested, "worktree", "add", "--detach", str(nested_checkout))
        disposable = app / ".worktrees/merged"
        git(app, "worktree", "add", "-b", "completed-task", str(disposable))
        (disposable / "node_modules").mkdir()
        (disposable / "node_modules/disposable-cache").write_bytes(b"x" * 2 * 1024 * 1024)
        dirty = app / ".worktrees/unfinished"
        git(app, "worktree", "add", "--detach", str(dirty))
        (dirty / ".gitignore").write_text("unfinished edit\n")
        missing = app / ".worktrees/abandoned"
        git(app, "worktree", "add", "--detach", str(missing))
        shutil.rmtree(missing)
        hidden = app / ".worktrees/hidden-index"
        git(app, "worktree", "add", "--detach", str(hidden))
        git(hidden, "update-index", "--assume-unchanged", ".gitignore")
        (hidden / ".gitignore").write_text("edit hidden from git status\n")
        assert git(hidden, "status", "--porcelain") == ""
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
            # A terminal on stderr keeps progress visible when stdout is logged.
            terminal, terminal_output = pty.openpty()
            progress_chunks = []
            finished = threading.Event()

            def read_progress():
                while not finished.is_set() or select.select([terminal], [], [], 0)[0]:
                    if select.select([terminal], [], [], 0.1)[0]:
                        progress_chunks.append(os.read(terminal, 65536))

            reader = threading.Thread(target=read_progress)
            reader.start()
            try:
                preview_run = subprocess.run(
                    ["/bin/bash", str(tool)], cwd=root,
                    env={**env, "TERM": "xterm"}, stdout=subprocess.PIPE,
                    stderr=terminal_output, text=True, timeout=60,
                )
            finally:
                # Drain before closing the slave: macOS discards unread terminal
                # output when the final slave descriptor closes.
                finished.set()
                reader.join(timeout=5)
                os.close(terminal_output)
                os.close(terminal)
            assert not reader.is_alive(), "Terminal progress reader did not stop"
            progress = b"".join(progress_chunks).decode()
            preview = preview_run.stdout
            assert preview_run.returncode == 0, preview + progress
            assert "Discovering repositories" in progress, progress
            assert "Scanning repositories 2/2" in progress, progress
            assert "Repositories checked: 2" in preview, preview
            assert preview.count("DISK USAGE") == 1, preview
            assert "REPOSITORY" in preview and "BASE" in preview, preview
            assert str(nested) not in preview, preview
            assert "4 worktree(s) would be removed" in preview, preview
            assert "Estimated reclaimable space" in preview, preview
            assert disposable.is_dir() and dependencies.is_dir() and completed.is_dir()
            assert "ignored files" in preview, preview
            assert "hidden index flags" in preview, preview
            header = next(line for line in preview.splitlines() if line.startswith("REPOSITORY"))
            size_at, age_at = header.index("DISK USAGE"), header.index("SIZE AGE")
            table = preview.split(header + "\n", 1)[1].split("\n\n", 1)[0].splitlines()
            sizes = [line[size_at:age_at].strip() for line in table]
            assert sizes[-1] == "-" and all(size != "-" for size in sizes[:-1]), preview
            units = {"KiB": 1, "MiB": 1024, "GiB": 1024**2, "TiB": 1024**3, "PiB": 1024**4}
            numeric = [float(size.split()[0]) * units[size.split()[1]] for size in sizes[:-1]]
            assert numeric == sorted(numeric), preview
            assert any("MiB" in size for size in sizes) and any("KiB" in size for size in sizes), preview
            # Start a process during the first removal, after planning and any
            # initial activity snapshot. The later candidate must stay alive.
            result = run(temporary, "-y", str(root), run_env=tool_env)
            assert "Removed 3 worktree(s)" in result, result
            assert "active process" in result, result
            assert not disposable.exists() and not dependencies.exists() and not completed.exists(), result
            assert dirty.is_dir() and active.is_dir() and locked.is_dir()
            assert nested_checkout.is_dir()
            assert (dirty / ".gitignore").read_text() == "unfinished edit\n"
            assert (hidden / ".gitignore").read_text() == "edit hidden from git status\n"
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
