#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["anthropic[vertex]>=0.40"]
# ///
"""Evaluate pick-model heuristic accuracy against labeled test cases.

Mirrors the real Claude Code execution context: loads the ## Model Selection
section from claude/CLAUDE.md plus the body of pick-model.md (frontmatter
stripped) as the system prompt, then sends each task as a user message.

Runs against Claude on Vertex AI, authenticated with the active gcloud access
token (gcloud auth print-access-token) — no ANTHROPIC_API_KEY needed.

Usage:    uv run claude/eval/pick-model-eval.py
Requires: an active gcloud session with Vertex AI access.
Env:      VERTEX_PROJECT (default easypost-platform),
          VERTEX_REGION  (default us-east5),
          EVAL_MODEL     (default claude-sonnet-4-6).
"""
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from anthropic import AnthropicVertex

REPO = Path(__file__).parent.parent
CLAUDE_MD = REPO / "CLAUDE.md"
PICK_MODEL_MD = REPO / "commands" / "pick-model.md"

PASS_THRESHOLD = 0.90
PROJECT = os.environ.get("VERTEX_PROJECT", "easypost-platform")
REGION = os.environ.get("VERTEX_REGION", "us-east5")
EVAL_MODEL = os.environ.get("EVAL_MODEL", "claude-sonnet-4-6")


def gcloud_access_token() -> str:
    return subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True
    ).strip()


def extract_model_selection_section(text: str) -> str:
    m = re.search(r"(## Model Selection\n.*?)(?=\n## |\Z)", text, re.DOTALL)
    if not m:
        raise ValueError("## Model Selection section not found in CLAUDE.md")
    return m.group(1).strip()


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.index("---", 3)
        return text[end + 3:].lstrip()
    return text


def build_system_prompt() -> str:
    model_section = extract_model_selection_section(CLAUDE_MD.read_text())
    command_body = strip_frontmatter(PICK_MODEL_MD.read_text())
    return f"{model_section}\n\n---\n\n{command_body}"


# Labels: str = single expected model; list[str] = any of these is correct (boundary case)
CASES: list[tuple[str, str | list[str]]] = [
    # --- Haiku ---
    ("What is the syntax for a Go map literal?",                                                   "Haiku 4.5"),
    ("Extract the 'name' field from this JSON response",                                           "Haiku 4.5"),
    ("What does HTTP 429 mean?",                                                                   "Haiku 4.5"),
    ("List the flags accepted by git rebase",                                                      "Haiku 4.5"),
    ("Convert this ISO timestamp to Unix epoch",                                                   "Haiku 4.5"),
    # --- Sonnet ---
    ("Add a --dry-run flag to the deploy script",                                                  "Sonnet 4.6"),
    ("Write a commit message for these staged changes",                                            "Sonnet 4.6"),
    ("Convert this CSV parser from Python 2 to Python 3 syntax",                                  "Sonnet 4.6"),
    ("Add docstrings to these Go functions",                                                       "Sonnet 4.6"),
    ("Fix the off-by-one error in this pagination loop",                                           "Sonnet 4.6"),
    ("Rename UserRecord to UserProfile across this file",                                          "Sonnet 4.6"),
    ("Write a Makefile target that runs go test ./... with -race",                                 "Sonnet 4.6"),
    # --- Opus ---
    ("Redesign auth to support multi-tenant JWT with per-org key rotation",                        "Opus 4.8"),
    ("Debug why the distributed cache becomes inconsistent under concurrent writes",               "Opus 4.8"),
    ("Identify service boundaries for splitting this monolith across 12 business domains",        "Opus 4.8"),
    ("Design the data model for a multi-currency billing system with proration",                   "Opus 4.8"),
    ("Audit the payment processing flow end-to-end for security vulnerabilities",                  "Opus 4.8"),
    ("Refactor the query planner to handle correlated subqueries without N+1 scans",              "Opus 4.8"),
    # --- Boundary cases (either answer acceptable) ---
    ("Add integration tests for the checkout flow across cart, payment, and fulfillment services", ["Sonnet 4.6", "Opus 4.8"]),
    ("Fix a nil pointer dereference in the request handler",                                       ["Haiku 4.5", "Sonnet 4.6"]),
]


def evaluate(
    client: AnthropicVertex,
    system: str,
    task: str,
    expected: str | list[str],
) -> tuple[str, bool, bool]:
    """Returns (got, passed, parse_error)."""
    try:
        resp = client.messages.create(
            model=EVAL_MODEL,
            max_tokens=256,
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": task}],
        )
    except Exception as e:
        return f"API_ERROR:{e}", False, True

    text = next(
        (block.text for block in resp.content if hasattr(block, "text")), ""
    )
    m = re.search(r"^Model:\s+(.+)$", text, re.MULTILINE)
    if not m:
        return "PARSE_ERROR", False, True

    got = m.group(1).strip()
    expected_list = [expected] if isinstance(expected, str) else expected
    passed = got in expected_list
    return got, passed, False


if __name__ == "__main__":
    system = build_system_prompt()
    client = AnthropicVertex(
        project_id=PROJECT, region=REGION, access_token=gcloud_access_token()
    )

    results = []
    per_class: dict[str, list[bool]] = defaultdict(list)
    parse_errors = 0

    for task, expected in CASES:
        got, passed, is_parse_error = evaluate(client, system, task, expected)
        if is_parse_error:
            parse_errors += 1
            status = "ERR "
        else:
            status = "PASS" if passed else "FAIL"
        results.append(passed)
        expected_label = expected if isinstance(expected, str) else "/".join(expected)
        primary_class = expected if isinstance(expected, str) else expected[0]
        per_class[primary_class].append(passed)
        print(f"{status}  expected={expected_label:<22} got={got:<12}  {task[:60]}")

    total = len(CASES)
    n_passed = sum(results)
    pct = n_passed / total

    print(f"\nPer-class recall:")
    for cls in ["Haiku 4.5", "Sonnet 4.6", "Opus 4.8"]:
        cls_results = per_class.get(cls, [])
        if cls_results:
            print(f"  {cls:<12} {sum(cls_results)}/{len(cls_results)}")

    print(f"\n{n_passed}/{total} ({pct:.0%})  parse_errors={parse_errors}")
    sys.exit(0 if pct >= PASS_THRESHOLD else 1)
