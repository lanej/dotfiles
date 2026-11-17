#!/usr/bin/env python3
"""Exercise the Beads installer through its actual entrypoint without downloads."""
import hashlib
import os
import platform
import tarfile
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="beads-install-") as temporary:
    root = Path(temporary)
    home = root / "home"
    home.mkdir()
    source = root / "bd-fixture"
    source.write_text('#!/bin/sh\nprintf "bd version 1.3.4 (fixture)\\n"\n')
    source.chmod(0o755)
    checksum = source.with_suffix(".sha256")
    checksum.write_text(f"{hashlib.sha256(source.read_bytes()).hexdigest()}  {source.name}\n")
    env = {**os.environ, "HOME": str(home), "BEADS_INSTALL_BINARY": str(source)}

    def install(success=True):
        result = subprocess.run(["sh", str(ROOT / "scripts/install-beads"), "1.3.4"], env=env, capture_output=True, text=True, timeout=20)
        assert (result.returncode == 0) == success, result.stdout + result.stderr
        return result

    install()
    binary = home / ".local/bin/bd"
    receipt = home / ".local/share/beads/install-receipt"
    installed = binary.read_bytes()
    recorded = receipt.read_bytes()
    install()
    assert binary.read_bytes() == installed and receipt.read_bytes() == recorded
    checksum.write_text("0" * 64 + f"  {source.name}\n")
    assert "checksum mismatch" in install(False).stderr
    assert binary.read_bytes() == installed and receipt.read_bytes() == recorded
    binary.write_text("operator modification\n")
    assert "modified" in install(False).stderr
    assert binary.read_text() == "operator modification\n"
    binary.unlink()
    receipt.unlink()
    binary.symlink_to(source)
    assert "unmanaged" in install(False).stderr
    assert binary.is_symlink()
    tools = root / "tools"
    tools.mkdir()
    curl = tools / "curl"
    curl.write_text("""#!/bin/sh
set -eu
while [ "$#" -gt 0 ]; do
 case "$1" in
  -o) output=$2; shift 2 ;;
  https:*) url=$1; shift ;;
  *) shift ;;
 esac
done
case "$url" in
 */checksums.txt) cp "$BEADS_FIXTURE_CHECKSUMS" "$output" ;;
 *.tar.gz) cp "$BEADS_FIXTURE_ARCHIVE" "$output" ;;
 *) exit 1 ;;
esac
""")
    curl.chmod(0o755)
    system = "darwin" if platform.system() == "Darwin" else "linux"
    architecture = "arm64" if platform.machine() in ("arm64", "aarch64") else "amd64"
    asset = f"beads_1.3.4_{system}_{architecture}.tar.gz"
    for index, member in enumerate(("bd", "./bd")):
        archive = root / f"release-{index}.tar.gz"
        with tarfile.open(archive, "w:gz") as stream:
            stream.add(source, arcname=member)
        manifest = root / f"checksums-{index}.txt"
        manifest.write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {asset}\n")
        archive_home = root / f"archive-home-{index}"
        env.update(HOME=str(archive_home), PATH=str(tools) + os.pathsep + os.environ["PATH"], BEADS_FIXTURE_ARCHIVE=str(archive), BEADS_FIXTURE_CHECKSUMS=str(manifest))
        env.pop("BEADS_INSTALL_BINARY", None)
        install()
        assert (archive_home / ".local/bin/bd").read_bytes() == source.read_bytes()
print("Beads installer preserves local work and accepts both official archive layouts")
