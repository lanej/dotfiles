#!/usr/bin/env python3
"""
Pull full Looker CI run detail for a GitHub PR and print only what matters: overall
status, and every per-explore test result that isn't passed/skipped, with full error
detail.

Skips straight past the terse GitHub status-check description, which this skill has
found to be unreliable in two distinct ways:
  1. A rollup label can bleed a sibling validator's failure into an unrelated check's
     pass/fail state even when that check's own count is genuinely zero.
  2. The description text itself can just be wrong: a real run showed the GitHub
     check as `LookML Validator: fail` with description "0 LookML validation
     failures" while the actual run detail had error_count: 2, with 2 real,
     actionable errors. Don't trust the count in the GitHub status line either --
     only the full run detail (this script's output) is ground truth.

Usage:
    ci-run-detail.py <pr-number> <looker-project-id> [--repo owner/repo]

Requires: gh CLI (authenticated), looker CLI (~/.looker/config.toml configured --
see this skill's SKILL.md).
"""
import argparse
import json
import re
import subprocess
import sys


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("pr", help="PR number")
    ap.add_argument("looker_project", help="Looker project id, e.g. easypost_engineering")
    ap.add_argument(
        "--repo", default=None, help="owner/repo (default: inferred by gh from cwd)"
    )
    args = ap.parse_args()

    gh_repo_args = ["--repo", args.repo] if args.repo else []

    sha = run(
        ["gh", "pr", "view", args.pr, *gh_repo_args, "--json", "headRefOid", "-q", ".headRefOid"]
    ).strip()
    if not sha:
        print("Could not resolve PR head SHA", file=sys.stderr)
        sys.exit(1)

    repo_slug = args.repo
    if not repo_slug:
        repo_slug = run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]
        ).strip()

    statuses = json.loads(run(["gh", "api", f"repos/{repo_slug}/commits/{sha}/statuses"]))

    run_id = None
    for s in statuses:
        target_url = s.get("target_url") or ""
        m = re.search(r"run_id=([0-9a-f-]{36})", target_url)
        if m:
            run_id = m.group(1)
            break

    if not run_id:
        print(
            "No run_id found in any commit status target_url -- has CI run yet? "
            "(a fresh PR/push can take several minutes before any status appears)",
            file=sys.stderr,
        )
        sys.exit(1)

    detail = json.loads(
        run(["looker", "project", "get-continuous-integration-run", args.looker_project, run_id])
    )

    print(f"Run {run_id} -- overall status: {detail.get('status')}")
    print(f"Looker run URL: {detail.get('run_url')}")
    print()

    result = detail.get("result") or {}
    any_problems = False
    for key in ("sql_result", "content_result", "lookml_result", "assert_result"):
        section = result.get(key)
        if section is None:
            print(f"{key}: null (validator not run or not applicable)")
            continue
        status = section.get("status")
        error_count = section.get("error_count")
        suffix = f" error_count={error_count}" if error_count is not None else ""
        print(f"{key}: status={status}{suffix}")

        for t in section.get("tested") or []:
            if t.get("status") not in ("passed", "skipped"):
                any_problems = True
                print(
                    f"  FAILED: model={t.get('model')} explore={t.get('explore')} "
                    f"errors={t.get('errors')}"
                )

        for e in section.get("errors") or []:
            any_problems = True
            detail_err = e.get("lookml_error") or e.get("generic_error") or e
            print(f"  ERROR: {json.dumps(detail_err, indent=2)}")

    print()
    if not any_problems and detail.get("status") == "passed":
        print("No problems found in the full run detail -- genuinely green, not just a rollup.")
    elif not any_problems:
        print(
            f"No per-item errors found, but overall status is '{detail.get('status')}' -- "
            "inspect the run_url above directly."
        )


if __name__ == "__main__":
    main()
