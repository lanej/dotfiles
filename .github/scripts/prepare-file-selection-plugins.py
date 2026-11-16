#!/usr/bin/env python3
"""Fetch the locked plugins needed by the file-selection acceptance check."""

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "destination", type=Path, help="Disposable plugin fixture directory"
    )
    args = parser.parse_args()
    lock = json.loads((ROOT / "nvim/lazy-lock.json").read_text())
    for name, repository in (
        ("fzf-lua", "ibhagwan/fzf-lua"),
        ("nvim-web-devicons", "nvim-tree/nvim-web-devicons"),
    ):
        destination = args.destination / name
        subprocess.run(["git", "init", "--quiet", str(destination)], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(destination),
                "fetch",
                "--quiet",
                "--depth=1",
                f"https://github.com/{repository}.git",
                lock[name]["commit"],
            ],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(destination),
                "checkout",
                "--quiet",
                "--detach",
                "FETCH_HEAD",
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
