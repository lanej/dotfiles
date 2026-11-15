#!/usr/bin/env python3
"""Install selected approval tools through their project-owned native installers."""

import argparse
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
REPOSITORIES = {"intent": "https://github.com/lanej/intent.git",
                "keylease": "https://github.com/lanej/keylease.git"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", choices=REPOSITORIES)
    args = parser.parse_args()
    controller = runpy.run_path(str(ROOT / "bin/project-update"))
    projects = controller["load_projects"](ROOT / "config/project-updates.toml")
    path = projects[args.project]["path"]
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--", REPOSITORIES[args.project], str(path)], check=True)
    # Existing checkouts remain at their selected revision. The shared controller
    # owns dirty-checkout protection, serialization and native-install receipts.
    subprocess.run([sys.executable, str(ROOT / "bin/project-update"), "build", args.project], check=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"approval-cli: {error}")
