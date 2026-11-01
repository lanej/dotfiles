#!/usr/bin/env python3
"""Resolve explicit dotfiles configuration sets without inspecting the machine."""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import sys

try:
    import tomllib
except ImportError:
    sys.exit("dotfiles-config: Python 3.11+ is required; run bash bootstrap.sh first")


ROOT = Path(__file__).resolve().parents[1]
# One field definition drives runtime validation, exports, and the editor schema.
SETTINGS = {
    "codex.github_enabled": {
        "type": bool,
        "variable": "DOTFILES_CODEX_GITHUB_ENABLED",
        "description": "Enable the Codex GitHub app and its plugins. False keeps GitHub access through gh.",
    },
    "zellij.source": {
        "type": str,
        "enum": ("patched", "release", "main"),
        "variable": "DOTFILES_ZELLIJ_SOURCE",
        "description": "Runtime source: patched includes the checkout's native fixes; release uses upstream stable; main builds pinned upstream without local patches.",
    },
}
SET_NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")
TOOL_FILE = ROOT / "bootstrap/tools.toml"
TOOLS = tomllib.loads(TOOL_FILE.read_text())["tools"]
INSTALLERS = {"package", "system", "config", "build", "rust", "go", "zellij", "font", "treehouse", "firstmate", "macos-window-tool"}
HOOKS = {"github-auth", "bedrock-credentials", "bedrock-router", "agent-status-broker", "kitty-terminfo", "neovim", "atuin-sync", "sql-formatters"}
for tool, recipe in TOOLS.items():
    SETTINGS[f"tools.{tool}"] = {
        "type": bool,
        "description": recipe.get("description", f"Enable the {tool} bootstrap recipe."),
    }


