#!/usr/bin/env python3
"""Install Octo releases and control their native macOS and Linux services."""
import argparse
import hashlib
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



def runtime_target(system, machine, libc=""):
    system_name = {"Darwin": "darwin", "Linux": "linux"}.get(system)
    architecture = {"arm64": "aarch64", "aarch64": "aarch64", "x86_64": "x64", "amd64": "x64"}.get(machine.lower())
    if system_name is None or architecture is None:
        raise ValueError(f"Unsupported Octo platform: {system}/{machine}")
    native_arch = "arm64" if architecture == "aarch64" else "x64"
    suffix = "-musl" if system_name == "linux" and libc == "musl" else ""
    baseline = "-baseline" if architecture == "x64" else ""
    return f"bun-{system_name}-{architecture}{suffix}{baseline}", f"{system_name}-{native_arch}"


def host_target():
    libc = platform.libc_ver()[0]
    if platform.system() == "Linux" and not libc:
        libc = "musl" if list(Path("/lib").glob("ld-musl-*.so.1")) else "glibc"
    return runtime_target(platform.system(), platform.machine(), libc)


def runtime(home, source):
    version = (source / ".bun-version").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Invalid pinned Bun version")
    name, target = host_target()
    directory = home / ".local/share/octo-manager/runtime" / target / f"bun-{version}"
    if directory.is_symlink():
        raise ValueError(f"Preserve symlinked runtime: {directory}")
    binary = directory / "bun"
    if binary.is_symlink():
        raise ValueError(f"Preserve symlinked runtime binary: {binary}")
    if binary.exists():
        if run([str(binary), "--version"]) != version:
            raise ValueError(f"Installed private Bun version does not match {version}")
        return binary
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    asset = name + ".zip"
    base = f"https://github.com/oven-sh/bun/releases/download/bun-v{version}"
    with tempfile.TemporaryDirectory(prefix=".download-", dir=directory) as temporary:
        stage = Path(temporary)
        download(f"{base}/SHASUMS256.txt", stage / "checksums")
        checksums = [line.split() for line in (stage / "checksums").read_text().splitlines()]
        matches = [digest for digest, filename in checksums if filename.lstrip("*./") == asset]
        if len(matches) != 1 or not re.fullmatch(r"[a-fA-F0-9]{64}", matches[0]):
            raise ValueError(f"Missing or ambiguous checksum for {asset}")
        download(f"{base}/{asset}", stage / asset)
        if hashlib.sha256((stage / asset).read_bytes()).hexdigest() != matches[0].lower():
            raise ValueError(f"Checksum mismatch for {asset}")
        with zipfile.ZipFile(stage / asset) as archive:
            candidate = stage / "bun"
            candidate.write_bytes(archive.read(f"{name}/bun"))
        candidate.chmod(0o755)
        if run([str(candidate), "--version"]) != version:
            raise ValueError("Downloaded Bun version does not match")
        candidate.rename(binary)
    return binary


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
