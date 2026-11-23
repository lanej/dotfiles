#!/usr/bin/env python3
"""Install Studio and delegate its lifecycle using the project's pinned Bun."""
import argparse
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from zipfile import BadZipFile

from bun_runtime import runtime, runtime_directory

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/lanej/studio.git"


def run(argv, **kwargs):
    return subprocess.check_output(argv, text=True, **kwargs).strip()


def download(url, destination):
    subprocess.run(["curl", "--fail", "--location", "--retry", "3", "--output", str(destination), url], check=True)


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


def installed_runtime(home, source):
    version = (source / ".bun-version").read_text().strip()
    candidates = [runtime_directory(home, source, "studio") / "bun"]
    launcher = home / ".local/bin/studio"
    if launcher.is_symlink():
        candidates.append(launcher.resolve().parents[1] / "runtime/bun")
    if binary := shutil.which("bun"):
        candidates.append(Path(binary))
    for binary in candidates:
        if binary.is_file() and os.access(binary, os.X_OK) and run([str(binary), "--version"]) == version:
            return binary
    raise ValueError("Studio's pinned Bun is missing; run make studio-install first.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="install", choices=("install", "build", "status", "restart"))
    args = parser.parse_args()
    if args.action == "install":
        checkout()
        # The shared controller serializes updates; Studio owns installation and configuration.
        return subprocess.call([sys.executable, str(ROOT / "bin/project-update"), "build", "studio"])
    source = Path.cwd()
    validate_source(source)
    home = Path.home()
    bun = runtime(home, source, "studio", download) if args.action == "build" else installed_runtime(home, source)
    env = {**os.environ, "PATH": str(bun.parent) + os.pathsep + os.environ.get("PATH", "")}
    return subprocess.call([str(bun), "scripts/lifecycle.mjs", args.action], cwd=source, env=env)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError, BadZipFile) as error:
        sys.exit(f"studio: {error}")
