#!/usr/bin/env python3
"""Import a private Bedrock JSON export into the shell's credential file."""
import json
import math
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import tempfile
import time


def read_export(path):
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("Bedrock token export must be a regular file owned by this user.")
        data = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("Could not read the Bedrock token JSON export.") from None
    return data


def install():
    home = Path.home()
    destination = home / ".config/bedrock/env"
    selected = os.environ.get("BEDROCK_TOKEN_FILE", "")
    if os.path.lexists(destination) and not selected:
        print("Bedrock credentials already configured; preserving the existing file.")
        return
    if selected:
        source = Path(selected).expanduser()
        data = read_export(source)
    else:
        candidates = []
        for path in sorted(home.glob("*.json")):
            if path.name.startswith("."):
                continue
            try:
                data = read_export(path)
            except ValueError:
                continue
            if isinstance(data, dict) and "bearer_token" in data:
                candidates.append((path, data))
        if not candidates:
            print("No Bedrock token export found; skipping credential setup.")
            return
        if len(candidates) > 1:
            raise ValueError("Multiple Bedrock token exports found; select one with BEDROCK_TOKEN_FILE.")
        source, data = candidates[0]

    if not isinstance(data, dict):
        raise ValueError("Bedrock token export must contain a JSON object.")
    token = data.get("bearer_token")
    region = data.get("region")
    if not isinstance(token, str) or not token.strip() or any(ord(c) < 32 for c in token):
        raise ValueError("Bedrock token export has an invalid bearer_token.")
    if not isinstance(region, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+-\d+", region):
        raise ValueError("Bedrock token export has an invalid region.")
    expiration = data.get("expiration")
    if expiration is not None and (
        isinstance(expiration, bool)
        or not isinstance(expiration, (int, float))
        or not math.isfinite(expiration)
        or expiration <= time.time()
    ):
        raise ValueError("Bedrock token export is expired or has an invalid expiration.")
    if destination.is_symlink() or (destination.exists() and not destination.is_file()):
        raise ValueError("Bedrock credential destination must be a regular file.")
    if destination.parent.is_symlink():
        raise ValueError("Bedrock credential directory must not be a symlink.")

    source.chmod(0o600)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.parent.chmod(0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".env-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w") as output:
            output.write(f"export AWS_REGION={shlex.quote(region)}\n")
            output.write(f"export AWS_BEARER_TOKEN_BEDROCK={shlex.quote(token)}\n")
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print("Installed private Bedrock credentials in ~/.config/bedrock/env (mode 600).")


if __name__ == "__main__":
    try:
        install()
    except (ValueError, OSError) as error:
        # Never include parser errors, source contents, or credential values.
        # Validation messages above are safe; OS errors need a generic message.
        message = str(error) if isinstance(error, ValueError) else "Could not install Bedrock credentials."
        print(f"Bedrock credential setup failed: {message}", file=sys.stderr)
        raise SystemExit(1)
