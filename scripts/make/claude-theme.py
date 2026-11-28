"""Apply the configured theme to an alternate Claude profile."""

import json
import os
import stat
import sys
import tempfile
from pathlib import Path


def apply_theme(managed, profile):
    theme = json.loads(managed.read_text(encoding="utf-8"))["theme"]
    path = profile.resolve()
    original = path.read_bytes() if path.exists() else None
    settings = json.loads(original) if original is not None else {}
    if not isinstance(settings, dict):
        raise ValueError(f"{profile} must contain a JSON object")
    if settings.get("theme") == theme:
        return
    settings["theme"] = theme
    mode = stat.S_IMODE(path.stat().st_mode) if original is not None else 0o600
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            json.dump(settings, output, indent=2, ensure_ascii=False)
            output.write("\n")
            output.flush()
            os.fchmod(output.fileno(), mode)
            if profile.resolve() != path or (path.read_bytes() if path.exists() else None) != original:
                raise ValueError(f"settings changed during installation: {profile}")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        apply_theme(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError) as error:
        sys.exit(f"Cannot set the Claude theme in {sys.argv[2]}: {error}")
