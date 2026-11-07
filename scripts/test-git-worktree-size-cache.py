#!/usr/bin/env python3
"""Exercise cold, warm, refreshed, expired, and replaced worktree size estimates."""
import json
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
    with tempfile.TemporaryDirectory(prefix="worktree-size-cache-check-") as folder:
        root = Path(folder).resolve()
        repo = root / "project"
        repo.mkdir()
        wrappers = root / "wrappers"
        wrappers.mkdir()
        clock = root / "clock"
        calls = root / "du-calls"
        shrink = root / "shrink-after-planning"
        unavailable = root / "size-unavailable"
        now = 946684800 + 51 * 3600  # HEAD is two days and three hours old.
        clock.write_text(str(now))
        env = {
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
            "NO_COLOR": "1", "XDG_CACHE_HOME": str(root / "cache"),
            "CODEX_HOME": str(root / "codex"),
            "PATH": str(wrappers) + os.pathsep + os.environ["PATH"],
            "WORKTREE_TEST_DU": shutil.which("du"),
            "WORKTREE_TEST_DATE": shutil.which("date"),
            "WORKTREE_TEST_CALLS": str(calls),
            "WORKTREE_TEST_CLOCK": str(clock),
            "WORKTREE_TEST_SHRINK": str(shrink),
            "WORKTREE_TEST_DU_FAILURE": str(unavailable),
        }
        env.pop("WORKTREE_CLEANUP_BASE_BRANCH", None)
        env.pop("WORKTREE_CLEANUP_AGE_HOURS", None)
        du = wrappers / "du"
        du.write_text("#!" + sys.executable + "\n" + """
import os, subprocess, sys
from pathlib import Path
with open(os.environ["WORKTREE_TEST_CALLS"], "a") as log:
    log.write(sys.argv[-1] + "\\n")
failure = Path(os.environ["WORKTREE_TEST_DU_FAILURE"])
if failure.exists() and failure.read_text() == sys.argv[-1]:
    sys.exit(1)
shrink = Path(os.environ["WORKTREE_TEST_SHRINK"])
if shrink.exists() and sys.argv[-1] == os.environ.get("WORKTREE_TEST_SIZE_CHECKOUT"):
    result = subprocess.run([os.environ["WORKTREE_TEST_DU"], *sys.argv[1:]])
    if result.returncode == 0:
        Path(os.environ["WORKTREE_TEST_SIZE_PAYLOAD"]).write_bytes(b"x" * 65536)
        shrink.unlink()
    sys.exit(result.returncode)
os.execv(os.environ["WORKTREE_TEST_DU"], ["du", *sys.argv[1:]])
""")
        du.chmod(0o755)
        date = wrappers / "date"
        date.write_text("#!" + sys.executable + "\n" + """
import os, sys
from pathlib import Path
if sys.argv[1:] == ["+%s"]:
    print(Path(os.environ["WORKTREE_TEST_CLOCK"]).read_text())
else:
    os.execv(os.environ["WORKTREE_TEST_DATE"], ["date", *sys.argv[1:]])
""")
        date.chmod(0o755)

        def git(*args):
            return subprocess.check_output(
                ["git", "-c", "user.name=Cache check",
                 "-c", "user.email=cache@example.invalid",
                 "-c", "commit.gpgsign=false", *args],
                cwd=repo, env=env, text=True,
            ).strip()

        def run_cleanup(*args, expected_status=0):
            result = subprocess.run(
                ["/bin/bash", str(tool), *args], cwd=repo, env=env,
                text=True, capture_output=True, timeout=60,
            )
            assert result.returncode == expected_status, result.stdout + result.stderr
            return result.stdout

        def scan(*args, expected_status=0):
            output = run_cleanup(*args, expected_status=expected_status)
            header = next(line for line in output.splitlines()
                          if line.startswith("REPOSITORY"))
            line = next(line for line in output.splitlines()
                        if line.endswith(str(checkout)))
            head_age_at = header.index("AGE")
            size_at, age_at, codex_at = (header.index(name)
                                        for name in ("DISK USAGE", "SIZE AGE", "CODEX SESSION"))
            assert line[head_age_at:size_at].strip() == "2d 3h", line
            return line, line[size_at:age_at].strip(), line[age_at:codex_at].strip()

        git("init", "-q", "--initial-branch", "main")
        (repo / ".gitignore").write_text(".worktrees/\nnode_modules/\n")
        git("add", ".gitignore")
        git("commit", "-qm", "Initialize cache fixture")
        checkout = repo / ".worktrees/task"
        git("worktree", "add", "--detach", str(checkout))
        (checkout / "node_modules").mkdir()
        payload = checkout / "node_modules/payload"
        payload.write_bytes(b"x" * 65536)
        cold, original_size, age = scan()
        assert "remove" in cold and age == "fresh", cold
        assert len(calls.read_text().splitlines()) == 1

        # Sizes may lag during their TTL, but eligibility must reflect new work.
        (checkout / "unfinished.txt").write_text("preserve this edit")
        payload.write_bytes(b"x" * 4 * 1024 * 1024)
        clock.write_text(str(now + 30))
        warm, size, age = scan()
        assert "dirty" in warm and size == original_size and age == "cached 30s", warm
        assert len(calls.read_text().splitlines()) == 1

        refreshed, grown_size, age = scan("--refresh")
        assert grown_size != original_size and age == "fresh", refreshed
        assert len(calls.read_text().splitlines()) == 2

        clock.write_text(str(now + 930))
        expired, size, age = scan()
        assert size == grown_size and age == "fresh", expired
        assert len(calls.read_text().splitlines()) == 3

        # Keeping the old directory alive guarantees a different inode at the
        # reused path; path-only caches would report its old dependency size.
        previous = repo / ".worktrees/previous"
        git("worktree", "move", str(checkout), str(previous))
        git("worktree", "add", "--detach", str(checkout))
        replaced, size, age = scan()
        assert size != grown_size and age == "fresh", replaced
        assert len(calls.read_text().splitlines()) == 5
        assert (previous / "unfinished.txt").read_text() == "preserve this edit"

        # A stale registration pointing through an alias must measure the real
        # directory, not poison its shared cache with the symlink's zero size.
        replacement_size = size
        real = repo / ".worktrees/real"
        checkout.rename(real)
        checkout.symlink_to(real, target_is_directory=True)
        alias, size, age = scan(expected_status=1)
        assert "checkout check failed" in alias and size == replacement_size, alias
        assert age == "fresh"
        git("worktree", "repair", str(real))
        checkout = real
        repaired, size, age = scan()
        assert size == replacement_size and age == "cached 0s", repaired
        assert len(calls.read_text().splitlines()) == 6

        small = repo / ".worktrees/small"
        git("worktree", "add", "--detach", str(small))
        (checkout / "node_modules").mkdir()
        payload = checkout / "node_modules/payload"
        payload.write_bytes(b"x" * 4 * 1024 * 1024)
        registration = git("worktree", "list", "--porcelain")
        preview = json.loads(run_cleanup("--min-size", "0.503808MB", "--json"))
        rows = {row["path"]: row for row in preview["worktrees"]}
        assert preview["min_size_kib"] == 492, preview
        assert rows[str(checkout)]["action"] == "remove", preview
        assert rows[str(checkout)]["size_kib"] >= 1024, preview
        assert rows[str(checkout)]["size_age"] == "fresh", preview
        assert rows[str(small)]["action"] == "skip", preview
        assert rows[str(small)]["reason"] == "below min size (492.0 KiB)", preview
        assert rows[str(previous)]["reason"] == "dirty", preview
        assert git("worktree", "list", "--porcelain") == registration
        assert payload.stat().st_size == 4 * 1024 * 1024

        env["WORKTREE_TEST_SIZE_CHECKOUT"] = str(checkout)
        env["WORKTREE_TEST_SIZE_PAYLOAD"] = str(payload)
        shrink.touch()
        threshold = f'{rows[str(checkout)]["size_kib"]}KiB'
        rechecked = run_cleanup("--min-size", threshold, "-y")
        planned_row = next(line for line in rechecked.splitlines() if line.endswith(str(checkout)))
        assert "remove" in planned_row, rechecked
        assert not shrink.exists() and payload.stat().st_size == 65536
        assert f"Retaining {checkout}: below min size" in rechecked, rechecked
        assert "Removed 0 worktree(s)" in rechecked, rechecked
        assert checkout.is_dir() and small.is_dir() and previous.is_dir()

        unavailable.write_text(str(small))
        failed = json.loads(run_cleanup("--min-size", "1MiB", "--json", expected_status=1))
        failed_rows = {row["path"]: row for row in failed["worktrees"]}
        assert failed["errors"] == 1, failed
        assert failed_rows[str(small)]["action"] == "skip", failed
        assert failed_rows[str(small)]["reason"] == "size unavailable", failed
        assert failed_rows[str(small)]["size_kib"] is None, failed
        assert small.is_dir() and checkout.is_dir()
        unavailable.unlink()

        payload.write_bytes(b"x" * 1536 * 1024)
        removed = run_cleanup("--min-size", "1.5MiB", "-y")
        assert "Removed 1 worktree(s)" in removed, removed
        assert not checkout.exists() and str(checkout) not in git("worktree", "list", "--porcelain")
        assert small.is_dir() and str(small) in git("worktree", "list", "--porcelain")
        assert previous.is_dir() and (previous / "unfinished.txt").read_text() == "preserve this edit"

    print("PASS: size cache avoids repeated du, keeps eligibility fresh, "
          "and remeasures on refresh, expiry, or directory replacement; size-filtered "
          "cleanup uses fresh sizes, retains shrinking or unknown checkouts, and removes only large ones.")


if __name__ == "__main__":
    main()
