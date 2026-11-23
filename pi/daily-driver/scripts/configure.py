"""Register the local Pi package while preserving unrelated settings and resources."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

package = Path(sys.argv[1]).resolve()
agent = Path(os.environ.get("PI_CODING_AGENT_DIR", sys.argv[2] if len(sys.argv) > 2 else str(Path.home() / ".pi/agent")))
if not (package / "node_modules/@earendil-works/pi-coding-agent/package.json").is_file():
    raise SystemExit("Install dependencies with bun install --frozen-lockfile --ignore-scripts first.")
agent.mkdir(parents=True, exist_ok=True)


def atomic_json(path, value):
    temporary = path.with_name(".pi-driver-" + path.name + "-" + str(os.getpid()))
    try:
        mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as staged:
            os.fchmod(staged.fileno(), mode)
            staged.write(json.dumps(value, indent=2) + "\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


with (agent / ".pi-driver-configure.lock").open("a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    settings = agent / "settings.json"
    registration = agent / "pi-driver-package.json"
    if settings.is_symlink() or registration.is_symlink():
        raise SystemExit("Preserving linked Pi settings or registration; configure its source explicitly.")
    value = json.loads(settings.read_text()) if settings.exists() else {}
    if not isinstance(value, dict):
        raise SystemExit("Pi settings must be an object; existing file preserved.")
    packages = value.get("packages", [])
    if not isinstance(packages, list):
        raise SystemExit("Pi packages must be an array; existing file preserved.")
    record = json.loads(registration.read_text()) if registration.exists() else {}
    managed = record.get("packages", [record["package"]] if "package" in record else [])
    if not isinstance(managed, list) or not all(isinstance(item, str) for item in managed):
        raise SystemExit("Invalid driver registration; existing settings preserved.")
    theme = package / "resources/theme.json"
    if not theme.is_file():
        raise SystemExit("The installed driver theme is missing.")
    theme_link = agent / "themes/dotfiles.json"
    owned_themes = {str(Path(item) / "resources/theme.json") for item in [*managed, str(package)]}
    # The former dotfiles helper registered this package and its generated theme together.
    # Recognize that exact pair while leaving unrelated packages and theme links alone.
    for entry in packages:
        if not isinstance(entry, str):
            continue
        previous = Path(entry)
        if not previous.is_absolute() or previous.name != "daily-driver" or previous.parent.name != "pi":
            continue
        legacy_theme = previous.parents[1] / "design-system/generated/pi.json"
        if not theme_link.is_symlink() or theme_link.resolve() != legacy_theme.resolve():
            continue
        try:
            metadata = json.loads((previous / "package.json").read_text())
        except (OSError, ValueError):
            continue
        if isinstance(metadata, dict) and metadata.get("name") == "@lanej/pi-daily-driver":
            owned_themes.add(str(legacy_theme.resolve()))
            if entry not in managed:
                managed.append(entry)
    if theme_link.is_symlink():
        if str(theme_link.resolve()) not in owned_themes:
            raise SystemExit("Preserving the existing dotfiles.json theme link; configure its source explicitly.")
    elif theme_link.exists():
        raise SystemExit("Preserving the local dotfiles.json theme; configure its source explicitly.")
    runtime = str(package / "runtime/bun") if (package / "runtime/bun").is_file() else "bun"
    subprocess.run([runtime, str(package / "scripts/prepare-delegation.mjs")], check=True)
    # Retain both sides of an interrupted settings update so retry/upgrade can remove only owned registrations.
    atomic_json(registration, {"packages": list(dict.fromkeys([*managed, str(package)]))})
    theme_link.parent.mkdir(parents=True, exist_ok=True)
    temporary_link = theme_link.with_name(".pi-driver-theme-" + str(os.getpid()))
    try:
        temporary_link.symlink_to(theme)
        os.replace(temporary_link, theme_link)
    finally:
        temporary_link.unlink(missing_ok=True)
    value["packages"] = [item for item in packages if item not in managed and item != str(package)] + [str(package)]
    value.setdefault("theme", "dotfiles")
    value.setdefault("quietStartup", True)
    atomic_json(settings, value)
print("Registered the Pi driver.")
