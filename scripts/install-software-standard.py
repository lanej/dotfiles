#!/usr/bin/env python3
"""Install the shared Builder package and Claude/Codex entrypoints.

Only managed paths are replaced; unrelated guidance is retained.
The installed package contains ordinary files and survives checkout removal.
"""
import argparse
from pathlib import Path
import shutil
import sys
import tempfile


NAME = "builder"
LEGACY_NAME = "pragmatic-hexagonal"
START = f"<!-- {NAME}:start -->"
END = f"<!-- {NAME}:end -->"
GUIDANCE = f"""{START}
# Default software guidance: Builder

For software design, implementation, modification, debugging, and review, read
`~/.local/share/software-standards/builder/references/instructions.md`
and follow the Builder skill, architecture standard, and construction policy it identifies.
{END}
"""
MARKER = "Installed by dotfiles install-software-standard.py\n"


def check_link(path, allowed):
    if path.is_symlink():
        if path.resolve() not in {target.resolve() for target in allowed}:
            raise ValueError(f"preserving unrelated link: {path}")
    elif path.exists():
        raise ValueError(f"preserving local entry: {path}")


def link(target, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() and path.readlink() == target:
        return
    if path.is_symlink():
        path.unlink()
    path.symlink_to(target, target_is_directory=target.is_dir())


def migrate_skills_directory(directory):
    """Replace a prevalidated directory link without changing its source tree."""
    original = directory.readlink()
    entries = list(directory.iterdir()) if directory.exists() else []
    with tempfile.TemporaryDirectory(prefix=".builder-skills-", dir=directory.parent) as temporary:
        staged = Path(temporary) / "skills"
        staged.mkdir()
        for entry in entries:
            # Preserve local/external links as such rather than making them look
            # like owned links that the shared synchronizer is allowed to prune.
            target = entry.resolve() if entry.is_symlink() else directory.resolve() / entry.name
            (staged / entry.name).symlink_to(target, target_is_directory=entry.is_dir())
        directory.unlink()
        try:
            staged.rename(directory)
        except OSError:
            directory.symlink_to(original, target_is_directory=True)
            raise


def managed_guidance(original, path):
    """Replace either managed name in place; reject ambiguous or broken blocks."""
    blocks = []
    for name in (NAME, LEGACY_NAME):
        start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
        if original.count(start) != original.count(end) or original.count(start) > 1:
            raise ValueError(f"malformed standard guidance block: {path}")
        if start in original:
            if original.index(start) > original.index(end):
                raise ValueError(f"malformed standard guidance block: {path}")
            blocks.append((start, end))
    if len(blocks) > 1:
        raise ValueError(f"conflicting standard guidance blocks: {path}")
    if blocks:
        start, end = blocks[0]
        before, rest = original.split(start, 1)
        _, after = rest.split(end, 1)
        return before + GUIDANCE.rstrip("\n") + after
    return GUIDANCE + "\n" + original


def install(source, home):
    source = source.resolve()
    home = home.resolve()
    for relative in ("SKILL.md", "references/standard.md",
                     "references/construction.md", "references/instructions.md"):
        if not (source / relative).is_file():
            raise ValueError(f"missing package resource: {source / relative}. "
                             "Restore the Builder package and rerun make software-standard.")
    package = home / ".local/share/software-standards" / NAME
    marker = package / ".dotfiles-managed"
    if package.is_symlink() or (package.exists() and
                               (not marker.is_file() or marker.read_text() != MARKER)):
        raise ValueError(f"preserving unmanaged package: {package}")
    cache = home / ".codex/dotfiles-skills"
    catalog = home / ".agents/skills/dotfiles"
    check_link(catalog, {cache.resolve()})
    skills_directory = home / ".claude/skills"
    migrate_skills = skills_directory.is_symlink()
    if migrate_skills:
        roots = {source.parent, source.parents[2] / "claude/skills"}
        if skills_directory.resolve() not in {root.resolve() for root in roots}:
            raise ValueError(f"preserving unrelated skill tree: {skills_directory}")
    rules_directory = home / ".claude/rules"
    if rules_directory.is_symlink():
        raise ValueError(f"preserving linked directory; migrate its entries first: {rules_directory}")
    claude_skill = skills_directory / NAME
    codex_skill = cache / NAME
    rule = rules_directory / f"{NAME}.md"
    # A directory-wide link exposes the regular source entry. After migration
    # it will be an individual link, so validate its intended target here.
    if not (migrate_skills and claude_skill.resolve() in {source, package.resolve()}):
        check_link(claude_skill, {source, package})
    check_link(codex_skill, {source, package})
    check_link(rule, {package / "references/instructions.md"})
    global_file = home / ".codex/AGENTS.md"
    if global_file.is_symlink():
        raise ValueError(f"preserving linked global instructions: {global_file}")
    original = global_file.read_text() if global_file.exists() else ""
    guidance = managed_guidance(original, global_file)

    # Migrate only the old installer's package and known dotfiles links.
    # An unrelated local skill/rule under the former name is not ours to remove.
    legacy_package = package.parent / LEGACY_NAME
    legacy_marker = legacy_package / ".dotfiles-managed"
    owned_legacy = (not legacy_package.is_symlink() and legacy_marker.is_file()
                    and legacy_marker.read_text() == MARKER)
    legacy_sources = {source.parent / LEGACY_NAME}
    legacy_rules = set()
    if owned_legacy:
        # A forwarding path preserves aliases without discovering every caller.
        # Refuse the migration before any writes if a legacy resource would
        # disappear or change kind. Runtime caches are not package resources.
        for entry in legacy_package.rglob("*"):
            relative = entry.relative_to(legacy_package)
            if (relative == Path(".dotfiles-managed") or "__pycache__" in relative.parts
                    or entry.suffix == ".pyc"):
                continue
            replacement = source / relative
            if (entry.is_symlink() or not (
                    entry.is_file() and replacement.is_file()
                    or entry.is_dir() and replacement.is_dir())):
                raise ValueError(f"preserving legacy package: cannot redirect {entry} to {replacement}. "
                                 "Review the legacy resource before retrying installation.")
        legacy_sources.add(legacy_package)
        legacy_rules.add(legacy_package / "references/instructions.md")
    obsolete = []
    for path, allowed in (
        (home / ".claude/skills" / LEGACY_NAME, legacy_sources),
        (cache / LEGACY_NAME, legacy_sources),
        (home / ".claude/rules" / f"{LEGACY_NAME}.md", legacy_rules),
    ):
        if path.is_symlink() and path.resolve() in {target.resolve() for target in allowed}:
            obsolete.append(path)
        elif path.exists() or path.is_symlink():
            print(f"software-standard: preserving local legacy entry {path}", file=sys.stderr)

    package.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".builder-install-", dir=package.parent) as temporary:
        temporary = Path(temporary)
        staged = temporary / "package"
        shutil.copytree(source, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (staged / ".dotfiles-managed").write_text(MARKER)
        if migrate_skills:
            migrate_skills_directory(skills_directory)
        backup = temporary / "previous"
        if package.exists():
            package.rename(backup)
        try:
            staged.rename(package)
        except OSError:
            if backup.exists():
                backup.rename(package)
            raise
    cache.mkdir(parents=True, exist_ok=True)
    link(cache, catalog)
    link(package, claude_skill)
    link(package, codex_skill)
    link(package / "references/instructions.md", rule)
    global_file.parent.mkdir(parents=True, exist_ok=True)
    if guidance != original:
        global_file.write_text(guidance)
    for path in obsolete:
        path.unlink()
    if owned_legacy:
        # Keep the old address usable for custom skill and reference aliases,
        # even inside external trees that this installer must not rewrite.
        # The forwarding link follows future Builder updates, not a stale copy.
        with tempfile.TemporaryDirectory(prefix=".builder-legacy-", dir=package.parent) as temporary:
            backup = Path(temporary) / LEGACY_NAME
            legacy_package.rename(backup)
            try:
                legacy_package.symlink_to(package.name, target_is_directory=True)
            except OSError:
                backup.rename(legacy_package)
                raise
    print(f"software-standard: installed Builder package at {package}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] / "ai/skills" / NAME)
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args()
    try:
        install(args.source.expanduser(), args.home.expanduser().absolute())
    except (OSError, ValueError) as error:
        parser.exit(1, f"software-standard: {error}\n")


if __name__ == "__main__":
    main()
