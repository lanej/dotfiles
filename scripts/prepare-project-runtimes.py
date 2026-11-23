#!/usr/bin/env python3
"""Read selected project manifests before installing shared runtime dependencies."""

import argparse
import json
from pathlib import Path
import runpy
import subprocess
import sys

from runtime_requirements import project_requirements


ROOT = Path(__file__).resolve().parents[1]


def prepare(selected):
    projects = {}
    for project, entrypoint in (("studio", "checkout"), ("octo-manager", "prepare_source")):
        if project not in selected:
            continue
        adapter = runpy.run_path(str(ROOT / f"scripts/install-{project}.py"))
        source = adapter[entrypoint]()
        requirements = project_requirements(source)
        if "bun" not in requirements:
            raise ValueError(f"{source / 'package.json'} must declare engines.bun")
        projects[project] = {"engines": {name: f">={minimum}" for name, minimum in requirements.items()},
                             "source": str(source / "package.json")}
    return {"projects": projects}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", required=True, help="comma-separated selected tools")
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    requirements = prepare(set(options.tools.split(",")))
    options.output.write_text(json.dumps(requirements, indent=2) + "\n")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"project-runtimes: {error}")
