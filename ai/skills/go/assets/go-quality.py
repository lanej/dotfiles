#!/usr/bin/env python3
"""Combine Go lint policy and enforce a shrinking budget of existing findings."""

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile


POLICY = Path(".go-quality.json")
BASELINE = Path(".go-quality-baseline.json")


def load_config(path):
    if path.suffix == ".json":
        data = json.loads(path.read_text())
    else:
        try:
            import yaml
        except ImportError as error:
            raise ValueError("Go config merging needs PyYAML; install PyYAML or run with uv --with PyYAML==6.0.3") from error
        class UniqueLoader(yaml.SafeLoader):
            def construct_mapping(self, node, deep=False):
                keys = [self.construct_object(k, deep=deep) for k, _ in node.value
                        if k.tag != "tag:yaml.org,2002:merge"]
                if len(set(keys)) != len(keys):
                    raise ValueError(f"{path}: duplicate YAML keys require manual reconciliation")
                return super().construct_mapping(node, deep=deep)
        try:
            data = yaml.load(path.read_text(), Loader=UniqueLoader)
        except yaml.YAMLError as error:
            raise ValueError(f"{path}: invalid YAML: {error}") from error
    if not isinstance(data, dict) or str(data.get("version")) != "2":
        raise ValueError(f"{path}: expected golangci-lint v2; migrate v1 with golangci-lint migrate first")
    return data


def merge(existing, defaults):
    """Union lists and mappings; the added profile owns conflicting scalars."""
    result = copy.deepcopy(existing)
    for key, value in defaults.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        elif isinstance(value, list) and isinstance(result.get(key), list):
            result[key] += [item for item in value if item not in result[key]]
        else:
            result[key] = copy.deepcopy(value)
    return result


def merged_config(existing, defaults):
    result = merge(existing, defaults)
    linters = result["linters"]
    # WHY: The original gate remains intact. Added checks cannot be disabled
    # or restricted to changed lines in the separate strict layer.
    linters["default"] = existing.get("linters", {}).get("default", "standard")
    enabled = set(linters["enable"])
    linters["disable"] = [name for name in linters.get("disable", []) if name not in enabled]
    if "wsl_v5" in enabled:
        linters["enable"] = [name for name in linters["enable"] if name != "wsl"]
        if "wsl" not in linters["disable"]:
            linters["disable"].append("wsl")
    settings = linters.setdefault("settings", {})
    for name in defaults["linters"]["enable"]:
        # WHY: Legacy opt-in/ignore settings must not disable new-file checks.
        settings.pop(name, None)
        if name in defaults["linters"]["settings"]:
            settings[name] = copy.deepcopy(defaults["linters"]["settings"][name])
    for key in ("new", "new-from-rev", "new-from-merge-base", "new-from-patch", "whole-files", "fix"):
        result.get("issues", {}).pop(key, None)
    # Existing exceptions still govern the unchanged legacy gate. The new
    # layer must not inherit broad exemptions for tests or newly added files.
    linters["exclusions"] = defaults["linters"]["exclusions"]
    result["formatters"]["exclusions"] = defaults["formatters"]["exclusions"]
    return result


def policy():
    if not POLICY.exists():
        return {"version": 1, "rollout": "strict", "config": ".golangci.yml", "legacy": None}
    value = json.loads(POLICY.read_text())
    if (not isinstance(value, dict) or value.get("version") != 1
            or value.get("rollout") not in ("strict", "ratchet")
            or value.get("config") not in (".golangci.yml", ".golangci.strict.json")):
        raise ValueError("invalid .go-quality.json")
    legacy = value.get("legacy")
    if legacy is not None and not isinstance(legacy, dict):
        raise ValueError("invalid legacy Go config policy")
    if legacy:
        if legacy.get("path") not in (".golangci.yml", ".golangci.yaml", ".golangci.json"):
            raise ValueError("invalid legacy Go config path")
        if hashlib.sha256(Path(legacy["path"]).read_bytes()).hexdigest() != legacy.get("sha256"):
            raise ValueError("existing lint policy changed; rerun repo-bootstrap --go to refresh the merged layer")
    return value


def key(issue):
    name = issue["Pos"]["Filename"].replace("\\", "/")
    if Path(name).is_absolute():
        name = str(Path(name).resolve().relative_to(Path.cwd().resolve()))
    path = PurePosixPath(name)
    if ".." in path.parts:
        raise ValueError(f"issue outside the project: {name}")
    source = "\n".join(line.strip() for line in issue.get("SourceLines", []))
    message = issue["Text"]
    if issue["FromLinter"] == "govet" and message.startswith("shadow: "):
        message = re.sub(r"(shadows declaration at line )\d+\b", r"\1<line>", message)
    return str(path), issue["FromLinter"], message, source


