"""Entrypoint size budgets. UTF-8 bytes / 4 is an estimate, not Claude tokenization."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
# Instruction destinations linked by Makefile, relative to the install home.
INSTALLED_ROOTS = ("claude/CLAUDE.md", "claude/CONSTITUTION.md", "claude/commands",
                   "claude/agents", "claude/skills", "gemini/skills")


def metrics(text):
    return {"lines": len(text.splitlines()), "estimated_tokens": (len(text.encode("utf-8")) + 3) // 4}


def assess(text, previous, override):
    if not isinstance(override, dict):
        raise ValueError("A budget override must be an object")
    if override and (not isinstance(override.get("reason"), str) or not override["reason"].strip()):
        raise ValueError("A per-file budget needs a reviewable reason")
    if set(override) - {"max_lines", "max_estimated_tokens", "reason"}:
        raise ValueError("Unknown budget field")
    budget = {"lines": override.get("max_lines", 500),
              "estimated_tokens": override.get("max_estimated_tokens", 4000)}
    if any(type(n) is not int or n <= 0 for n in budget.values()):
        raise ValueError("Budgets must be positive integers")
    current = metrics(text)
    old = metrics(previous) if previous is not None else {k: 0 for k in budget}
    limits = {k: max(budget[k], old[k]) for k in budget}
    return {**current, "limits": limits,
            "failed": any(current[k] > limits[k] for k in budget),
            "over_budget": any(current[k] > budget[k] for k in budget)}


def is_entrypoint(path):
    return (Path(path).name in {"SKILL.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md"}
            or path == "claude/CONSTITUTION.md"
            or path.startswith(("claude/commands/", "claude/agents/")) and path.endswith(".md"))


def installed_entrypoints(home):
    def walk(path, name, ancestors=()):
        if path.is_dir():
            resolved = path.resolve()
            if resolved in ancestors:
                return
            for child in sorted(path.iterdir()):
                yield from walk(child, name + "/" + child.name, ancestors + (resolved,))
        elif is_entrypoint(name):
            yield name, path

    for name in INSTALLED_ROOTS:
        path = home / ("." + name)
        if path.is_symlink() and not path.exists():
            yield name, path  # Report a broken install rather than silently skipping it.
        elif path.exists():
            yield from walk(path, name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--installed-home", type=Path,
                        help="also check the Claude/Gemini instruction destinations in this home")
    args = parser.parse_args()
    # Resolve once: an unavailable base must fail, never silently grandfather nothing.
    base = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--verify",
                                    args.base + "^{commit}"]).decode().strip()
    tree = subprocess.check_output(["git", "-C", str(ROOT), "ls-tree", "-r", "-z", base])
    # A Git symlink blob contains a path, not the previous instruction text.
    base_files = {entry.split(b"\t", 1)[1].decode() for entry in tree.split(b"\0")
                  if entry.startswith(b"100")}
    config = json.loads((Path(__file__).with_name("size-budgets.json")).read_text())
    if not isinstance(config, dict):
        raise ValueError("Budget file must map entrypoint paths to reviewed overrides")
    files = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"]).decode().split("\0")
    bad_config = set(config) - {p for p in files if is_entrypoint(p)}
    if bad_config:
        raise ValueError(f"Budget overrides do not name tracked entrypoints: {sorted(bad_config)}")
    scans = {"source": [(name, ROOT / name) for name in files if is_entrypoint(name)
                         and (ROOT / name).is_file() and not (ROOT / name).is_symlink()]}
    if args.installed_home is not None:
        scans["installed"] = installed_entrypoints(args.installed_home.expanduser())
    failed = False
    for scope, entries in scans.items():
        count = 0
        for name, path in entries:
            label = name if scope == "source" else f"installed {path}"
            previous = (subprocess.check_output(["git", "-C", str(ROOT), "show", f"{base}:{name}"])
                        .decode("utf-8") if name in base_files else None)
            count += 1
            try:
                text = path.read_bytes().decode("utf-8")
            except (OSError, UnicodeError) as error:
                print(f"FAIL {label}: {error}")
                failed = True
                continue
            result = assess(text, previous, config.get(name, {}))
            if result["failed"] or result["over_budget"]:
                print(f"{'FAIL' if result['failed'] else 'EXISTING'} {label}: "
                      f"{result['lines']} lines, ~{result['estimated_tokens']} tokens; "
                      f"allowed {result['limits']['lines']} / ~{result['limits']['estimated_tokens']}")
            failed |= result["failed"]
        print(f"Checked {count} {scope} entrypoints.")
    print("Token estimates use ceil(UTF-8 bytes / 4), not the Claude tokenizer.")
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
