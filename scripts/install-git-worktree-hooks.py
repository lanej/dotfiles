#!/usr/bin/env python3
"""Install the pinned patched Git package without modifying system Git."""

import argparse
import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def catalog():
    with (ROOT / "bootstrap/tools.toml").open("rb") as stream:
        return tomllib.load(stream)["tools"]["git-worktree-hooks"]


def run_git(runtime, *arguments, home):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(HOME=str(home), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    return subprocess.check_output([str(runtime / "bin/git"), *arguments], env=env, text=True, stderr=subprocess.STDOUT).strip()


def validate(runtime, expected, home):
    if run_git(runtime, "--version", home=home) != f"git version {expected}":
        raise ValueError("Archive runtime version does not match the tool catalog")
    actual_exec = Path(run_git(runtime, "--exec-path", home=home)).resolve()
    if actual_exec != (runtime / "libexec/git-core").resolve():
        raise ValueError("Git helpers did not relocate with the runtime")
    if not os.access(runtime / "libexec/git-core/git-remote-http", os.X_OK):
        raise ValueError("Archive is missing the HTTPS helper")
    with tempfile.TemporaryDirectory(prefix="git-install-smoke-") as smoke:
        run_git(runtime, "init", smoke, home=home)
        if not (Path(smoke) / ".git/hooks/pre-commit.sample").is_file():
            raise ValueError("Git templates did not relocate with the runtime")


def managed_link(link, installs):
    if not os.path.lexists(link):
        return True
    if not link.is_symlink():
        return False
    try:
        target = link.resolve()
    except (OSError, RuntimeError):
        return False
    return (target.parent.name == "bin" and target.name == "git"
            and target.parent.parent.parent == installs.resolve()
            and (target.parent.parent / ".archive-sha256").is_file())


def install(archive, home):
    if not hasattr(tarfile, "data_filter"):
        raise ValueError("Safe extraction requires Python 3.11.8+ or 3.12+")
    recipe = catalog()
    expected = recipe["runtime_version"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", expected):
        raise ValueError("Invalid runtime version in catalog")
    installs = home / ".local/opt/git-worktree-hooks"
    active = home / ".local/bin/git"
    if not managed_link(active, installs):
        raise ValueError(f"Refusing to replace user-managed executable or link: {active}")
    if installs.is_symlink():
        raise ValueError(f"Runtime directory must not be a symlink: {installs}")
    destination = installs / expected
    if archive is None and not os.path.lexists(destination):
        os_name = {"Darwin": "darwin", "Linux": "linux"}.get(platform.system())
        if not os_name:
            raise ValueError("Unsupported platform")
        basename = f"git-{recipe['version']}-worktree-hooks-{os_name}-{platform.machine()}.tar.gz"
        with tempfile.TemporaryDirectory(prefix="git-runtime-download-") as temporary:
            archive = Path(temporary) / basename
            for name in (basename + ".sha256", basename):
                url = f"{recipe['release_url']}/{name}"
                print(f"Downloading {url}", flush=True)
                with urllib.request.urlopen(url, timeout=60) as source, (Path(temporary) / name).open("wb") as target:
                    shutil.copyfileobj(source, target)
            return install(archive, home)
    digest = None
    if archive is not None:
        os_name = {"Darwin": "darwin", "Linux": "linux"}.get(platform.system())
        if not os_name:
            raise ValueError("Unsupported platform")
        basename = f"git-{recipe['version']}-worktree-hooks-{os_name}-{platform.machine()}.tar.gz"
        if archive.name != basename:
            raise ValueError(f"Expected platform archive {basename}")
        lines = archive.with_name(archive.name + ".sha256").read_text().splitlines()
        matching = [line.split() for line in lines if len(line.split()) == 2 and line.split()[1].lstrip("*") == archive.name]
        if len(matching) != 1 or not re.fullmatch(r"[0-9a-fA-F]{64}", matching[0][0]):
            raise ValueError("Checksum file must identify this archive exactly once")
        with archive.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != matching[0][0].lower():
            raise ValueError("Archive checksum mismatch")
    if os.path.lexists(destination):
        if destination.is_symlink() or not destination.is_dir():
            raise ValueError(f"Existing runtime is not managed: {destination}")
        installed_digest = (destination / ".archive-sha256").read_text().strip()
        if not re.fullmatch(r"[0-9a-f]{64}", installed_digest) or (digest is not None and installed_digest != digest):
            raise ValueError(f"Existing runtime is not the same managed archive: {destination}")
        validate(destination, expected, home)
    else:
        if archive is None:
            raise ValueError("No managed runtime installed; set DOTFILES_GIT_WORKTREE_HOOKS_ARCHIVE or pass --archive with a downloaded platform archive and its adjacent .sha256 file; see docs/git-worktree-hooks.md")
        installs.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".install-", dir=installs) as temporary:
            staged = Path(temporary) / "runtime"
            staged.mkdir()
            snapshot = Path(temporary) / "archive.tar.gz"
            shutil.copyfile(archive, snapshot)
            with snapshot.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                    raise ValueError("Archive changed before extraction")
                stream.seek(0)
                with tarfile.open(fileobj=stream, mode="r:gz") as source:
                    source.extractall(staged, filter="data")
            validate(staged, expected, home)
            (staged / ".archive-sha256").write_text(digest + "\n")
            staged.rename(destination)
        try:
            validate(destination, expected, home)
        except Exception:
            shutil.rmtree(destination)
            raise
    active.parent.mkdir(parents=True, exist_ok=True)
    if not managed_link(active, installs):
        raise ValueError(f"Refusing to replace user-managed executable or link: {active}")
    with tempfile.TemporaryDirectory(prefix=".git-link-", dir=active.parent) as temporary:
        staged_link = Path(temporary) / "git"
        staged_link.symlink_to(destination / "bin/git")
        os.replace(staged_link, active)
    print(f"Activated {active} -> {destination / 'bin/git'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use a local platform archive and adjacent .sha256 instead of downloading the pinned package")
    parser.add_argument("--home", default=Path.home(), type=Path)
    options = parser.parse_args()
    try:
        install(options.archive.resolve() if options.archive else None, options.home.resolve())
    except (OSError, ValueError, tarfile.TarError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Git runtime install failed: {error}\n")


if __name__ == "__main__":
    main()
