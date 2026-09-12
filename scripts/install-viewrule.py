#!/usr/bin/env python3
"""Install the pinned Viewrule archive; activate only after a successful setup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


def install():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use a local copy of the pinned archive")
    parser.add_argument("--skip-browser", action="store_true", help="Install the CLI only (e.g. integration CI)")
    args = parser.parse_args()
    pin = json.loads((ROOT / "claude/ui-review/tool.json").read_text())
    install_root = Path(os.environ.get("VIEWRULE_INSTALL_ROOT", Path.home() / ".local/share/viewrule")).expanduser().resolve()
    releases = install_root / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    destination = releases / f'{pin["version"]}-{pin["sha256"][:12]}'
    with tempfile.TemporaryDirectory(prefix=".install-", dir=releases) as temporary:
        temporary = Path(temporary)
        archive = temporary / "viewrule.tgz"
        if args.archive:
            shutil.copyfile(args.archive, archive)
        else:
            try:
                with urllib.request.urlopen(pin["url"], timeout=60) as response, archive.open("wb") as output:
                    shutil.copyfileobj(response, output)
            except OSError as error:
                raise RuntimeError("Cannot download the pinned Viewrule release. The first release must be published before remote installation; use VIEWRULE_DEV_DIR for a local checkout.") from error
        if hashlib.sha256(archive.read_bytes()).hexdigest() != pin["sha256"]:
            raise RuntimeError("Viewrule archive checksum differs from the reviewed pin; installation was not activated.")
        if not destination.exists():
            prefix = temporary / "prefix"
            subprocess.run(["npm", "install", "--prefix", str(prefix), "--no-audit", "--no-fund", str(archive)], check=True)
            package = prefix / "node_modules/viewrule"
            metadata = json.loads((package / "package.json").read_text())
            if metadata["name"] != "viewrule" or metadata["version"] != pin["version"]:
                raise RuntimeError("The installed package does not match the version pin.")
            if not args.skip_browser:
                subprocess.run(["node", str(package / "bin/viewrule.mjs"), "install-browser"], check=True)
            prefix.rename(destination)
        elif not args.skip_browser:
            subprocess.run(["node", str(destination / "node_modules/viewrule/bin/viewrule.mjs"), "install-browser"], check=True)
        # Rename a symlink on the same filesystem: failed setup never switches current.
        pending = temporary / "current"
        pending.symlink_to(destination, target_is_directory=True)
        pending.replace(install_root / "current")
    print(f'Viewrule {pin["version"]} installed at {destination}')


if __name__ == "__main__":
    try:
        install()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Viewrule installation failed: {error}")
