"""Check shared Bun requirements; only explicit dotfiles setup provisions Bun."""

import fcntl
import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile

from runtime_requirements import combined_requirements, project_requirements, version_key


ROOT = Path(__file__).resolve().parents[1]


def run(argv, **kwargs):
    return subprocess.check_output(argv, text=True, **kwargs).strip()


def runtime_target(system, machine, libc=""):
    system_name = {"Darwin": "darwin", "Linux": "linux"}.get(system)
    architecture = {"arm64": "aarch64", "aarch64": "aarch64", "x86_64": "x64", "amd64": "x64"}.get(machine.lower())
    if system_name is None or architecture is None:
        raise ValueError(f"Unsupported Bun platform: {system}/{machine}")
    native_arch = "arm64" if architecture == "aarch64" else "x64"
    suffix = "-musl" if system_name == "linux" and libc == "musl" else ""
    baseline = "-baseline" if architecture == "x64" else ""
    return f"bun-{system_name}-{architecture}{suffix}{baseline}", f"{system_name}-{native_arch}"


def host_target():
    libc = platform.libc_ver()[0]
    if platform.system() == "Linux" and not libc:
        libc = "musl" if list(Path("/lib").glob("ld-musl-*.so.1")) else "glibc"
    return runtime_target(platform.system(), platform.machine(), libc)


def installed_bun(minimum, *, path=None):
    """Return PATH's qualifying runtime, without resolving package-manager symlinks."""
    binary = shutil.which("bun", path=path)
    if binary is None:
        raise ValueError(f"Bun >= {minimum} is required on PATH; run make install or install Bun with your system package manager")
    version = run([binary, "--version"])
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) or version_key(version) < version_key(minimum):
        raise ValueError(f"Bun >= {minimum} is required on PATH; found {version!r} at {binary}")
    return Path(binary).absolute()


def required_bun(source, home=None):
    requirements = project_requirements(source)
    if "bun" not in requirements:
        raise ValueError(f"{source / 'package.json'} must declare engines.bun as a minimum requirement")
    combined = combined_requirements(home, extra=requirements)
    minimum = combined["bun"]["minimum"]
    catalog = ROOT / "bootstrap/tools.toml"
    if catalog.is_file():
        baseline = tomllib.loads(catalog.read_text())["tools"].get("bun", {}).get("version")
        if baseline and version_key(baseline) > version_key(minimum):
            minimum = baseline
    return minimum


def require_runtime(source, home=None):
    """Read-only lifecycle operations must never install a missing dependency."""
    return installed_bun(required_bun(source, home))


def ensure_runtime(source, home=None):
    """Explicit project installation shares bootstrap's environment-level installer."""
    home = home or Path.home()
    minimum = required_bun(source, home)
    try:
        return installed_bun(minimum)
    except ValueError:
        environment = {**os.environ, "HOME": str(home),
                       "PATH": str(home / ".local/bin") + os.pathsep + os.environ.get("PATH", "")}
        # Arguments remain data; bootstrap contains the only installation policy.
        subprocess.run(["bash", "-c", 'source "$1"; install_package_version bun "$2"',
                        "dotfiles-bun", str(ROOT / "bootstrap.sh"), minimum],
                       env=environment, check=True, stdout=sys.stderr)
        return installed_bun(minimum, path=environment["PATH"])


def download(url, destination):
    subprocess.run(["curl", "--fail", "--location", "--retry", "3", "--output", str(destination), url], check=True)


def install_release(minimum, home=None, *, fetch=download):
    """Fallback for hosts whose package manager cannot provide the shared minimum."""
    version_key(minimum)
    home = home or Path.home()
    name, _ = host_target()
    directory = home / ".local/bin"
    directory.mkdir(parents=True, exist_ok=True)
    state = home / ".local/state/dotfiles"
    state.mkdir(parents=True, exist_ok=True)
    binary = directory / "bun"
    with (state / "bun-install.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        # Another project may already have raised the shared minimum.
        try:
            return installed_bun(minimum)
        except ValueError:
            pass
        if binary.is_symlink():
            raise ValueError(f"Upgrade the package-manager-owned Bun symlink instead of replacing it: {binary}")
        if binary.exists() and not binary.is_file():
            raise ValueError(f"Preserve non-file Bun destination: {binary}")
        if binary.is_file():
            try:
                current = run([str(binary), "--version"])
                if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", current):
                    raise ValueError(f"Preserve unrecognized Bun executable: {binary}")
                if version_key(current) >= version_key(minimum):
                    return binary
            except (OSError, subprocess.CalledProcessError):
                raise ValueError(f"Preserve unrecognized Bun executable: {binary}") from None
        asset = name + ".zip"
        base = f"https://github.com/oven-sh/bun/releases/download/bun-v{minimum}"
        with tempfile.TemporaryDirectory(prefix=".bun-", dir=directory) as temporary:
            stage = Path(temporary)
            fetch(f"{base}/SHASUMS256.txt", stage / "checksums")
            matches = [parts[0] for line in (stage / "checksums").read_text().splitlines()
                       if len(parts := line.split()) == 2 and parts[1].lstrip("*./") == asset]
            if len(matches) != 1 or not re.fullmatch(r"[a-fA-F0-9]{64}", matches[0]):
                raise ValueError(f"Missing or ambiguous checksum for {asset}")
            fetch(f"{base}/{asset}", stage / asset)
            if hashlib.sha256((stage / asset).read_bytes()).hexdigest() != matches[0].lower():
                raise ValueError(f"Checksum mismatch for {asset}")
            with zipfile.ZipFile(stage / asset) as archive:
                candidate = stage / "bun"
                candidate.write_bytes(archive.read(f"{name}/bun"))
            candidate.chmod(0o755)
            if run([str(candidate), "--version"]) != minimum:
                raise ValueError("Downloaded Bun version does not match the selected release")
            os.replace(candidate, binary)
    return binary


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("Usage: bun_runtime.py MINIMUM_VERSION")
        install_release(sys.argv[1])
    except (OSError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        sys.exit(f"bun-runtime: {error}")
