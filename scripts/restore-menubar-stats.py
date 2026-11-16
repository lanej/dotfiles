#!/usr/bin/env python3
"""Merge the portable preset into MenuBar Stats preferences while it is closed."""

import copy
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path


def merge(settings, preset):
    for key, value in preset.items():
        if isinstance(value, dict) and isinstance(settings.get(key), dict):
            merge(settings[key], value)
        else:
            settings[key] = copy.deepcopy(value)


def export(preferences):
    return subprocess.run(
        ["defaults", "export", str(preferences), "-"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def main():
    preset_path, preferences = map(Path, sys.argv[1:])
    preset = plistlib.loads(preset_path.read_bytes())
    if Path(f"{preferences}.plist").exists():
        original = export(preferences)
        settings = plistlib.loads(original)
        with tempfile.NamedTemporaryFile(
            prefix=f"{preferences.name}.backup-",
            suffix=".plist",
            dir=preferences.parent,
            delete=False,
        ) as backup:
            backup.write(original)
            print(f"Preferences backup: {backup.name}", flush=True)
    else:
        settings = {}
    merge(settings, preset)
    subprocess.run(
        ["defaults", "import", str(preferences), "-"],
        input=plistlib.dumps(settings),
        check=True,
    )
    if plistlib.loads(export(preferences)) != settings:
        raise RuntimeError("MenuBar Stats preferences did not match the restored settings.")
    print("MenuBar Stats settings restored. Reopen MenuBar Stats.")


if __name__ == "__main__":
    main()
