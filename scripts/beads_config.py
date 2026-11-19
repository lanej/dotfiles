"""Validate and seed the local Beads trial profile without starting services."""

import json
import os
from pathlib import Path
import re
import tempfile
import tomllib


def location(home):
    return Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "beads-service/config.toml"


def fields(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f"{label}: expected exactly {', '.join(expected)}")


def validate(value):
    fields(value, ("version", "profile", "service", "workspace", "history"), "Beads profile")
    if type(value["version"]) is not int or value["version"] != 1 or value["profile"] != "trial":
        raise ValueError("Expected Beads profile version 1 and profile = trial")
    fields(value["service"], ("http_port", "sql_port"), "service")
    ports = value["service"]
    for port in ports.values():
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("Ports must be integers between 1024 and 65535")
    if ports["http_port"] == ports["sql_port"]:
        raise ValueError("Beads HTTP and Dolt SQL need different ports")
    fields(value["workspace"], ("database", "prefix", "branch"), "workspace")
    for key, item in value["workspace"].items():
        if not isinstance(item, str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,62}", item):
            raise ValueError(f"workspace.{key}: use a simple nonempty identifier")
    fields(value["history"], ("remote", "url", "mode"), "history")
    history = value["history"]
    if not isinstance(history["remote"], str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]*", history["remote"]):
        raise ValueError("history.remote: expected a named Dolt remote")
    if not isinstance(history["url"], str) or not re.fullmatch(
            r"git\+https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+\.git", history["url"]):
        raise ValueError("history.url: the trial supports a GitHub git+https URL without credentials")
    if history["mode"] != "manual":
        raise ValueError("history.mode: only manual pushes are supported; no backup timer is installed")
    return value


def load(home):
    config = location(home)
    if not config.is_file():
        raise ValueError(f"Missing {config}; run python3 scripts/beads-service.py install from dotfiles to seed the trial profile")
    return validate(tomllib.loads(config.read_text()))


def seed(home, template):
    """Preserve existing TOML; carry forward only validated legacy port settings."""
    config = location(home)
    if config.exists() or config.is_symlink():
        load(home)
        return
    value = validate(tomllib.loads(template.read_text()))
    legacy = config.with_suffix(".json")
    if legacy.exists() or legacy.is_symlink():
        old = json.loads(legacy.read_text())
        fields(old, ("http_port", "sql_port"), str(legacy))
        value["service"] = old
        validate(value)
    config.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    # Exclusive creation preserves a profile installed concurrently. Legacy JSON is retained unchanged.
    text = "# Local Beads trial profile. Installation preserves this file.\n"
    text += f'version = {value["version"]}\nprofile = "trial"\n'
    for section in ("service", "workspace", "history"):
        text += f"\n[{section}]\n"
        for key, item in value[section].items():
            text += f"{key} = {json.dumps(item)}\n"
    descriptor = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        output.write(text)


def write_record(path, value):
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            json.dump(value, output, indent=2)
            output.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
