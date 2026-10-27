#!/usr/bin/env python3
"""Sweep real repositories, removing idle merged worktrees and retaining work."""
import os
from pathlib import Path
import pty
import re
import select
import shutil
import sqlite3
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
            # Real lsof scans scale with the host's other running processes.
            capture_output=True, text=True, timeout=180,
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
        pooled = app / ".worktrees/.treehouse/app-fixture/1/app-1"
        git(app, "worktree", "add", "--detach", str(pooled))
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
        git(app, "commit", "--allow-empty", "-qm", "Advance the merged base without file changes")
        git(app, "update-ref", "refs/remotes/origin/main", "HEAD")
        operation = app / ".worktrees/unfinished-merge"
        git(app, "worktree", "add", "-b", "merge-in-progress", str(operation), "HEAD~1")
        git(operation, "merge", "--no-ff", "--no-commit", "main")
        assert git(operation, "status", "--porcelain") == ""
        dependencies = root / "library linked checkout"
        git(library, "worktree", "add", "--detach", str(dependencies))
        (dependencies / "node_modules").mkdir()
        (dependencies / "node_modules/disposable-cache").write_bytes(b"x" * 65536)
        completed = library / ".worktrees/completed"
        git(library, "worktree", "add", "--detach", str(completed))
        active = library / ".worktrees/background"
        git(library, "worktree", "add", "--detach", str(active))
        # One conflicting merge includes enough files to exercise ranking and
        # truncation, plus a tabbed filename and a binary file in its full list.
        conflict_names = ["largest file.txt", "a\tfile.txt", "small-1.txt", "small-2.txt"]
        for name in conflict_names:
            (app / name).write_text("original\n")
        (app / "binary.dat").write_bytes(b"\0original")
        (app / "mode.txt").write_text("original\n")
        git(app, "add", ".")
        git(app, "commit", "-qm", "Initialize conflicting files")
        conflicted = app / ".worktrees/conflicted"
        git(app, "worktree", "add", "-b", "conflict-report", str(conflicted))
        for name in conflict_names:
            (conflicted / name).write_text("head\n")
            (app / name).write_text("base\n")
        (conflicted / "largest file.txt").write_text("head\n" * 7)
        (app / "largest file.txt").write_text("base\n" * 2)
        (conflicted / "binary.dat").write_bytes(b"\0head")
        (app / "binary.dat").write_bytes(b"\0base")
        (conflicted / "mode.txt").chmod(0o755)
        git(app, "rm", "-q", "mode.txt")
        git(conflicted, "commit", "-qam", "Conflicting HEAD edits")
        git(app, "commit", "-qam", "Conflicting base edits")
        git(app, "update-ref", "refs/remotes/origin/main", "HEAD")
        conflict_head = git(conflicted, "rev-parse", "HEAD")
        conflict_index = Path(git(conflicted, "rev-parse", "--path-format=absolute",
                                  "--git-path", "index")).read_bytes()
        codex_directory = temporary / "codex"
        codex_directory.mkdir()
        env["CODEX_HOME"] = str(codex_directory)
        codex_path_alias = temporary / "codex-worktree-alias"
        codex_path_alias.symlink_to(app, target_is_directory=True)
        database = codex_directory / "state_5.sqlite"
        with sqlite3.connect(database) as metadata:
            metadata.execute("CREATE TABLE threads "
                             "(id TEXT, cwd TEXT, name TEXT, title TEXT, source TEXT, "
                             "updated_at INTEGER, archived INTEGER)")
            metadata.executemany("INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?, ?)", [
                ("latest", str(codex_path_alias / ".worktrees/conflicted"),
                 "Resolve\tcleanup conflicts", "Original long prompt", "cli", 100, 0),
                ("older", str(conflicted / "src"), "Earlier conversation", "Old prompt", "vscode", 90, 1),
                ("helper", str(conflicted), "Review helper", "Helper prompt",
                 '{"subagent":"review"}', 200, 0),
                ("unrelated", str(conflicted) + "-other", "Wrong conversation", "Other prompt", "cli", 300, 0),
            ])
        database_before = database.read_bytes()
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
import signal
import time
while not Path(os.environ["WORKTREE_TEST_TRIGGER"]).exists():
    time.sleep(0.01)
