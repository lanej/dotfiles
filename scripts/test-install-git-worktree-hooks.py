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


def fixture_archive(path, *, traversal=False, loader_failure=False):
    with tarfile.open(path, "w:gz") as stream:
        member = tarfile.TarInfo("../escape" if traversal else "bin/git")
        payload = b"#!/bin/sh\nprintf 'git version wrong-version\\n'\n"
        if loader_failure:
            payload = b"#!/bin/sh\necho \"fixture loader: GLIBC_2.34 not found\" >&2\nexit 1\n"
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
        for system, machine, release, package_platform in (
            ("Linux", "x86_64", {"ID": "rocky", "ID_LIKE": "rhel centos", "VERSION_ID": "8.6"}, "linux-el8"),
            ("Linux", "aarch64", {"ID": "almalinux", "ID_LIKE": "rhel centos fedora", "VERSION_ID": "8.10"}, "linux-el8"),
            ("Linux", "x86_64", {"ID": "rhel", "VERSION_ID": "8"}, "linux-el8"),
            ("Linux", "x86_64", {"ID": "ubuntu", "VERSION_ID": "22.04"}, "linux"),
            ("Linux", "x86_64", {"ID": "rocky", "ID_LIKE": "rhel", "VERSION_ID": "9.6"}, "linux"),
            ("Darwin", "arm64", {}, "darwin"),
        ):
            selected = scratch / f"git-{recipe['version']}-worktree-hooks-{package_platform}-{machine}.tar.gz"
            fixture_archive(selected)
            builds = []
            original_run = installer.subprocess.run
            def build(arguments, **kwargs):
                if arguments[:2] != ["bash", str(ROOT / "scripts/build-git-worktree-hooks.sh")]:
                    return original_run(arguments, **kwargs)
                builds.append(arguments)
                assert kwargs["check"]
                output = Path(arguments[-1])
                import shutil
                shutil.copyfile(selected, output / selected.name)
                shutil.copyfile(selected.with_name(selected.name + ".sha256"), output / (selected.name + ".sha256"))
            with patch.object(installer.platform, "system", return_value=system), \
                 patch.object(installer.platform, "machine", return_value=machine), \
                 patch.object(installer.platform, "freedesktop_os_release", return_value=release), \
                 patch.object(installer.subprocess, "run", side_effect=build):
                try:
                    installer.install(None, home)
                except ValueError as error:
                    assert "runtime version" in str(error), str(error)
                else:
                    raise AssertionError("Wrong-version build unexpectedly activated")
            assert len(builds) == 1
            assert not active.exists()
        print("PASS local builds select Enterprise Linux 8, standard Linux and macOS artifacts")

        with patch.object(installer.subprocess, "run", side_effect=OSError("fixture build failed")):
            try:
                installer.install(None, home)
            except OSError as error:
                assert "fixture build failed" in str(error)
            else:
                raise AssertionError("Failed build unexpectedly installed Git")
        assert not active.exists()
        if options.archive:
            real = options.archive.resolve()
            built_home = scratch / "built home with 'quotes"
            builds = []
            original_run = installer.subprocess.run
            def build_real(arguments, **kwargs):
                if arguments[:2] == ["bash", str(ROOT / "scripts/build-git-worktree-hooks.sh")]:
                    import shutil
                    builds.append(arguments)
                    output = Path(arguments[-1])
                    shutil.copyfile(real, output / installer.archive_name(recipe))
                    shutil.copyfile(real.with_name(real.name + ".sha256"), output / (installer.archive_name(recipe) + ".sha256"))
                    return
                return original_run(arguments, **kwargs)
            with patch.object(installer.subprocess, "run", side_effect=build_real):
                installer.install(None, built_home)
                assert len(builds) == 1
                installer.install(None, built_home)
                assert len(builds) == 1, "Rerun rebuilt unchanged source"
                first_runtime = (built_home / ".local/bin/git").resolve()
                with patch.object(installer, "source_identity", return_value="f" * 64):
                    installer.install(None, built_home)
                assert len(builds) == 2, "Changed source inputs did not rebuild"
                assert first_runtime.is_file(), "Updating removed the previous runtime"
                assert (built_home / ".local/bin/git").resolve() != first_runtime
                current = (built_home / ".local/bin/git").readlink()
                with patch.object(installer, "source_identity", return_value="e" * 64), \
                     patch.object(installer.subprocess, "run", side_effect=OSError("fixture build failed")):
                    try:
                        installer.install(None, built_home)
                    except OSError:
                        pass
                    else:
                        raise AssertionError("Failed build unexpectedly activated Git")
                assert (built_home / ".local/bin/git").readlink() == current
            assert (built_home / ".local/bin/git").resolve().name == "git-launcher"
            bootstrap_install(real, home)
            first_target = active.readlink()
            expected_target = home / ".local/opt/git-worktree-hooks" / recipe["runtime_version"] / "bin/git-launcher"
            assert active.resolve() == expected_target, active
            exec_path = subprocess.check_output([str(active), "--exec-path"], text=True).strip()
            assert Path(exec_path).resolve() == expected_target.parent.parent / "libexec/git-core"
            assert subprocess.check_output([str(active), "--version"], text=True).strip() == f"git version {recipe['runtime_version']}"
            checked_install(real, home, success=True)
            assert active.readlink() == first_target
            active.unlink()
            active.symlink_to(expected_target.with_name("git"))
            checked_install(real, home, success=True)
            assert active.readlink() == first_target, "Legacy direct-binary link was not migrated"
            bootstrap_install(real, home)
            assert active.readlink() == first_target
            active.unlink()
            checked_install(real, home, success=True)
            assert active.readlink() == first_target
            print("PASS real activation, relocation, unchanged build reuse and failed-update preservation")
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

        fixture_archive(fixture, loader_failure=True)
        incompatible_home = scratch / "loader-failure-home"
        checked_install(fixture, incompatible_home, success=False, reason="fixture loader: GLIBC_2.34 not found")
        assert not (incompatible_home / ".local/bin/git").exists()
        print("PASS runtime loader diagnostics preserved without activation")

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
