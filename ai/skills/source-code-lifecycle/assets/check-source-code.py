#!/usr/bin/env python3
"""Run the project's versioned lifecycle command plan without a shell."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


def plan(root, language):
    policy = json.loads((root / ".source-code.json").read_text())
    rules = json.loads((root / ".agents/skills/source-code-lifecycle/references/stages.json").read_text())
    if not isinstance(policy, dict) or not isinstance(rules, dict):
        raise ValueError("source-code policy and rules must be objects")
    if type(policy.get("schema_version")) is not int or policy["schema_version"] != 1 or type(rules.get("schema_version")) is not int or rules["schema_version"] != 1:
        raise ValueError("unsupported source-code schema version")
    if policy.get("policy_version") != "1.0.0" or rules.get("policy_version") != policy["policy_version"]:
        raise ValueError("unsupported or mismatched source-code policy version")
    languages = policy.get("languages")
    if not isinstance(languages, list) or not all(name in {"go", "typescript"} for name in languages):
        raise ValueError("invalid installed language list")
    if language not in languages:
        raise ValueError(f"language is not installed: {language}")
    stage = policy.get("stage")
    if stage not in {"research", "alpha", "beta", "production"}:
        raise ValueError(f"unsupported source-code stage: {stage}")
    commands = rules["stages"][stage][language]
    if not isinstance(commands, list) or not commands:
        raise ValueError("empty lifecycle command plan")
    for command in commands:
        if not isinstance(command, list) or not command or not all(isinstance(arg, str) and arg for arg in command):
            raise ValueError("lifecycle commands must be nonempty argv arrays")
    return stage, commands


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("language", choices=("go", "typescript"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        stage, commands = plan(root, args.language)
        print(f"Source-code {args.language}: {stage}", flush=True)
        for command in commands:
            if args.dry_run:
                print(json.dumps(command))
            else:
                subprocess.run(command, cwd=root, check=True)
    except subprocess.CalledProcessError as error:
        return error.returncode if error.returncode > 0 else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Source-code: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
