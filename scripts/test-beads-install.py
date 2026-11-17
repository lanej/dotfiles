#!/usr/bin/env python3
"""Exercise the Beads installer through its actual entrypoint without downloads."""
import hashlib
import os
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
print("Beads installation preserves verified, modified and unmanaged files")
