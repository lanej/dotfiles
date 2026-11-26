"""Name a frozen Socrates session and keep its original path as an alias."""

import argparse
import ctypes
import errno
import fcntl
from itertools import chain, count
import os
from pathlib import Path
import re
import sys
import unicodedata


DRAFT_NAME = re.compile(r"(?P<date>[0-9]{8})-[0-9]{6}")
LABEL = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")


def short_label(label: str) -> str:
    text = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "plan"
    if not slug[0].isalpha():
        slug = f"plan-{slug}"
    return slug[:32].rstrip("-")


def exchange(directory: int, first: str, second: str) -> None:
    symbol = {"darwin": "renameatx_np", "linux": "renameat2"}.get(sys.platform)
    rename = getattr(ctypes.CDLL(None, use_errno=True), symbol, None) if symbol else None
    if rename is None:
        raise OSError(errno.ENOTSUP, "atomic session naming is unavailable on this host")
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    exchange_flag = 2  # RENAME_SWAP on macOS and RENAME_EXCHANGE on Linux.
    if rename(directory, os.fsencode(first), directory, os.fsencode(second), exchange_flag):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), first)


def name_session(session: Path, label: str) -> Path:
    session = Path(os.path.abspath(session))
    root = session.parent
    if root.name != ".socrates":
        raise ValueError("select a session directory directly inside .socrates")

    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(directory, fcntl.LOCK_EX)
        draft = DRAFT_NAME.fullmatch(session.name)
        reservation = session / ".naming"
        if session.is_symlink():
            target = os.readlink(session)
            prefix = f"{draft['date']}-" if draft else ""
            named = root / target
            spec = named / "spec.md"
            if (draft and target.startswith(prefix) and LABEL.fullmatch(target[len(prefix):])
                    and not named.is_symlink() and not spec.is_symlink() and spec.is_file()):
                if reservation.is_symlink() and os.readlink(reservation) == target:
                    reservation.unlink()
                return named
            raise ValueError(f"session alias does not name a sibling session: {session}")

        spec = session / "spec.md"
        if not session.is_dir() or spec.is_symlink() or not spec.is_file():
            raise ValueError(f"session has no local spec.md: {session}")
        if not draft or os.path.lexists(session / "plan.md"):
            return session

        header = spec.read_text(encoding="utf-8").split("\n## ", 1)[0]
        metadata = dict(line.split(":", 1) for line in header.splitlines() if ":" in line)
        if metadata.get("Status", "").strip() != "Validated" or metadata.get("Frozen", "").strip() != "true":
            return session

        prefix = f"{draft['date']}-"
        stem = prefix + short_label(label)
        previous = ()
        if reservation.is_symlink():
            reserved = os.readlink(reservation)
            if not reserved.startswith(prefix) or not LABEL.fullmatch(reserved[len(prefix):]):
                raise ValueError(f"invalid naming reservation: {reservation}")
            previous = (reserved,)

        candidates = (stem if index == 1 else f"{stem}-{index}" for index in count(1))
        for candidate in chain(previous, candidates):
            if not reservation.is_symlink():
                reservation.symlink_to(candidate)
            named = root / candidate
            try:
                # The reserved link becomes valid at the old path in the same operation that moves the directory.
                os.symlink(candidate, candidate, dir_fd=directory)
            except FileExistsError:
                if not named.is_symlink() or os.readlink(named) != candidate:
                    reservation.unlink()
                    continue
            break

        try:
            exchange(directory, session.name, candidate)
        finally:
            if named.is_symlink() and os.readlink(named) == candidate:
                named.unlink()
            reservation.unlink()
        return named
    finally:
        os.close(directory)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path, help="selected directory inside .socrates")
    parser.add_argument("label", help="short, human-readable label for the plan")
    args = parser.parse_args()
    try:
        print(name_session(args.session, args.label))
    except (OSError, ValueError) as error:
        parser.exit(1, f"could not name Socrates session: {error}\n")


if __name__ == "__main__":
    main()
