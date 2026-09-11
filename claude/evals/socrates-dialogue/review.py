#!/usr/bin/env python3
"""Validate a documented human review against immutable paired replay records."""
import argparse
import hashlib
import json
from pathlib import Path

from run import summarize


CHECKS = {"readiness_and_endpoint", "seeded_blockers", "decision_preservation", "executable_spec"}
COUNTS = {"unnecessary_questions", "repeated_questions", "premature_planning"}


def assess(folder, reviews):
    manifest = json.loads((folder / "manifest.json").read_text())
    scenarios = json.loads((folder / "scenarios.json").read_text())
    fixture_hash = hashlib.sha256((folder / "scenarios.json").read_bytes()).hexdigest()
    if manifest["scenarios_sha256"] != fixture_hash:
        raise ValueError("Review must use the exact fixtures used by the replay")
    expected = {f"{arm}-{s['id']}-{trial}" for arm in ("old", "new")
                for s in scenarios for trial in range(1, manifest["trials"] + 1)}
    if set(reviews) != expected:
        raise ValueError("Review must cover every expected arm, scenario, and trial exactly once")
    records = []
    for key in sorted(expected):
        data = (folder / key / "record.json").read_bytes()
        record = json.loads(data)
        review = reviews[key]
        if review.get("record_sha256") != hashlib.sha256(data).hexdigest():
            raise ValueError(f"{key}: review does not match captured record")
        if set(review.get("checks", {})) != CHECKS:
            raise ValueError(f"{key}: all scenario checks are required")
        for check in review["checks"].values():
            if (not isinstance(check, dict) or type(check.get("passed")) is not bool
                    or not isinstance(check.get("evidence"), str) or not check["evidence"].strip()):
                raise ValueError(f"{key}: checks require a Boolean result and evidence")
        if set(review.get("counts", {})) != COUNTS or any(
                type(n) is not int or n < 0 for n in review["counts"].values()):
            raise ValueError(f"{key}: counts must be nonnegative integers")
        if not isinstance(review.get("question_notes"), str) or not review["question_notes"].strip():
            raise ValueError(f"{key}: explain the question assessment, including when none were asked")
        if record.get("ref") != manifest["refs"][record["arm"]]:
            raise ValueError(f"{key}: record commit differs from the manifest")
        record["review"] = review
        records.append(record)
    summary = summarize(records)
    summary["manual_review"] = "complete; see evidence and question notes in reviews.json"
    for arm, totals in summary["arms"].items():
        selected = [r for r in records if r["arm"] == arm]
        totals["scenario_passes"] = sum(
            "error" not in r and not r["mechanical_failures"]
            and all(c["passed"] for c in r["review"]["checks"].values()) for r in selected)
        totals.update({name: sum(r["review"]["counts"][name] for r in selected) for name in COUNTS})
    summary["candidate_passes_all_checks"] = (
        summary["comparison_valid"]
        and summary["arms"]["new"]["scenario_passes"] == len(scenarios) * manifest["trials"])
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--reviews", required=True, type=Path)
    args = parser.parse_args()
    result = assess(args.folder, json.loads(args.reviews.read_text()))
    print(json.dumps(result, indent=2))
    return int(not result["candidate_passes_all_checks"])


if __name__ == "__main__":
    raise SystemExit(main())
