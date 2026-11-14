# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Check skill metadata and local Markdown resource links, not model behavior."""

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

import yaml


class UniqueLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError("frontmatter mapping keys must be strings")
            if key in seen:
                raise ValueError(f"duplicate frontmatter key: {key}")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def validate(folder):
    entrypoint = folder / "SKILL.md"
    text = entrypoint.read_text()
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("SKILL.md requires opening and closing YAML frontmatter")
    end = lines.index("---", 1)
    metadata = yaml.load("\n".join(lines[1:end]), Loader=UniqueLoader)
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter must be a mapping")
    name = metadata.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError("name must use lowercase words separated by hyphens")
    if len(name) > 64 or name != folder.name:
        raise ValueError("name must match the folder and be at most 64 characters")
    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("description must be nonempty text")
    if not "\n".join(lines[end + 1:]).strip():
        raise ValueError("instruction body is empty")
    warnings = []
    if len(description) > 1024:
        raise ValueError("description exceeds 1024 characters")
    if len(description.split()) < 6 or not re.search(r"\b(use|trigger|when)\b", description, re.I):
        warnings.append("description should explain when to select the skill")
    if len(lines) > 500 or len(text.encode("utf-8")) > 16000:
        warnings.append("entrypoint exceeds the default 500-line/4000-estimated-token budget; use conditional references or document an exception")
    for child in folder.iterdir():
        if child.is_file() and child.name.lower() in {"readme.md", "changelog.md", "installation_guide.md"}:
            warnings.append(f"{child.name}: keep instructions in SKILL.md and supporting resources")
        if child.is_dir() and child.name not in {"scripts", "references", "assets", "__pycache__"}:
            warnings.append(f"{child.name}: prefer scripts/, references/, or assets/ for supporting resources")
    for document in [entrypoint, *sorted((folder / "references").rglob("*.md"))]:
        for target in re.findall(r"\]\(([^\s)]+)\)", document.read_text()):
            parsed = urlsplit(target.strip("<>"))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resource = document.resolve().parent / unquote(parsed.path)
            if not resource.exists():
                raise ValueError(f"{document.name}: missing resource {target}")
    return warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folders", type=Path, nargs="+")
    parser.add_argument("--strict", action="store_true", help="treat best-practice warnings as failures")
    parser.add_argument("--json", action="store_true", help="return structured package findings")
    args = parser.parse_args()
    failed = False
    results = []
    for folder in args.folders:
        try:
            warnings = validate(folder)
        except (OSError, ValueError, yaml.YAMLError) as error:
            results.append({"path": str(folder), "errors": [str(error)], "warnings": []})
            failed = True
        else:
            results.append({"path": str(folder), "errors": [], "warnings": warnings})
            failed = failed or bool(args.strict and warnings)
    if args.json:
        print(json.dumps(results))
    else:
        for result in results:
            for error in result["errors"]:
                print(f"{result['path']}: {error}", file=sys.stderr)
            for warning in result["warnings"]:
                print(f"{result['path']}: warning: {warning}")
            if not result["errors"]:
                print(f"{Path(result['path']).name}: package valid (behavior not evaluated)")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
