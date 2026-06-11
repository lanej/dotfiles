# DORA Data Pipeline Reference

## Quick-Start Commands

```bash
EPQ_ENV=prod uv run python pipeline.py   # Full incremental refresh (all sources, writes to BQ)
uv run python pipeline.py                # Dry run — fetches data, runs transforms, skips BQ writes
uv run python pipeline.py --force        # Force re-run all stages (ignore freshness cache)
just refresh                             # Alias for EPQ_ENV=prod uv run python pipeline.py
just pipeline-status                     # Show last-run status per stage
just verify-attribution                  # Sanity-check identity; exits 1 on hard failures
```

`just refresh-enterprise` and `just refresh` both call the same `pipeline.py` — there is no separate enterprise pipeline.

## Pipeline Architecture

Single Python-based pipeline: `pipeline.py` (EPQ assembler).

All sources — EasyPost (Phabricator, GitHub, PagerDuty, MySQL) and Enterprise (Azure DevOps, CLS) — are wired into one pipeline object. Each source is a domain module in `domains/`.

**Medallion flow (per domain):**

```
CustomExtract loader fn → DuckDB bronze table
DuckDBTransform (SQL file) → DuckDB silver table
BQExport (SELECT * FROM silver) → DORA_raw.*_raw (prod only, append_mode=True)
```

BQExport stages are skipped when `EPQ_ENV != prod`. Dry runs fetch real API data and run transforms but write nothing to BigQuery.

## Stage Types

**`CustomExtract(name, loader_fn, contract=...)`**
- `loader_fn` is a zero-arg callable returning `pd.DataFrame`
- No TTL by default — always re-runs on every pipeline invocation
- Result stored in DuckDB as the bronze table named `name`

**`DuckDBTransform(name, sql_path, table, contract=...)`**
- `sql_path` points to a file under `sql/`
- SQL uses `{{ ref('stage_name') }}` for table resolution (resolves to the DuckDB table from a prior stage)
- Result stored in DuckDB as `table`

**`BQExport(name, query, bq_table, append_mode=True, depends_on=[...])`**
- `query` is typically `"SELECT * FROM {{ ref('silver_stage_name') }}"`
- `bq_table` is the fully-qualified raw table (e.g. `easypost-platform.DORA_raw.revisions_raw`)
- Skipped entirely when `EPQ_ENV != prod` (no exception, no failure — stage is marked env_skipped)

## Key Utilities (`pipeline_utils.py`)

**`bq_watermark(bq_table, date_col, partition_lookback_days=90, fallback_days=30) → date`**
Queries `MAX(date_col)` from `bq_table` using a partition filter (last `partition_lookback_days` days to avoid full-table scans), then returns the day after as the incremental start date. Falls back to `today - fallback_days` if the table is empty or the query fails. Used at the top of every `_load_*` function.

**`run_subprocess(cmd, retries=3, backoff_base=1.0, error_patterns=[...])`**
Shell command runner with exponential backoff. Retries on non-zero exit or when stderr matches any pattern in `error_patterns` (default: `429`, `rate limit`, `too many requests`). Raises `RuntimeError` after exhausting retries.

**`iter_subprocess(cmd, error_patterns=None) → Iterator[str]`**
Streaming variant — yields non-empty stdout lines as they arrive. Use for JSONL-outputting commands (phab, az) to process records incrementally without buffering the full output.

**`run_gh(args, paginate=False) → list[dict]`**
`gh` CLI wrapper. Checks rate limit before paginated calls; retries on secondary rate limit errors.

**`run_az(args) → list[dict] | None`**
`az` CLI wrapper. Returns `None` on failure (ADO pattern — caller must handle None).

**`run_pd(args) → list[dict]`**
PagerDuty `pd` CLI wrapper.

**`run_jira(path, retries=5) → Any`**
Calls `jira api GET <path>` with exponential backoff on 429. Returns parsed JSON or `None`.

**`records_to_df(records) → pd.DataFrame`**
Converts a list of dicts to a DataFrame. Unwraps BQ-style `{"value": "..."}` dicts that can appear in nested fields.

## Domain Modules (`domains/`)

One Python file per source. Canonical structure:

```python
_SQL = Path(__file__).parent.parent / "sql" / "{source}_silver.sql"
TARGET = "easypost-platform.DORA_raw.{source}_raw"  # or use paths.py constant

def _load_{source}() -> pd.DataFrame:
    since = bq_watermark(TARGET, "date_col")
    # ... fetch from API using run_subprocess / run_gh / run_az / run_pd / run_jira ...
    return records_to_df(records)  # or pd.DataFrame(records)

_bronze_contract = SchemaContract([ExpectNonEmpty(), ExpectNoNulls("pk_col")])

stages = [
    CustomExtract("{source}", _load_{source}, contract=_bronze_contract),
    DuckDBTransform("{source}_silver", _SQL, "{source}_silver",
                    contract=SchemaContract([ExpectNonEmpty(), ExpectNoNulls("pk_col")])),
    BQExport("{source}_upload",
             "SELECT * FROM {{ ref('{source}_silver') }}",
             TARGET, append_mode=True),
]
```

