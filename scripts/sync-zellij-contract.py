#!/usr/bin/env python3
"""Sync the runtime's complete generated Rust IPC contract without code generation."""

import argparse
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    revision = re.search(r"^zellij_revision=([a-f0-9]+)$", (ROOT / "scripts/install-zellij").read_text(), re.M)[1]
    url = f"https://raw.githubusercontent.com/lanej/zellij/{revision}/zellij-utils/assets/prost_ipc/client_server_contract.rs"
    with urllib.request.urlopen(url, timeout=30) as response:
        contract = response.read()
    destination = ROOT / "zellij/cli/src/ipc/contract.rs"
    if args.check:
        if destination.read_bytes() != contract:
            raise SystemExit("Zellij IPC contract is stale; run python3 scripts/sync-zellij-contract.py")
    else:
        destination.write_bytes(contract)


if __name__ == "__main__":
    main()
