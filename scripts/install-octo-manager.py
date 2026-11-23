#!/usr/bin/env python3
"""Install Octo releases and control their native macOS and Linux services."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import tomllib
import zipfile

from bun_runtime import runtime as project_runtime, runtime_target, host_target

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/lanej/octo-manager.git"


def run(argv, *, cwd=None, env=None):
    return subprocess.run(argv, cwd=cwd, env=env, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()


def download(url, destination):
    run(["curl", "--fail", "--location", "--retry", "3", "--output", str(destination), url])


def source_checkout(cache, revision):
    source = cache / revision
    if source.is_symlink():
        raise ValueError(f"Preserve symlinked source cache: {source}")
    if not source.exists():
        with tempfile.TemporaryDirectory(prefix=".source-", dir=cache) as temporary:
            stage = Path(temporary) / "checkout"
            run(["git", "init", "--quiet", str(stage)])
            run(["git", "remote", "add", "origin", REPOSITORY], cwd=stage)
            run(["git", "fetch", "--quiet", "--depth", "1", "origin", revision], cwd=stage)
            run(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=stage)
            stage.rename(source)
    if (run(["git", "rev-parse", "HEAD"], cwd=source) != revision or
            run(["git", "remote", "get-url", "origin"], cwd=source) != REPOSITORY or
            run(["git", "status", "--porcelain"], cwd=source)):
        raise ValueError(f"Preserve modified or unrecognized Octo source cache: {source}")
    return source



def runtime(home, source):
    return project_runtime(home, source, "octo-manager", download)



def latest_revision():
    fields = run(["git", "ls-remote", "--exit-code", REPOSITORY, "refs/heads/main"]).split()
    if len(fields) != 2 or fields[1] != "refs/heads/main" or not re.fullmatch(r"[a-f0-9]{40}", fields[0]):
        raise ValueError("Could not identify the exact Octo main revision")
    return fields[0]


def installed_revision(home):
    metadata = home / ".local/share/octo-manager/current/release.json"
    if not metadata.is_file():
        raise ValueError("Octo is not installed; run make octo-manager-install")
    release = json.loads(metadata.read_text())
    revision = release.get("revision") if isinstance(release, dict) else None
    if not isinstance(revision, str) or not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError(f"Installed Octo revision is invalid: {metadata}")
    return revision


def manage_service(action, home):
    system = platform.system()
    if system == "Darwin":
        label = "com.lanej.octo-manager"
        definition = home / "Library/LaunchAgents" / f"{label}.plist"
    elif system == "Linux":
        label = "octo-manager.service"
        config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        definition = config / "systemd/user" / label
    else:
        raise ValueError(f"Unsupported Octo service platform: {system}")
    if not definition.is_file():
        raise ValueError(f"Missing Octo service definition: {definition}; run make octo-manager-install")
    if system == "Darwin":
        domain = f"gui/{os.getuid()}"
        target = f"{domain}/{label}"
        run(["launchctl", "enable", target])
        loaded = subprocess.run(["launchctl", "print", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if not loaded:
            run(["launchctl", "bootstrap", domain, str(definition)])
        run(["launchctl", "kickstart", *(["-k"] if action == "restart" and loaded else []), target])
    else:
        run(["systemctl", "--user", "daemon-reload"])
        run(["systemctl", "--user", "enable", str(definition.resolve())])
        run(["systemctl", "--user", action, label])
    print(f"Octo service {action} requested: {label}")


def install(root=ROOT, home=None, revision=None):
    _, target = host_target()
    home = home or Path.home()
    if revision is None:
        recipe = tomllib.loads((root / "bootstrap/tools.toml").read_text())["tools"]["octo-manager"]
        revision = recipe["revision"]
    if not isinstance(revision, str) or not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Octo Manager requires a full source revision")
    cache = Path(os.environ.get("XDG_CACHE_HOME", home / ".cache")) / "dotfiles/octo-manager" / target
    if cache.is_symlink():
        raise ValueError(f"Preserve symlinked install cache: {cache}")
    cache.mkdir(parents=True, mode=0o700, exist_ok=True)
    lock = cache / ".install-lock"
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError:
        raise ValueError(f"Octo installation already locked: {lock}") from None
    try:
        source = source_checkout(cache, revision)
        bun = runtime(home, source)
        env = {**os.environ, "PATH": str(bun.parent) + os.pathsep + os.environ.get("PATH", "")}
        run([str(bun), "install", "--frozen-lockfile", "--ignore-scripts"], cwd=source, env=env)
        result = run([str(bun), "scripts/install-local.ts", "--home", str(home), "--codex"], cwd=source, env=env)
        print(result)
        print("Octo hooks configured. Review them in Codex /hooks if the host requests trust approval.")
    finally:
        lock.rmdir()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="install", choices=("install", "reinstall", "pull-latest", "start", "restart"))
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args(argv)
    if args.action in ("start", "restart"):
        manage_service(args.action, args.home)
    else:
        revision = None
        if args.action == "pull-latest":
            revision = latest_revision()
        elif args.action == "reinstall":
            revision = installed_revision(args.home)
        install(ROOT, args.home, revision)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        sys.exit(f"install-octo-manager: {error}")
