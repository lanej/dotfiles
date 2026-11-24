#!/usr/bin/env python3
"""Install Studio and delegate its lifecycle using the shared environment Bun."""
import argparse
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from bun_runtime import ensure_runtime, require_runtime
from runtime_requirements import project_requirements, register_requirements

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/lanej/studio.git"


def run(argv, **kwargs):
    return subprocess.check_output(argv, text=True, **kwargs).strip()


def checkout():
    controller = runpy.run_path(str(ROOT / "bin/project-update"))
    source = controller["load_projects"](ROOT / "config/project-updates.toml")["studio"]["path"]
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".studio-", dir=source.parent) as temporary:
            stage = Path(temporary) / "checkout"
            subprocess.run(["git", "clone", "--", REPOSITORY, str(stage)], check=True)
            stage.rename(source)
    validate_source(source)
    return source


def validate_source(source):
    remotes = run(["git", "-C", str(source), "config", "--get-regexp", r"^remote\..*\.url$"]).splitlines()
    accepted = {REPOSITORY, "https://github.com/lanej/studio", "git@github.com:lanej/studio.git", "ssh://git@github.com/lanej/studio.git"}
    if not any(line.split(None, 1)[-1] in accepted for line in remotes):
        raise ValueError(f"Preserve unrecognized Studio checkout: {source}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="install", choices=("install", "build", "status", "inventory", "checkpoint", "restart", "restore", "verify"))
    args = parser.parse_args()
    if args.action == "install":
        checkout()
        # The shared controller serializes updates; Studio owns installation and configuration.
        return subprocess.call([sys.executable, str(ROOT / "bin/project-update"), "build", "studio"])
    source = Path.cwd()
    validate_source(source)
    home = Path.home()
    bun = ensure_runtime(source, home) if args.action == "build" else require_runtime(source, home)
    env = {**os.environ, "PATH": str(bun.parent) + os.pathsep + os.environ.get("PATH", "")}
    result = subprocess.call([str(bun), "scripts/lifecycle.mjs", args.action], cwd=source, env=env)
    if result == 0 and args.action == "build":
        register_requirements("studio", project_requirements(source), home, source=str(source / "package.json"))
    return result


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(f"studio: {error}")
