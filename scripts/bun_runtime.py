"""Provision a project-pinned private Bun runtime from verified release archives."""
import hashlib
from pathlib import Path
import platform
import re
import subprocess
import tempfile
import zipfile


def run(argv):
    return subprocess.check_output(argv, text=True).strip()


def runtime_directory(home, source, project):
    version = (source / ".bun-version").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Invalid pinned Bun version")
    _, target = host_target()
    return home / ".local/share" / project / "runtime" / target / f"bun-{version}"


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


def runtime(home, source, project, download):
    version = (source / ".bun-version").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Invalid pinned Bun version")
    name, _ = host_target()
    directory = runtime_directory(home, source, project)
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

