#!/usr/bin/env python3
"""Shared file usage for shell fzf and Neovim; no editor runtime required."""
import argparse
from collections import Counter
import contextlib
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

HALF_LIFE = 30 * 24 * 60 * 60


def database():
    state = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return state / "dotfiles/file-history.sqlite3"


def canonical(path):
    return os.path.realpath(os.path.abspath(path))


def decay(score, updated, now):
    return score * math.exp(-math.log(2) * max(0, now - updated) / HALF_LIFE)


def record(paths):
    counts = Counter(canonical(path) for path in paths if Path(path).is_file())
    if not counts:
        return
    location = database()
    location.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Serialize each read/modify/write batch, including across editor processes.
    with contextlib.closing(sqlite3.connect(location, timeout=5)) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS visits (path TEXT PRIMARY KEY, score REAL NOT NULL, updated REAL NOT NULL)")
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            now = time.time()
            for path, count in counts.items():
                previous = connection.execute("SELECT score, updated FROM visits WHERE path = ?", (path,)).fetchone()
                score = decay(*previous, now) if previous else 0
                connection.execute("INSERT OR REPLACE INTO visits VALUES (?, ?, ?)", (path, score + count, now))


def scores():
    location = database()
    if not location.exists():
        return {}
    # Ranking must not create a database or mutate another process's history.
    uri = location.resolve().as_uri() + "?mode=ro"
    with contextlib.closing(sqlite3.connect(uri, uri=True, timeout=5)) as connection:
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'visits'").fetchone():
            return {}
        now = time.time()
        return {path: decay(score, updated, now) for path, score, updated in connection.execute("SELECT path, score, updated FROM visits")}


def candidates(args):
    history = scores()
    if args.global_files:
        paths = [path for path in history if Path(path).is_file()]
    else:
        command = ["git", "ls-files", "--cached", "-z"] if args.git else ["fd", "--print0", "--type", "f", "--exclude", ".git"]
        if not args.git:
            if not args.no_follow:
                command.append("--follow")
            if args.hidden:
                command.append("--hidden")
            if args.no_ignore:
                command.append("--no-ignore")
        result = subprocess.run(command, stdout=subprocess.PIPE, check=True)
        paths = [os.fsdecode(path).removeprefix("./") for path in result.stdout.split(b"\0") if path]
    # Retain user-facing paths; canonical paths are only database identities.
    parents = {}
    def key(path):
        relative = os.path.relpath(path) if os.path.isabs(path) else path
        score = 0
        if history:
            absolute = os.path.abspath(path)
            parent, name = os.path.split(absolute)
            if parent not in parents:
                parents[parent] = os.path.realpath(parent)
            identity = os.path.join(parents[parent], name)
            if os.path.islink(identity):
                identity = os.path.realpath(identity)
            score = history.get(identity, 0)
        return (-score, relative.count(os.sep), len(path), path)
    return sorted(set(paths), key=key)


def output(paths, null=False):
    delimiter = b"\0" if null else b"\n"
    for path in paths:
        sys.stdout.buffer.write(os.fsencode(path) + delimiter)


def pick(args):
    paths = candidates(args)
    if not paths:
        return 1
    command = ["fzf", "--read0", "--print0", "--scheme=path", "--tiebreak=index", "--smart-case", "--multi", "--prompt=Frecent files > "]
    # Ctrl-T's recording binding is separate; this picker records after acceptance.
    result = subprocess.run(command, input=b"\0".join(map(os.fsencode, paths)) + b"\0", stdout=subprocess.PIPE)
    if result.returncode:
        return result.returncode
    selected = [os.fsdecode(path) for path in result.stdout.split(b"\0") if path]
    record(selected)
    output(selected, args.print0)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    visit = commands.add_parser("record", help="Record file selections or file visits")
    visit.add_argument("--stdin", action="store_true", help="Read a JSON array of paths")
    visit.add_argument("paths", nargs="*")
    for name in ("files", "pick"):
        command = commands.add_parser(name)
        command.add_argument("--global", dest="global_files", action="store_true", help="Previously used files across projects")
        command.add_argument("--hidden", action="store_true")
        command.add_argument("--no-ignore", action="store_true")
        command.add_argument("--no-follow", action="store_true")
        command.add_argument("--git", action="store_true")
        command.add_argument("--print0", action="store_true")
    args = parser.parse_args()
    if args.command == "record":
        paths = json.load(sys.stdin) if args.stdin else args.paths
        if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
            parser.error("record expects an array of file paths")
        record(paths)
    elif args.command == "files":
        output(candidates(args), args.print0)
    else:
        return pick(args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, sqlite3.Error, subprocess.CalledProcessError, ValueError) as error:
        print(f"file-history: {error}", file=sys.stderr)
        raise SystemExit(1)
