#!/usr/bin/env python3
"""Exercise isolated installer activation with a real artifact and unsafe inputs."""

import argparse
import hashlib
import io
import importlib.util
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/install-git-worktree-hooks.py"


def checked_install(archive, home, *, success, reason=""):
    arguments = [sys.executable, str(INSTALLER), "--home", str(home)]
    if archive is not None:
        arguments.extend(["--archive", str(archive)])
    result = subprocess.run(arguments, text=True, capture_output=True)
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    if reason:
        assert reason in result.stderr, result.stderr
    return result


def bootstrap_install(archive, home):
    env = {**os.environ, "HOME": str(home),
           "DOTFILES_INSTALL_PLAN": "git-worktree-hooks\tgit-worktree-hooks\tgit-worktree-hooks\t2.56.0"}
    env.pop("DOTFILES_GIT_WORKTREE_HOOKS_ARCHIVE", None)
    if archive:
        env["DOTFILES_GIT_WORKTREE_HOOKS_ARCHIVE"] = str(archive)
    subprocess.run(["bash", "-c", 'source "$1"; install_config_runtime() { :; }; load_dotfiles_config() { :; }; install_dependencies',
                    "git-runtime-bootstrap-test", str(ROOT / "bootstrap.sh")], env=env, check=True, capture_output=True, text=True)


def checksum(archive):
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    archive.with_name(archive.name + ".sha256").write_text(f"{digest}  {archive.name}\n")


def fixture_archive(path, *, traversal=False):
    with tarfile.open(path, "w:gz") as stream:
        member = tarfile.TarInfo("../escape" if traversal else "bin/git")
        payload = b"#!/bin/sh\nprintf 'git version wrong-version\\n'\n"
        member.size = len(payload)
        member.mode = 0o755
        stream.addfile(member, io.BytesIO(payload))
    checksum(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Real runtime artifact; enables relocation and idempotency acceptance")
    options = parser.parse_args()
    with (ROOT / "bootstrap/tools.toml").open("rb") as stream:
        recipe = tomllib.load(stream)["tools"]["git-worktree-hooks"]
    basename = f"git-{recipe['version']}-worktree-hooks-{platform.system().lower()}-{platform.machine()}.tar.gz"
    with tempfile.TemporaryDirectory(prefix="git-runtime-install-test-") as temporary:
        scratch = Path(temporary).resolve()
        home = scratch / "home"
        home.mkdir()
        active = home / ".local/bin/git"
        spec = importlib.util.spec_from_file_location("git_runtime_installer", INSTALLER)
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with patch.object(installer.urllib.request, "urlopen", side_effect=OSError("fixture download failed")):
            try:
                installer.install(None, home)
            except OSError as error:
                assert "fixture download failed" in str(error)
            else:
                raise AssertionError("Missing download unexpectedly installed Git")
        assert not active.exists()
        if options.archive:
            real = options.archive.resolve()
            downloaded_home = scratch / "downloaded-home"
            requests = []
            def download(url, timeout):
                requests.append(url)
                assert timeout == 60
                assert url.startswith(recipe["release_url"] + "/")
                return real.with_name(url.rsplit("/", 1)[1]).open("rb")
            with patch.object(installer.urllib.request, "urlopen", side_effect=download):
                installer.install(None, downloaded_home)
                assert len(requests) == 2
                installer.install(None, downloaded_home)
                assert len(requests) == 2, "Rerun downloaded the installed runtime again"
            assert (downloaded_home / ".local/bin/git").resolve().name == "git"
            bootstrap_install(real, home)
            first_target = active.readlink()
            expected_target = home / ".local/opt/git-worktree-hooks" / recipe["runtime_version"] / "bin/git"
            assert active.resolve() == expected_target, active
            assert subprocess.check_output([str(active), "--version"], text=True).strip() == f"git version {recipe['runtime_version']}"
            checked_install(real, home, success=True)
            assert active.readlink() == first_target
            bootstrap_install(None, home)
            assert active.readlink() == first_target
            active.unlink()
            checked_install(None, home, success=True)
            assert active.readlink() == first_target
            print("PASS real archive activation, runtime relocation and rerun/reactivation without archive")
            incompatible = scratch / "incompatible" / real.name
            incompatible.parent.mkdir()
            replaced_helper = False
            with tarfile.open(real, "r:gz") as source, tarfile.open(incompatible, "w:gz") as target:
                for member in source.getmembers():
                    if member.name.removeprefix("./") == "libexec/git-core/git-remote-http":
                        replaced_helper = True
                        member.type = tarfile.REGTYPE
                        member.linkname = ""
                        payload = b"#!/bin/sh\necho 'fixture loader failure' >&2\nexit 127\n"
                        member.size = len(payload)
                        target.addfile(member, io.BytesIO(payload))
                    else:
                        target.addfile(member, source.extractfile(member) if member.isfile() else None)
            assert replaced_helper, "Real archive did not contain the exercised helper"
            checksum(incompatible)
            incompatible_home = scratch / "incompatible-home"
            checked_install(incompatible, incompatible_home, success=False, reason="HTTPS helper cannot run")
            assert not (incompatible_home / ".local/bin/git").exists()
            print("PASS incompatible HTTPS helper cannot activate Git")
        else:
            print("SKIP real runtime activation (pass --archive to exercise it)")

        fixture = scratch / basename
        fixture_archive(fixture)
        before = active.readlink() if active.is_symlink() else None
        checked_install(fixture, home, success=False, reason="runtime version" if before is None else "not the same managed archive")
        assert (active.readlink() if active.is_symlink() else None) == before
        checked_install(fixture, scratch / "wrong-version-home", success=False, reason="runtime version")
        fixture.with_name(fixture.name + ".sha256").write_text(f"{'0' * 64}  {fixture.name}\n")
        checked_install(fixture, home, success=False, reason="checksum mismatch")
        assert (active.readlink() if active.is_symlink() else None) == before
        print("PASS invalid version/archive and checksum leave activation unchanged")

        fixture_archive(fixture, traversal=True)
        unsafe_home = scratch / "unsafe-home"
        checked_install(fixture, unsafe_home, success=False, reason="outside the destination")
        assert not (unsafe_home / ".local/bin/git").exists()
        assert not list(unsafe_home.rglob("escape"))
        print("PASS unsafe archive extraction rejected")

        fixture_archive(fixture)
        owned_home = scratch / "owned-home"
        owned = owned_home / ".local/bin/git"
        owned.parent.mkdir(parents=True)
        owned.write_text("user-managed executable\n")
        checked_install(options.archive.resolve() if options.archive else fixture, owned_home, success=False, reason="user-managed")
        assert owned.read_text() == "user-managed executable\n"
        owned.unlink()
        owned.symlink_to("/usr/bin/git")
        checked_install(options.archive.resolve() if options.archive else fixture, owned_home, success=False, reason="user-managed")
        assert os.readlink(owned) == "/usr/bin/git"
        print("PASS user-owned executable and link preserved")


if __name__ == "__main__":
    main()
