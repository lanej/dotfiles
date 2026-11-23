"""Combine declared runtime minimums without installing or selecting exact versions."""

import json
import os
from pathlib import Path
import re
import tempfile


RUNTIMES = frozenset({"bun", "node", "go", "rust"})
VERSION = re.compile(r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){0,2}")
PROJECT = re.compile(r"[a-z0-9][a-z0-9_-]*")


def version_key(version):
    """Compare numeric versions, treating omitted minor/patch components as zero."""
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError(f"invalid stable runtime version: {version!r}")
    parts = tuple(int(part) for part in version.split("."))
    return parts + (0,) * (3 - len(parts))


def minimum(requirement, source):
    if not isinstance(requirement, str) or not requirement.startswith(">="):
        raise ValueError(f"{source}: runtime requirement must be a minimum such as >=1.4.5")
    try:
        return ".".join(str(part) for part in version_key(requirement[2:].strip()))
    except ValueError as error:
        raise ValueError(f"{source}: unsupported runtime requirement {requirement!r}; use a stable >= minimum") from error


def read_engines(document, source, *, project=False):
    if not isinstance(document, dict) or not isinstance(document.get("engines"), dict):
        raise ValueError(f"{source}: expected an engines object")
    if not project and "source" in document and not isinstance(document["source"], str):
        raise ValueError(f"{source}: source must be a string")
    engines = document["engines"]
    if not project and set(engines) - RUNTIMES:
        raise ValueError(f"{source}: unsupported runtimes: {', '.join(sorted(set(engines) - RUNTIMES))}")
    supported = {"bun", "node"} if project else RUNTIMES
    return {name: minimum(value, f"{source} engines.{name}")
            for name, value in engines.items() if name in supported}


def project_requirements(source):
    """Read the installed application's Bun/Node minimums from its package manifest."""
    manifest = source / "package.json" if source.is_dir() else source
    return read_engines(json.loads(manifest.read_text()), manifest, project=True)


def requirements_directory(home=None, *, environment=None):
    environment = os.environ if environment is None else environment
    home = Path(home) if home is not None else Path(environment.get("HOME", str(Path.home())))
    configured = environment.get("XDG_CONFIG_HOME")
    if configured == "~" or (configured and configured.startswith("~/")):
        configured = str(home / configured[2:])
    config = Path(configured) if configured else home / ".config"
    return config / "dotfiles/runtime-requirements.d"


def register_requirements(project, requirements, home=None, *, environment=None, source=None):
    """Replace one project's declaration after a successful installation."""
    if not isinstance(project, str) or not PROJECT.fullmatch(project):
        raise ValueError(f"invalid runtime requirement project: {project!r}")
    document = {"engines": {name: f">={version}" for name, version in requirements.items()}}
    read_engines(document, project)
    if source is not None:
        document["source"] = str(source)
    directory = requirements_directory(home, environment=environment)
    destination = directory / f"{project}.json"
    if directory.is_symlink() or destination.is_symlink():
        raise ValueError(f"Preserve symlinked runtime requirements: {destination}")
    directory.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=directory, prefix=f".{project}-", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(document, stream, indent=2)
            stream.write("\n")
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def add_requirements(combined, requirements, source):
    """Add normalized minimums, retaining their origin for installation-plan inspection."""
    for runtime, version in requirements.items():
        if runtime not in RUNTIMES:
            raise ValueError(f"{source}: unsupported runtime: {runtime}")
        key = version_key(version)
        entry = combined.setdefault(runtime, {"minimum": version, "sources": []})
        if key > version_key(entry["minimum"]):
            entry["minimum"] = version
        entry["sources"].append({"source": str(source), "minimum": version})


def combined_requirements(home=None, *, environment=None, extra=None):
    """Read installed declarations plus an optional prepared plan, without effects."""
    environment = os.environ if environment is None else environment
    combined = {}
    directory = requirements_directory(home, environment=environment)
    if directory.exists() and not directory.is_dir():
        raise ValueError(f"runtime requirements must be a directory: {directory}")
    for path in sorted(directory.glob("*.json")):
        document = json.loads(path.read_text())
        add_requirements(combined, read_engines(document, path), path)
    if prepared := environment.get("DOTFILES_RUNTIME_REQUIREMENTS_FILE"):
        path = Path(prepared)
        document = json.loads(path.read_text())
        if not isinstance(document, dict) or not isinstance(document.get("projects"), dict):
            raise ValueError(f"{path}: expected a projects object")
        for project, requirements in document["projects"].items():
            source = f"{path} project {project}"
            floors = read_engines(requirements, source)
            if "source" in requirements:
                source = f"{project}: {requirements['source']}"
            add_requirements(combined, floors, source)
    if extra:
        add_requirements(combined, extra, "requested project")
    return combined
