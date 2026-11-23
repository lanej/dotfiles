#!/usr/bin/env python3
"""Verify the selected executables for the next Git/manager invocation."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def identity(paths):
    if not all(path.is_file() for path in paths):
        return None
    digests = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    return hashlib.sha256(json.dumps(digests).encode()).hexdigest()


def main():
    action, git_version, manager_version = sys.argv[1:]
    installed = [Path.home() / ".local/bin" / name for name in ("git", "worktree")]
    selected = [shutil.which(name) for name in ("git", "worktree")]
    expected = identity(installed)
    correct = expected is not None
    for path, version in zip(installed, (f"git version {git_version}", f"worktree {manager_version}")):
        if path.is_file():
            result = subprocess.run([str(path), "--version"], capture_output=True, text=True)
            correct = correct and result.returncode == 0 and result.stdout.strip() == version
    running = identity([Path(path) for path in selected]) if all(selected) else None
    target = {"target": "local", "expected_identity": expected if correct else None,
              "running_identity": running, "ready": correct and running == expected,
              "process": None, "sessions": []}
    if not correct:
        target["reason"] = "selected-git-and-manager-not-installed"
    elif running != expected:
        target["reason"] = "subsequent-invocation-selects-another-executable"
    if action == "checkpoint":
        target["checkpoint"] = {"state": "confirmed", "run_id": os.environ.get("PROJECT_UPDATE_RUN_ID"),
                                "reason": "no-persistent-process"}
    print(json.dumps({"schema_version": 1, "targets": [target]}))
    return 0 if target["ready"] or action == "inventory" else 3


if __name__ == "__main__":
    sys.exit(main())
