"""Check review provenance; this does not grade model behavior or run model calls."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
CONTROL_FILES = {
    "AGENTS.md", "CLAUDE.md", "GEMINI.md", "claude/CLAUDE.md", "gemini/GEMINI.md",
    "docs/skill-maintenance.md", ".github/workflows/skill-maintenance.yml",
    "claude/evals/skill-maintenance/check_evidence.py",
    "claude/evals/skill-maintenance/check_size.py",
    "claude/evals/skill-maintenance/size-budgets.json",
}


def governed(path):
    return path in CONTROL_FILES or path.startswith((
        "claude/skills/", "claude/commands/", "claude/agents/", "gemini/skills/"))


def local_path(root, name):
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("Expected a repository-relative path")
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or str(relative) != name:
        raise ValueError(f"Unsafe evidence path: {name}")
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Evidence path escapes repository: {name}")
    if any(part.is_symlink() for part in [path, *path.parents] if part != root.parent):
        # Repo-owned, tracked regular files only; external skill links are not evidence.
        raise ValueError(f"Symlink is not captured evidence: {name}")
    return path


def matches(root, name, expected, allow_absent=False):
    path = local_path(root, name)
    if expected is None and allow_absent:
        return not path.exists()
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        return False
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected


def validate(root, record):
    if not isinstance(record, dict) or record.get("version") != 1:
        raise ValueError("Expected evidence version 1")
    sources = record.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("No captured instruction sources")
    for name, digest in sources.items():
        if not matches(root, name, digest, allow_absent=True):
            raise ValueError(f"Source changed or missing: {name}")
    artifacts = record.get("artifacts")
    if not isinstance(artifacts, dict) or not {"baseline", "candidate", "review"} <= artifacts.keys():
        raise ValueError("Baseline, candidate, and review artifacts are required")
    paths = []
    for role, artifact in artifacts.items():
        if not isinstance(artifact, dict) or not matches(root, artifact.get("path"), artifact.get("sha256")):
            raise ValueError(f"Evidence changed or missing: {role}")
        paths.append(artifact["path"])
    if len(paths) != len(set(paths)):
        raise ValueError("Baseline, candidate, and review must be distinct artifacts")
    checks = record.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("Document the reviewed checks")
    for item in checks:
        if (not isinstance(item, dict) or item.get("passed") is not True
                or not isinstance(item.get("name"), str) or not item["name"].strip()
                or not isinstance(item.get("evidence"), str) or not item["evidence"].strip()):
            raise ValueError("Every declared check needs a passing result and specific evidence")
    return set(sources)


def check(root, changed):
    needed = {p for p in changed if governed(p)}
    if not needed:
        return []
    covered, diagnostics = set(), []
    for path in sorted((root / "claude/evals").rglob("evidence.json")):
        try:
            local_path(root, path.relative_to(root).as_posix())
            record = json.loads(path.read_text())
            covered.update(validate(root, record))
        except (ValueError, OSError, TypeError) as exc:
            # Historical unsuccessful/stale runs remain on disk; a fresh run can cover them.
            diagnostics.append(f"{path.relative_to(root)}: {exc}")
    return [f"{p}: no current reviewed evidence. " + "; ".join(diagnostics)
            for p in sorted(needed - covered)]


def changed_paths(root, base, head):
    return subprocess.check_output(
        ["git", "-C", str(root), "diff", "--name-only", "--no-renames", "-z", base, head]
    ).decode().rstrip("\0").split("\0")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="PR base or pre-push commit")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    paths = changed_paths(ROOT, args.base, args.head)
    errors = check(ROOT, paths)
    if errors:
        print("\n".join(errors))
        print("See docs/skill-maintenance.md; retain old runs and record fresh evidence.")
    else:
        print("Skill evidence freshness passed (provenance only, not behavioral grading).")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
