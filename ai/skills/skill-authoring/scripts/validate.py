# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Check skill metadata and local Markdown resource links, not model behavior."""

import argparse
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

import yaml


def validate(folder):
    entrypoint = folder / "SKILL.md"
    text = entrypoint.read_text()
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("SKILL.md requires opening and closing YAML frontmatter")
    end = lines.index("---", 1)
    metadata = yaml.safe_load("\n".join(lines[1:end]))
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
    for document in [entrypoint, *sorted((folder / "references").rglob("*.md"))]:
        for target in re.findall(r"\]\(([^\s)]+)\)", document.read_text()):
            parsed = urlsplit(target.strip("<>"))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resource = document.parent / unquote(parsed.path)
            if not resource.exists():
                raise ValueError(f"{document.name}: missing resource {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folders", type=Path, nargs="+")
    args = parser.parse_args()
    failed = False
    for folder in args.folders:
        try:
            validate(folder)
        except (OSError, ValueError, yaml.YAMLError) as error:
            print(f"{folder}: {error}", file=sys.stderr)
            failed = True
        else:
            print(f"{folder.name}: package valid (behavior not evaluated)")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