def read_baseline():
    if BASELINE.is_symlink():
        raise ValueError("refusing linked baseline")
    data = json.loads(BASELINE.read_text())
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("issues"), list):
        raise ValueError("invalid Go quality baseline")
    result = Counter()
    for entry in data["issues"]:
        finding = (entry["path"], entry["linter"], entry["text"], entry["source"])
        if (finding in result or not all(isinstance(s, str) and s for s in finding[:3])
                or not isinstance(finding[3], str)
                or type(entry["count"]) is not int or entry["count"] <= 0
                or Path(finding[0]).is_absolute() or ".." in PurePosixPath(finding[0]).parts):
            raise ValueError("invalid or duplicate baseline finding")
        result[finding] = entry["count"]
    return result


def write_baseline(counts):
    # One finding per line keeps adoption and cleanup diffs reviewable.
    lines = [json.dumps({"path": p, "linter": l, "text": t, "source": s, "count": n}, ensure_ascii=False)
             for (p, l, t, s), n in sorted(counts.items()) if n]
    data = '{\n  "version": 1,\n  "issues": [\n' + ",\n".join("    " + line for line in lines) + '\n  ]\n}\n'
    if BASELINE.is_symlink():
        raise ValueError("refusing to replace linked baseline")
    with tempfile.NamedTemporaryFile(mode="w", dir=".", prefix=".go-quality-", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
    try:
        temporary.replace(BASELINE)
    finally:
        temporary.unlink(missing_ok=True)


def analyze(linter, config):
    with tempfile.TemporaryDirectory(prefix="go-quality-") as temporary:
        report = Path(temporary) / "issues.json"
        result = subprocess.run([linter, "run", "--config", config,
                                 "--fix=false",
                                 "--new=false", "--new-from-rev=", "--new-from-merge-base=", "--new-from-patch=",
                                 "--max-issues-per-linter=0", "--max-same-issues=0", "--uniq-by-line=false",
                                 "--output.json.path", str(report), "--output.text.path", "/dev/null",
                                 "--show-stats=false", "./..."], capture_output=True, text=True)
        if result.returncode not in (0, 1) or not report.is_file():
            raise ValueError(result.stdout + result.stderr or f"lint failed: exit {result.returncode}")
        issues = json.loads(report.read_text()).get("Issues") or []
        if result.returncode and not issues:
            raise ValueError(result.stdout + result.stderr or "lint failed without a diagnostic report")
        if any(issue["FromLinter"] == "typecheck" for issue in issues):
            raise ValueError("Go code must compile before baselining or checking lint:\n" + "\n".join(i["Text"] for i in issues))
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        return issues


def baseline_source_is_committed():
    commands = (["git", "diff", "--name-only", "HEAD", "--", "*.go"],
                ["git", "ls-files", "--others", "--", "*.go"])
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode or result.stdout.strip():
            raise ValueError("baseline adoption requires committed Go source; commit existing source before creating its one-time baseline")


def check(args):
    settings = policy()
    if args.action == "baseline":
        if settings["rollout"] != "ratchet" or BASELINE.exists() or BASELINE.is_symlink():
            raise ValueError("baseline creation requires a new ratchet rollout; existing baselines can only shrink with ratchet")
        baseline_source_is_committed()
    elif settings["rollout"] == "ratchet" and not BASELINE.is_file():
        raise ValueError("initialize existing debt explicitly with bash scripts/check-go.sh baseline before running CI")
    issues = analyze(args.linter, settings["config"])
    counts = Counter(key(issue) for issue in issues)
    if args.action == "baseline":
        write_baseline(counts)
        print(f"Recorded {sum(counts.values())} existing lint findings. New files and new findings are strict.")
        return 0
    allowed = read_baseline() if settings["rollout"] == "ratchet" else Counter()
    new = counts - allowed
    remaining = Counter(new)
    for issue in issues:
        finding = key(issue)
        if remaining[finding]:
            pos = issue["Pos"]
            print(f"{finding[0]}:{pos['Line']}:{pos['Column']}: {issue['Text']} ({finding[1]})")
            remaining[finding] -= 1
    if new:
        print(f"Go quality: {sum(new.values())} new findings; existing debt was not expanded.", file=sys.stderr)
        return 1
    resolved = allowed - counts
    if args.action == "ratchet":
        if settings["rollout"] != "ratchet":
            raise ValueError("ratchet requires a ratchet rollout")
        write_baseline(counts)
        print(f"Removed {sum(resolved.values())} resolved findings from the baseline.")
    elif resolved:
        raise ValueError(f"{sum(resolved.values())} baseline findings were fixed; run bash scripts/check-go.sh ratchet and commit the smaller baseline")
    else:
        print(f"Go quality: no new findings ({sum(allowed.values())} existing findings baselined).")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "baseline", "ratchet", "merge", "policy"))
    parser.add_argument("--linter")
    parser.add_argument("--existing", type=Path)
    parser.add_argument("--profile", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "merge":
            print(json.dumps(merged_config(load_config(args.existing), load_config(args.profile)), indent=2) + "\n")
            return 0
        if args.action == "policy":
            settings = policy()
            print(settings["config"])
            print(settings["rollout"])
            print(settings["legacy"]["path"] if settings.get("legacy") else "")
            return 0
        if not args.linter:
            parser.error("--linter is required")
        return check(args)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Go quality: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