def tool_plan(values, origins, specified, host):
    """Resolve a concrete ordered tool plan; explicit disables constrain dependencies."""
    ordered, visiting = [], []

    def enable(name, required_by=None):
        if name not in TOOLS:
            raise ValueError(f"unknown tool dependency {name!r}")
        key = f"tools.{name}"
        if required_by and key in specified and values[key] is False:
            raise ValueError(f"tools.{required_by} requires tools.{name}, explicitly disabled in {origins[key]}")
        if name in visiting:
            raise ValueError("tool dependency cycle: " + " -> ".join([*visiting, name]))
        if name in ordered:
            return
        recipe = TOOLS[name]
        if recipe.get("platform", host) != host:
            raise ValueError(f"tools.{name} requires {recipe['platform']}; this host is {host}")
        if recipe.get("installer", "package") not in INSTALLERS:
            raise ValueError(f"{TOOL_FILE}: unknown installer for {name}")
        package = recipe.get("package", name)
        version = recipe.get("version", "-")
        if not isinstance(package, str) or not SET_NAME.fullmatch(package):
            raise ValueError(f"{TOOL_FILE}: invalid package name for {name}")
        if not isinstance(version, str) or (version != "-" and not re.fullmatch(r"[0-9]+(?:\.[0-9]+){0,2}", version)):
            raise ValueError(f"{TOOL_FILE}: invalid version for {name}")
        if recipe.get("installer", "package") in {"package", "rust", "go"} and version == "-":
            raise ValueError(f"{TOOL_FILE}: missing version for {name}")
        for target in recipe.get("setup", []):
            if not isinstance(target, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", target):
                raise ValueError(f"{TOOL_FILE}: invalid setup target for {name}")
        for phase in ("prepare", "post"):
            if any(hook not in HOOKS for hook in recipe.get(phase, [])):
                raise ValueError(f"{TOOL_FILE}: unknown {phase} hook for {name}")
        visiting.append(name)
        dependencies = recipe.get("requires", [])
        if name == "zellij" and values["zellij.source"] == "release":
            dependencies = []
        for dependency in dependencies:
            enable(dependency, name)
        visiting.pop()
        if not values[key]:
            values[key] = True
            origins[key] = f"required by tools.{required_by}"
        ordered.append(name)

    for name in TOOLS:
        if values[f"tools.{name}"]:
            enable(name)
    plan = [{"name": name, **TOOLS[name]} for name in ordered]

    def phase(key):
        return list(dict.fromkeys(value for tool in plan for value in tool.get(key, [])))

    return plan, phase("setup"), phase("prepare"), phase("post")


def read(path):
    with path.open("rb") as stream:
        return tomllib.load(stream)


def validate(document, path):
    selected = document.get("sets", [])
    if not isinstance(selected, list) or any(
            not isinstance(name, str) or not SET_NAME.fullmatch(name) for name in selected):
        raise ValueError(f"{path}: sets must be an array of simple lowercase set names")
    values = {}
    for section, fields in document.items():
        if section == "sets":
            continue
        if not isinstance(fields, dict):
            raise ValueError(f"{path}: unknown setting {section}")
        if section not in {key.split(".")[0] for key in SETTINGS}:
            raise ValueError(f"{path}: unknown section {section}")
        for name, value in fields.items():
            key = f"{section}.{name}"
            if key not in SETTINGS:
                raise ValueError(f"{path}: unknown setting {key}")
            expected, choices = SETTINGS[key]["type"], SETTINGS[key].get("enum")
            if type(value) is not expected or (choices and value not in choices):
                allowed = ", ".join(choices) if choices else "true or false"
                raise ValueError(f"{path}: {key} must be {allowed}")
            values[key] = value
    return selected, values


def resolve(path, environment, explicit=False, host="linux"):
    for legacy in ("IS_EASYPOST", "BOOTSTRAP_MERMAID"):
        if legacy in environment:
            raise ValueError(f"{legacy} is retired; select sets or settings in {path}")
    values = {f"tools.{name}": False for name in TOOLS}
    origins = {key: "not selected" for key in values}
    applied, visiting, specified = [], [], set()
    repository_sets = ROOT / "config/sets"
    local_sets = path.parent / "sets"

    def merge(settings, source):
        values.update(settings)
        origins.update({key: str(source) for key in settings})
        specified.update(settings)

    def apply(name):
        if name in visiting:
            raise ValueError("configuration set cycle: " + " -> ".join([*visiting, name]))
        if name in applied:
            return
        # The repository baseline always supplies the defaults. Local sets may
        # override other names, or compose them into a machine/role preset.
        source = repository_sets / f"{name}.toml"
        if name != "base" and (local_sets / f"{name}.toml").exists():
            source = local_sets / f"{name}.toml"
        if not source.is_file():
            raise ValueError(f"unknown configuration set {name!r} (requested by {visiting[-1] if visiting else path})")
        selected, settings = validate(read(source), source)
        visiting.append(name)
        for parent in selected:
            apply(parent)
        visiting.pop()
        merge(settings, source)
        applied.append(name)

    apply("base")
    # A missing conventional file uses the baseline. An explicitly selected
    # DOTFILES_CONFIG must exist, so a typo cannot silently change policy.
    document = read(path) if path.exists() or explicit or "DOTFILES_CONFIG" in environment else {}
    selected, overrides = validate(document, path)
    for name in selected:
        apply(name)
    merge(overrides, path)
    missing = SETTINGS.keys() - values.keys()
    if missing:
        raise ValueError("missing settings: " + ", ".join(sorted(missing)))
    plan, setup, prepare, post = tool_plan(values, origins, specified, host)
    all_setup = list(dict.fromkeys(target for recipe in TOOLS.values() for target in recipe.get("setup", [])))
    if any(not isinstance(target, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", target) for target in all_setup):
        raise ValueError(f"{TOOL_FILE}: invalid setup target")
    return {"sets": applied, "settings": values, "sources": origins, "config": str(path),
            "tools": plan, "setup": setup, "prepare": prepare, "post": post,
            "all_setup": all_setup}


def editor_schema():
    _, defaults = validate(read(ROOT / "config/sets/base.toml"), ROOT / "config/sets/base.toml")
    defaults.update({f"tools.{name}": False for name in TOOLS})
    properties = {
        "sets": {
            "type": "array",
            "description": "Compose named sets in order, then apply this file's individual settings. Local sets are supported; existence and dependency cycles are checked at runtime.",
            "items": {
                "type": "string",
                "pattern": f"^{SET_NAME.pattern}$",
                "anyOf": [
                    {"enum": sorted(path.stem for path in (ROOT / "config/sets").glob("*.toml"))},
                    {"type": "string"},
                ],
            },
        },
    }
    for key, definition in SETTINGS.items():
        section, name = key.split(".")
        group = properties.setdefault(section, {
            "type": "object", "additionalProperties": False, "properties": {},
        })
        field = {
            "type": {bool: "boolean", str: "string"}[definition["type"]],
            "description": definition["description"],
            "default": defaults[key],
        }
        if "enum" in definition:
            field["enum"] = list(definition["enum"])
        group["properties"][name] = field
    return {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Dotfiles configuration",
        "description": "Machine settings and reusable sets. Individual properties override selected sets. All fields are optional; omitted values inherit the base configuration.",
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
    }


def literal(value):
    return json.dumps(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="use an alternate machine configuration")
    parser.add_argument("--format", choices=("toml", "json", "plan", "make", "shell", "schema"), default="toml")
    options = parser.parse_args()
    if options.format == "schema":
        print(json.dumps(editor_schema(), indent=2))
        return
    directory = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    path = Path(options.config or os.environ.get("DOTFILES_CONFIG", str(directory / "dotfiles/config.toml"))).expanduser().resolve()
    host = {"darwin": "macos", "linux": "linux"}.get(sys.platform, sys.platform)
    result = resolve(path, os.environ, explicit=options.config is not None, host=host)
    if options.format == "json":
        print(json.dumps(result, indent=2))
    elif options.format == "plan":
        print(json.dumps({key: result[key] for key in ("sets", "tools", "setup", "prepare", "post")}, indent=2))
    elif options.format in ("make", "shell"):
        if options.format == "shell" and (options.config is not None or "DOTFILES_CONFIG" in os.environ):
            # Bootstrap changes directories when it invokes Make. Carry the
            # same absolute file forward, including when selected relatively.
            print(f"export DOTFILES_CONFIG={shlex.quote(str(path))}")
        for key, definition in SETTINGS.items():
            variable = definition.get("variable")
            if not variable:
                continue
            value = result["settings"][key]
            text = str(value).lower() if isinstance(value, bool) else value
            print(f"{variable}={shlex.quote(text) if options.format == 'shell' else text}")
        for variable, values in (
            ("DOTFILES_TOOLS", [tool["name"] for tool in result["tools"]]),
            ("DOTFILES_SETUP_TARGETS", result["setup"]),
            ("DOTFILES_CONFIG_TARGETS", result["all_setup"]),
            ("DOTFILES_PREPARE_HOOKS", result["prepare"]),
            ("DOTFILES_POST_HOOKS", result["post"]),
        ):
            print(f"{variable}={shlex.quote(','.join(values)) if options.format == 'shell' else ','.join(values)}")
        if options.format == "shell":
            rows = ["\t".join((tool["name"], tool.get("installer", "package"), tool.get("package", tool["name"]), tool.get("version", "-"))) for tool in result["tools"]]
            print(f"DOTFILES_INSTALL_PLAN={shlex.quote(chr(10).join(rows))}")
    else:
        print(f"# Machine configuration: {path}")
        print(f"# Applied sets: {', '.join(result['sets'])}")
        print("# Unlisted bootstrap recipes are disabled.")
        section = None
        for key, value in result["settings"].items():
            if key.startswith("tools.") and not value and result["sources"][key] == "not selected":
                continue
            group, name = key.split(".")
            if group != section:
                print(f"\n[{group}]")
                section = group
            print(f"# From {result['sources'][key]}")
            print(f"{name} = {literal(value)}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        print(f"dotfiles-config: {error}", file=sys.stderr)
        sys.exit(1)
