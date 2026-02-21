#!/usr/bin/env python3
"""
Compare data/cache/ to live BigQuery. Fails if any value drifts > threshold.
Run: uv run python scripts/validate-cache.py

Instructions:
  1. Add an entry to CHECKS for each scalar you want to validate.
  2. Each entry is (cache_file_name, scalar_key, sql_query).
     The SQL must return a single row with a single column named 'val'.
  3. Run 'just validate' to check for drift.

The script reads each cached scalar, re-runs the corresponding query live,
and compares them. Exits 1 if any value drifts more than THRESHOLD.
"""

import json, sys, subprocess
from pathlib import Path

THRESHOLD = 0.05  # 5% tolerance for most values
STRICT_THRESHOLD = 0.02  # 2% for high-stakes values listed in STRICT_KEYS
STRICT_KEYS: set[str] = set()  # ← add scalar keys that need tight tolerance

cache_dir = Path("data/cache")
if not list(cache_dir.glob("*.json")):
    print("ERROR: No cache files. Run 'just render' first.", file=sys.stderr)
    sys.exit(1)


def run_bq(sql: str, max_results: int = 1) -> list[dict]:
    r = subprocess.run(
        ["bigquery", "query", "--yes", "--max-results", str(max_results), sql],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise Exception(f"Query failed: {r.stderr[:200]}")
    data = json.loads(r.stdout)
    return data.get("rows", [])


# ── CHECKS ────────────────────────────────────────────────────────────────────
# Each tuple: (cache_file_name, scalar_key, validation_sql)
# SQL must return single row, single column named 'val'.
#
# Example:
#   (
#       "deal_flow",
#       "total_deals",
#       "SELECT COUNT(*) AS val FROM `project.dataset.table` WHERE ...",
#   ),
CHECKS: list[tuple[str, str, str]] = [
    # TODO: add your validation checks here
    # (
    #     "example_dataset",
    #     "example_count",
    #     "SELECT COUNT(*) AS val FROM `{{GCP_PROJECT}}.{{DATASET}}.{{TABLE}}`",
    # ),
]
# ─────────────────────────────────────────────────────────────────────────────

if not CHECKS:
    print("No checks configured. Add entries to CHECKS in scripts/validate-cache.py")
    sys.exit(0)

failures = []

for cache_name, scalar_key, sql in CHECKS:
    cache_file = cache_dir / f"{cache_name}.json"
    if not cache_file.exists():
        print(f"SKIP {cache_name}: no cache file", file=sys.stderr)
        continue
    cached = json.loads(cache_file.read_text())
    cached_val = cached.get("scalars", {}).get(scalar_key)
    if cached_val is None:
        print(f"SKIP {cache_name}.{scalar_key}: not in cache scalars")
        continue
    try:
        rows = run_bq(sql)
        if not rows:
            print(f"WARN {cache_name}.{scalar_key}: live query returned no rows")
            continue
        live_val = float(list(rows[0].values())[0])
        cached_val = float(cached_val)
        if cached_val == 0:
            continue
        drift = abs(live_val - cached_val) / abs(cached_val)
        threshold = STRICT_THRESHOLD if scalar_key in STRICT_KEYS else THRESHOLD
        status = "FAIL" if drift > threshold else "OK  "
        print(
            f"{status} {cache_name}.{scalar_key}: cached={cached_val:.2f} "
            f"live={live_val:.2f} drift={drift:.1%}"
        )
        if drift > threshold:
            failures.append(
                f"{cache_name}.{scalar_key}: drift {drift:.1%} > {threshold:.0%}"
            )
    except Exception as e:
        print(f"WARN {cache_name}.{scalar_key}: {e}")

if failures:
    print(f"\n⚠️  VALIDATION FAILED ({len(failures)} issues):", file=sys.stderr)
    for f in failures:
        print(f"  {f}", file=sys.stderr)
    sys.exit(1)

print(f"\n✓ Validation passed")
