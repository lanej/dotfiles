#!/usr/bin/env python3
"""Install the shared architecture package and Claude/Codex entrypoints.

Only this standard's managed paths are replaced; unrelated guidance is retained.
The installed package contains ordinary files and survives checkout removal.
"""
import argparse
from pathlib import Path
import shutil
import sys
import tempfile


NAME = "pragmatic-hexagonal"
START = "<!-- pragmatic-hexagonal:start -->"
END = "<!-- pragmatic-hexagonal:end -->"
GUIDANCE = f"""{START}
# Default software standard

For software design, implementation, modification, debugging, and review, read
`~/.local/share/software-standards/pragmatic-hexagonal/references/instructions.md`
and follow the shared skill and standard it identifies.
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


def install(source, home):
    source = source.resolve()
    home = home.resolve()
    for relative in ("SKILL.md", "references/standard.md", "references/instructions.md"):
        if not (source / relative).is_file():
            raise ValueError(f"missing package resource: {source / relative}")
    package = home / ".local/share/software-standards" / NAME
    marker = package / ".dotfiles-managed"
    if package.is_symlink() or (package.exists() and
                               (not marker.is_file() or marker.read_text() != MARKER)):
        raise ValueError(f"preserving unmanaged package: {package}")
    cache = home / ".codex/dotfiles-skills"
    catalog = home / ".agents/skills/dotfiles"
    check_link(catalog, {cache.resolve()})
    for directory in (home / ".claude/skills", home / ".claude/rules"):
        if directory.is_symlink():
            raise ValueError(f"preserving linked directory; migrate its entries first: {directory}")
    claude_skill = home / ".claude/skills" / NAME
    codex_skill = cache / NAME
    rule = home / ".claude/rules" / f"{NAME}.md"
    check_link(claude_skill, {source, package})
    check_link(codex_skill, {source, package})
    check_link(rule, {package / "references/instructions.md"})
    global_file = home / ".codex/AGENTS.md"
    if global_file.is_symlink():
        raise ValueError(f"preserving linked global instructions: {global_file}")
    original = global_file.read_text() if global_file.exists() else ""
    if original.count(START) != original.count(END) or original.count(START) > 1:
        raise ValueError(f"malformed standard guidance block: {global_file}")
    if START in original:
        before, rest = original.split(START, 1)
        _, after = rest.split(END, 1)
        guidance = before + GUIDANCE.rstrip("\n") + after
    else:
        guidance = GUIDANCE + "\n" + original

    package.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pha-install-", dir=package.parent) as temporary:
        temporary = Path(temporary)
        staged = temporary / "package"
        shutil.copytree(source, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (staged / ".dotfiles-managed").write_text(MARKER)
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
    print(f"software-standard: installed shared package at {package}")


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