os.chdir(os.environ["WORKTREE_TEST_ACTIVE"])
Path(os.environ["WORKTREE_TEST_READY"]).touch()
signal.pause()
"""], cwd=temporary, env=tool_env,
        )
        try:
            # Terminals exercise both table coloring and progress output.
            terminal, terminal_output = pty.openpty()
            table_terminal, table_output = pty.openpty()
            progress_chunks = []
            preview_chunks = []
            finished = threading.Event()

            def read_terminal(fd, chunks):
                while not finished.is_set() or select.select([fd], [], [], 0)[0]:
                    if select.select([fd], [], [], 0.1)[0]:
                        chunks.append(os.read(fd, 65536))

            reader = threading.Thread(target=read_terminal, args=(terminal, progress_chunks))
            table_reader = threading.Thread(target=read_terminal, args=(table_terminal, preview_chunks))
            reader.start()
            table_reader.start()
            preview_env = {**env, "TERM": "xterm"}
            preview_env.pop("NO_COLOR", None)
            try:
                preview_run = subprocess.run(
                    ["/bin/bash", str(tool)], cwd=root,
                    env=preview_env, stdout=table_output,
                    stderr=terminal_output, text=True, timeout=60,
                )
            finally:
                # Drain before closing the slave: macOS discards unread terminal
                # output when the final slave descriptor closes.
                finished.set()
                reader.join(timeout=5)
                table_reader.join(timeout=5)
                os.close(terminal_output)
                os.close(terminal)
                os.close(table_output)
                os.close(table_terminal)
            assert not reader.is_alive() and not table_reader.is_alive(), "Terminal reader did not stop"
            progress = b"".join(progress_chunks).decode()
            colored_preview = b"".join(preview_chunks).decode()
            assert "\x1b[32m       7\x1b[0m" in colored_preview, colored_preview
            assert "\x1b[31m       1\x1b[0m" in colored_preview, colored_preview
            assert "\x1b[31mMerge conflicts:\x1b[0m" in colored_preview, colored_preview
            zero_line = next(line for line in colored_preview.splitlines() if line.endswith("mode.txt"))
            assert not re.search(r"\x1b\[[0-9;]*m *0", zero_line), zero_line
            preview = re.sub(r"\x1b\[[0-9;]*m", "", colored_preview).replace("\r\n", "\n")
            assert preview_run.returncode == 0, preview + progress
            assert "Discovering repositories" in progress, progress
            assert "Scanning repositories 2/2" in progress, progress
            assert "Repositories checked: 2" in preview, preview
            assert preview.count("DISK USAGE") == 1, preview
            assert "REPOSITORY" in preview and "BASE" in preview, preview
            assert "CODEX SESSION" in preview, preview
            conflict_row = next(line for line in preview.splitlines() if line.endswith(str(conflicted)))
            assert "Resolve cleanup conflicts (+1 more)" in conflict_row, conflict_row
            assert "Review helper" not in preview and "Wrong conversation" not in preview, preview
            assert database.read_bytes() == database_before, "Codex metadata was modified"
            assert str(nested) not in preview, preview
            assert "4 worktree(s) would be removed" in preview, preview
            assert "Estimated reclaimable space" in preview, preview
            assert disposable.is_dir() and dependencies.is_dir() and completed.is_dir()
            assert "reserved Treehouse pool" in preview, preview
            assert "ignored files" in preview, preview
            assert "hidden index flags" in preview, preview
            assert "Git operation in progress" in preview, preview
            details = preview.split(f"Merge conflicts: {conflicted}\n", 1)[1]
            assert "HEAD vs origin/main" in details, details
            assert "Showing 5 of 6 conflicting files; 1 more omitted" in details, details
            assert "HEAD +" in details and "HEAD -" in details and "BASE +" in details and "BASE -" in details
            file_lines = details.split("FILE\n", 1)[1].split("  Showing", 1)[0].splitlines()
            assert file_lines[0].endswith("largest file.txt"), details
            assert file_lines[0].split()[:4] == ["7", "1", "2", "1"], details
            assert next(line for line in file_lines if line.endswith("mode.txt")).split()[:4] == ["0", "0", "0", "1"], details
            assert "a\\tfile.txt" in details and "binary.dat" not in details, details
            assert git(conflicted, "status", "--porcelain") == ""
            assert git(conflicted, "rev-parse", "HEAD") == conflict_head
            assert Path(git(conflicted, "rev-parse", "--path-format=absolute",
                            "--git-path", "index")).read_bytes() == conflict_index
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
            assert "\x1b[" not in result, result
            assert "Removed 3 worktree(s)" in result, result
            assert "active process" in result, result
            assert not disposable.exists() and not dependencies.exists() and not completed.exists(), result
            assert dirty.is_dir() and active.is_dir() and locked.is_dir()
            assert pooled.is_dir() and str(pooled) in git(app, "worktree", "list", "--porcelain")
            assert nested_checkout.is_dir()
            assert operation.is_dir()
            assert conflicted.is_dir() and "merge conflicts" in result
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
