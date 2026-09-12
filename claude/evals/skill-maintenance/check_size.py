"""Entrypoint size budgets. UTF-8 bytes / 4 is an estimate, not Claude tokenization."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]


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
    return (path.startswith(("claude/skills/", "gemini/skills/")) and path.endswith("/SKILL.md")
            or path.startswith(("claude/commands/", "claude/agents/")) and path.endswith(".md"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    # Resolve once: an unavailable base must fail, never silently grandfather nothing.
    subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--verify", args.base + "^{commit}"])
    config = json.loads((Path(__file__).with_name("size-budgets.json")).read_text())
    if not isinstance(config, dict):
        raise ValueError("Budget file must map entrypoint paths to reviewed overrides")
    files = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"]).decode().split("\0")
    bad_config = set(config) - {p for p in files if is_entrypoint(p)}
    if bad_config:
        raise ValueError(f"Budget overrides do not name tracked entrypoints: {sorted(bad_config)}")
    failed, count = False, 0
    for name in files:
        path = ROOT / name
        if not is_entrypoint(name) or not path.is_file() or path.is_symlink():
            continue
        old = subprocess.run(["git", "-C", str(ROOT), "show", f"{args.base}:{name}"],
                             capture_output=True)
        result = assess(path.read_bytes().decode("utf-8"),
                        old.stdout.decode("utf-8") if old.returncode == 0 else None, config.get(name, {}))
        count += 1
        if result["failed"] or result["over_budget"]:
            print(f"{'FAIL' if result['failed'] else 'EXISTING'} {name}: "
                  f"{result['lines']} lines, ~{result['estimated_tokens']} tokens; "
                  f"allowed {result['limits']['lines']} / ~{result['limits']['estimated_tokens']}")
        failed |= result["failed"]
    print(f"Checked {count} entrypoints. Token estimates use ceil(UTF-8 bytes / 4), not the Claude tokenizer.")
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
