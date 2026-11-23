"""Private, durable results for detached workstation updates."""

import fcntl
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import uuid


def private_directory(path):
    path = Path(path)
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError(f"Operation directory must be private and owned: {path}")
    return path


def state_root():
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return private_directory(root / "dotfiles/project-update")


def operation_path(run_id):
    try:
        if str(uuid.UUID(run_id)) != run_id:
            raise ValueError()
    except (ValueError, AttributeError) as error:
        raise ValueError("RUN_ID must be a complete operation UUID") from error
    path = state_root() / run_id
    if not path.exists():
        raise ValueError(f"Unknown update operation: {run_id}")
    return private_directory(path)


def read_json(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError(f"Operation file must be private and owned: {path}")
        return json.load(stream)


def write_json(path, value):
    private_directory(path.parent)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=".result-", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def acquire(path, private=True):
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or (private and info.st_mode & 0o077)):
            raise ValueError(f"Operation lock must be private and owned: {path}")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return os.fdopen(fd, "w")


def wait_result(directory):
    """Wait without repeating a mutation when a coordinator has disappeared."""
    while True:
        try:
            with acquire(directory / "coordinator.lock"):
                if (directory / "result.json").exists():
                    return read_json(directory / "result.json")
                state = read_json(directory / "progress.json")
                rows = state["results"]
                for row in rows:
                    if row["outcome"] == "ok":
                        row.update(outcome="incomplete", reason="coordinator-exited-before-verification")
                    row["recovery_path"] = str(directory)
                return {"exit_code": 3, "results": rows}
        except BlockingIOError:
            time.sleep(0.1)
