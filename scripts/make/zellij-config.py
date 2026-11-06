#!/usr/bin/env python3
"""Keep Zellij's setup wizard from replacing the managed configuration."""

import json
import os
from pathlib import Path
import re
import sys
import tempfile


def main():
    setup_home = Path(sys.argv[1])
    configure_navigation_permissions(setup_home)
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


def configure_navigation_permissions(setup_home):
    if sys.platform == "darwin":
        cache = setup_home / "Library/Caches/org.Zellij-Contributors.Zellij"
    else:
        cache = Path(os.environ.get("XDG_CACHE_HOME", ""))
        if not cache.is_absolute():
            cache = setup_home / ".cache"
        cache /= "zellij"
    path = cache / "permissions.kdl"
    plugin = setup_home / ".local/share/zellij/plugins/pane-navigation.wasm"
    name = json.dumps(str(plugin), ensure_ascii=False)
    permissions = ("ReadApplicationState", "ChangeApplicationState", "WriteToStdin", "Reconfigure")
    entry = name + """ {
    ReadApplicationState
    ChangeApplicationState
    WriteToStdin
    Reconfigure
}
"""
    try:
        existing = path.read_text()
    except FileNotFoundError:
        existing = ""
    # WHY: Zellij rewrites these native cache nodes with a different permission order.
    nodes = re.findall(r"(?m)^" + re.escape(name) + r"\s*\{([^}]*)\}", existing)
    if nodes and all(re.search(r"(?m)^\s*" + permission + r"\s*;?\s*$", nodes[-1])
                     for permission in permissions):
        return
    cache.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".navigation-permissions-", dir=cache)
    try:
        with os.fdopen(descriptor, "w") as output:
            output.write(existing.rstrip() + "\n" + entry)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == "__main__":
    main()
