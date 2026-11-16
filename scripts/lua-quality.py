#!/usr/bin/env python3
"""Format and analyze repository-owned Lua, including untracked source files."""

import argparse
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true", help="apply formatting before analysis")
    args = parser.parse_args()
    listed = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT
    )
    files = sorted({name.decode() for name in listed.split(b"\0") if name.endswith(b".lua")
                    and (ROOT / name.decode()).is_file() and not (ROOT / name.decode()).is_symlink()})
    if not files:
        parser.error("no repository-owned Lua files found")
    print(f"Checking {len(files)} Lua files", flush=True)
    commands = [
        ["stylua", "--verify", *([] if args.fix else ["--check"]), "--", *files],
        ["luacheck", "--config", ".luacheckrc", "--codes", "--", *files],
    ]
    failed = False
    for command in commands:
        failed |= subprocess.run(command, cwd=ROOT).returncode != 0
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
