#!/usr/bin/env python3
"""Exercise cold, warm, refreshed, expired, and replaced worktree size estimates."""
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
        }
        env.pop("WORKTREE_CLEANUP_BASE_BRANCH", None)
        env.pop("WORKTREE_CLEANUP_AGE_HOURS", None)
        du = wrappers / "du"
        du.write_text("#!" + sys.executable + "\n" + """
import os, sys
with open(os.environ["WORKTREE_TEST_CALLS"], "a") as log:
    log.write(sys.argv[-1] + "\\n")
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

        def scan(*args, expected_status=0):
            result = subprocess.run(
                ["/bin/bash", str(tool), *args], cwd=repo, env=env,
                text=True, capture_output=True, timeout=60,
            )
            assert result.returncode == expected_status, result.stdout + result.stderr
            header = next(line for line in result.stdout.splitlines()
                          if line.startswith("REPOSITORY"))
            line = next(line for line in result.stdout.splitlines()
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

    print("PASS: size cache avoids repeated du, keeps eligibility fresh, "
          "and remeasures on refresh, expiry, or directory replacement.")


if __name__ == "__main__":
    main()
