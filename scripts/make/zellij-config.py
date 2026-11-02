#!/usr/bin/env python3
"""Keep Zellij's setup wizard from replacing the managed configuration."""

import json
import os
from pathlib import Path
import sys
import tempfile


def main():
    setup_home = Path(sys.argv[1])
    if sys.platform == "darwin":
        data_dir = setup_home / "Library/Application Support/org.Zellij-Contributors.Zellij"
    else:
        data_home = Path(os.environ.get("XDG_DATA_HOME", ""))
        if not data_home.is_absolute():
            data_home = setup_home / ".local/share"
        data_dir = data_home / "zellij"
    path = data_dir / "desktop_integration.json"
    try:
        state = json.loads(path.read_text())
    except FileNotFoundError:
        state = {}
    flags = state.setdefault("flags", [])
    if not isinstance(flags, list):
        raise ValueError(f"Expected a flag list in {path}")
    if "SetupApproved" in flags or "SetupNeverShow" in flags:
        return
    # Upstream's native "never show again" choice; retain all desktop settings.
    flags.append("SetupNeverShow")
    data_dir.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".desktop-integration-", dir=data_dir)
    try:
        with os.fdopen(descriptor, "w") as output:
            json.dump(state, output)
            output.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == "__main__":
    main()