Target table constants live in `paths.py` (e.g. `REVISIONS_RAW`, `BUGS_RAW`). Use them rather than repeating the string.

## Adding a New Domain

1. Create `domains/{source}.py` following the canonical pattern above
2. Create `sql/{source}_silver.sql` with `SELECT ... FROM {{ ref('{source}') }}`
3. Create `tests/test_domain_{source}.py` with `FixturePipeline` tests (see Testing below)
4. Add `from domains import {source}` and `{source}` to the domain loop in `pipeline.py`

## Testing

Use `FixturePipeline` from `epq.pipeline`. Tests populate DuckDB bronze directly (bypassing real API calls), run the silver transform, and assert on contract pass/fail and output shape. No real API credentials needed.

## Empty Incremental Windows

When no new data exists since the watermark, `_load_{source}` returns an empty DataFrame. If `ExpectNonEmpty()` is in the contract, the stage fails its contract check and downstream stages (silver, BQExport) are skipped cleanly. The pipeline exits 0 — empty windows are not a hard failure unless the contract explicitly requires rows.

## Deprecation Note

The legacy bash-based pipeline has been moved to `scripts/deprecated/`:

- `scripts/deprecated/refresh.sh` — former EasyPost pipeline orchestrator
- `scripts/deprecated/refresh-enterprise.sh` — former Enterprise pipeline orchestrator
- `scripts/deprecated/download-*.sh` / `scripts/deprecated/upload-*.sh` — former per-source scripts

**Do not use these.** They are kept for reference only.

Identity and team management scripts remain active in `scripts/` (not deprecated):
- `scripts/download-unified-identity.py` / `just upload-unified-identity`
- `scripts/download-team-registry.py` / `just upload-teams` / `just upload-team-code-aliases`
- `scripts/download-team-membership-changelog.py` / `just upload-team-membership-changelog`

## Upload CLI Taxonomy (Identity/Team Scripts Only)

The EPQ pipeline handles raw table uploads internally. The following CLI patterns apply only to the identity/team scripts that remain outside the pipeline:

| CLI | When to use | Notes |
|-----|-------------|-------|
| `bigquery tables load --write-disposition WRITE_TRUNCATE --temp-bucket <bucket>` | Curated reference tables (full replacement): `unified_identity_history`, `teams`, `team_code_aliases`, `*_team_mapping`, `jira_project_teams`, `pagerduty_users`, `former_employee_teams`, `phab_project_teams`, `team_membership_changelog` | Requires `--temp-bucket` or `BIGQUERY_TEMP_BUCKET` env var; `--yes` is NOT valid on `tables load` |
| `bigquery tables insert --format jsonl --yes` | Manual append-only raw table ingestion (if needed outside the pipeline) | `--yes` required for non-interactive |

## Infrastructure Commands

```bash
just fmt                  # Format HCL
just validate             # Validate OpenTofu config
just plan                 # Preview changes
just build-schemas        # Regenerate *_schema.json from infra/schemas/*.yml
just check-schema-drift   # Verify JSON matches YAML (CI drift check)
just gen-data-dictionary  # Regenerate schema column tables in docs/
```

## Identity / Teams (infrequent)

```bash
just download-unified-identity && just upload-unified-identity
  # upload-unified-identity automatically calls just verify-attribution

just download-team-registry && just upload-teams && just upload-team-code-aliases
just download-team-registry && just upload-incident-team-mapping && just upload-pagerduty-team-mapping
just download-team-membership-changelog && just upload-team-membership-changelog
```

## Troubleshooting

**SSH / Duo MFA exit 255 on deployments**: Transient Duo rejection from simultaneous connections. Re-run — the `deployments` domain is idempotent via watermark.

**BQExport stage skipped (env_skipped)**: Running without `EPQ_ENV=prod`. Set `EPQ_ENV=prod` to enable BQ writes.

**Stage contract failure (`ExpectNonEmpty`)**: Incremental window returned no rows. Normal for sources with no recent activity. If unexpected, check the watermark date — `bq_watermark` may have returned an unusually recent date, narrowing the window to zero.

**BigQuery load failures on identity scripts**: Check schema mismatches. Run `just check-schema-drift` — JSON schema may have drifted from YAML source if `build-schemas` was skipped.

**`bq_watermark` partition filter returning wrong date**: The watermark uses a `partition_lookback_days=90` filter. If the table has no recent partitions but does have older data, watermark falls back to `today - fallback_days`. Check the pipeline log for `watermark ... fallback to` messages.
