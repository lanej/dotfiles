"""Detect project language context from Git's file inventory and manifest names."""

import json
import os
from pathlib import Path
import subprocess


IGNORED = {".git", ".agents", ".claude", ".codex", ".typescript-quality", "vendor", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target", "third_party", "third-party"}


def detect(root, definitions, excluded=()):
    rules = json.loads(definitions.read_text())
    if not isinstance(rules, dict) or not rules:
        raise ValueError("language definitions must be a nonempty mapping")
    for rule in rules.values():
        if not isinstance(rule, dict) or not isinstance(rule.get("skill"), str) or not all(
            isinstance(rule.get(key), list) and all(isinstance(value, str) and value for value in rule[key])
            for key in ("extensions", "manifests")):
            raise ValueError("invalid language definition")
    environment = dict(os.environ)
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        environment.pop(name, None)
    inventory = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"], capture_output=True, env=environment)
    files = set()
    if inventory.returncode == 0:
        files.update(Path(name.decode("utf-8", errors="surrogateescape")) for name in inventory.stdout.split(b"\0") if name)
    elif not (root / ".git").exists():
        for directory, children, names in os.walk(root):
            children[:] = [name for name in children if name not in IGNORED and not name.startswith(".")]
            files.update((Path(directory) / name).relative_to(root) for name in names)
    else:
        raise ValueError("Git could not inventory project files for language detection")
    evidence = {}
    for relative in sorted(files):
        if relative.as_posix() in excluded or any(part in IGNORED for part in relative.parts):
            continue
        if not (root / relative).is_file():
            continue
        for language, rule in rules.items():
            if relative.suffix in rule["extensions"] or relative.name in rule["manifests"] or language == "typescript" and relative.name.startswith("tsconfig.") and relative.suffix == ".json":
                evidence.setdefault(language, set()).add(relative.as_posix())
        if relative.name == "package.json":
            try:
                package = json.loads((root / relative).read_text())
                if isinstance(package, dict) and any(isinstance(package.get(key), dict) and "typescript" in package[key]
                                                    for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")):
                    evidence.setdefault("typescript", set()).add(relative.as_posix())
            except (OSError, ValueError):
                pass
    return {"languages": sorted(evidence), "skills": sorted({rules[name]["skill"] for name in evidence}),
            "evidence": {name: sorted(paths)[:5] for name, paths in sorted(evidence.items())}}
