#!/usr/bin/env python3
"""Purge idle scratch files while retaining active work and recent contents."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time


def main():
    tool = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (
        Path(__file__).resolve().parents[1] / "bin/tmp-cleanup"
    )
    with tempfile.TemporaryDirectory(prefix="tmp-cleanup-check-", dir="/tmp") as folder:
        root = Path(folder).resolve()
        scratch = root / "completed task"
        scratch.mkdir()
        (scratch / "output.txt").write_text("disposable")
        external = root / "external"
        external.mkdir()
        (external / "keep.txt").write_text("retained link target")
        (scratch / "link").symlink_to(external, target_is_directory=True)
        recent = root / "recent"
        recent.mkdir()
        child = recent / "new-output.txt"
        child.write_text("recent result")
        future = time.time() + 3600
        os.utime(child, (future, future))
        active = root / "active"
        active.mkdir()
        handle = (active / "running.txt").open("w")
        handle.write("in use")
        handle.flush()
        checkout = root / "checkout"
        subprocess.run(["git", "init", "-q", str(checkout)], check=True)
        pipe = root / "service-pipe"
        os.mkfifo(pipe)
        service = root / "com.apple.tmp-cleanup-fixture"
        service.mkdir()
        service_file = service / "service-state.txt"
        service_file.write_text("retain macOS service state")
        os.utime(service_file, (future, future))
        readonly = root / "read-only cache"
        readonly.mkdir()
        (readonly / "module").write_text("retain an unremovable cache")
        readonly.chmod(0o555)

        def run(*args):
            result = subprocess.run(
                [sys.executable, str(tool), "--age-hours", "0", "--json",
                 str(root), *args], capture_output=True, text=True, timeout=60,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            return json.loads(result.stdout)

        try:
            # NOTE: Zero grace time avoids falsifying filesystem change times in this fixture.
            time.sleep(2)
            preview = run()
            rows = {Path(row["path"]).name: row for row in preview["entries"]}
            assert preview["mode"] == "preview"
            assert rows[scratch.name]["action"] == "remove", rows[scratch.name]
            assert scratch.exists(), "preview removed scratch files"
            assert rows[recent.name]["action"] == "retain", rows[recent.name]
            assert rows[active.name]["action"] == "retain", rows[active.name]
            assert rows[checkout.name]["action"] == "retain", rows[checkout.name]
            assert rows[pipe.name]["action"] == "retain", rows[pipe.name]
            assert rows[readonly.name]["action"] == "retain", rows[readonly.name]
            source = checkout / "src"
            source.mkdir()
            valuable = source / "work.txt"
            valuable.write_text("retained source")
            rejected = subprocess.run(
                [sys.executable, str(tool), "--age-hours", "0", "-y", str(source)],
                capture_output=True, text=True, timeout=60,
            )
            assert rejected.returncode != 0 and valuable.exists(), rejected.stdout + rejected.stderr
            if sys.platform == "darwin":
                rejected_service = subprocess.run(
                    [sys.executable, str(tool), "--age-hours", "0", "-y", str(service)],
                    capture_output=True, text=True, timeout=60,
                )
                assert rejected_service.returncode != 0 and service_file.exists(), (
                    rejected_service.stdout + rejected_service.stderr
                )

            # The link target is deliberately made recent before the purge.
            os.utime(external / "keep.txt", (future, future))
            wrapper = root / "wrapper"
            wrapper.mkdir()
            shutil.copy2(tool.parent / "system-cleanup", wrapper / "system-cleanup")
            for name in ("worktree-cleanup", "disk-cleanup", "cargo-sweep-cleanup",
                         "rust-dev-cleanup", "opencode-cleanup-cache",
                         "opencode-cleanup-snapshots", "npm-cleanup"):
                stub = wrapper / name
                stub.write_text("#!/bin/sh\nexit 0\n")
                stub.chmod(0o755)
            entrypoint = wrapper / "tmp-cleanup"
            entrypoint.write_text("#!/bin/sh\nexec " + shlex.join([
                sys.executable, str(tool), "--age-hours", "0", "--json", str(root),
            ]) + ' "$@"\n')
            entrypoint.chmod(0o755)
            result = subprocess.run(
                [str(wrapper / "system-cleanup")],
                env={**os.environ, "PATH": str(wrapper) + ":/usr/bin:/bin:/usr/sbin:/sbin"},
                capture_output=True, text=True, timeout=60,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            applied = json.loads(next(line for line in result.stdout.splitlines()
                                      if line.startswith("{")))
            assert applied["mode"] == "apply"
            assert not scratch.exists(), "purge did not remove idle scratch files"
            assert any(row["path"] == str(scratch) and row["action"] == "removed"
                       for row in applied["entries"]), applied
            assert (external / "keep.txt").read_text() == "retained link target"
            assert child.exists() and (active / "running.txt").exists()
            assert (checkout / ".git").exists() and pipe.exists()
            assert (readonly / "module").exists()

            idle = root / "inspection-failure.txt"
            idle.write_text("retain when process inspection fails")
            tools = root / "tools"
            tools.mkdir()
            probe = tools / "lsof"
            probe.write_text("#!/bin/sh\nexit 2\n")
            probe.chmod(0o755)
            failed = subprocess.run(
                [sys.executable, str(tool), "--age-hours", "0", "-y", str(root)],
                env={**os.environ, "PATH": str(tools) + os.pathsep + os.environ["PATH"]},
                capture_output=True, text=True, timeout=60,
            )
            assert failed.returncode != 0 and idle.exists(), failed.stdout + failed.stderr
        finally:
            handle.close()
            readonly.chmod(0o755)
    print("Temporary cleanup workflow passed")


if __name__ == "__main__":
    main()
