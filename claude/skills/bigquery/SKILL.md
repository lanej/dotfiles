---
name: bigquery
description: Use bigquery CLI (instead of `bq`) for all Google BigQuery and GCP data warehouse operations including SQL query execution, data ingestion (streaming insert, bulk load, JSONL/CSV/Parquet), data extraction/export, dataset/table management, cost estimation with dry-run, authentication with gcloud, data pipelines, ETL workflows, and MCP server integration for AI-assisted querying. Modern TypeScript/Bun implementation replacing the Python `bq` CLI with instant startup (~10ms vs ~500ms), automatic cost awareness with confirmation prompts, and native streaming support (JSONL). Handles both small-scale streaming inserts (<1000 rows) and large-scale bulk loading (>10MB files) from Cloud Storage.
---
# BigQuery CLI & MCP Server

## CLI vs MCP

**The CLI is the full interface. MCP tools are a subset.**

Default to the `bigquery` CLI for any operation not listed in the MCP tools section below. Use MCP when an agent needs structured tool call semantics.

## Authentication

Uses Google Cloud SDK (`gcloud`) ADC — no separate BigQuery auth required.

```bash
bigquery auth check   # verify status and scopes
```

## Output Format Defaults

| Command | Default | Notes |
|---------|---------|-------|
| `query` | JSON | includes metadata (bytes, cost, cacheHit) |
| `datasets list` | text | human-readable |
| `tables list` | text | human-readable |

All commands accept `--format json|text|jsonl`.

## Query Operations

```bash
# Basic (automatic dry-run + cost confirmation)
bigquery query "SELECT * FROM dataset.table LIMIT 10"

# Skip cost confirmation (required for automation)
bigquery query --yes "SELECT COUNT(*) FROM dataset.table"

# JSONL output (one object per line — for pipelines/DuckDB)
bigquery query --jsonl "SELECT * FROM dataset.table"

# Stream large results
bigquery query "SELECT * FROM large_table" --stream > results.jsonl

# From file / stdin
bigquery query --file query.sql
cat query.sql | bigquery query --stdin --yes

# Dry run (cost estimate, $0 to run)
bigquery dry-run "SELECT * FROM large_table WHERE date >= '2025-01-01'"
```

**Cost Awareness**: auto dry-run before every query; prompts if cost > threshold (default: 1 GB); response includes `bytesProcessed`, `estimatedCostUSD`, `cacheHit`.

Key flags: `--yes`, `--format`, `--jsonl`, `--stream`, `--cost-threshold`, `--max-results`, `--project`

**Important**: `--max-results` limits returned rows, NOT bytes scanned (no cost reduction). Use `LIMIT` in SQL instead.

## Dataset Operations

```bash
bigquery datasets list [--project PROJECT]
bigquery datasets describe PROJECT.DATASET
bigquery datasets create PROJECT.DATASET [--description "..." --location US --default-ttl 30]
bigquery datasets update PROJECT.DATASET --description "..."
bigquery datasets delete PROJECT.DATASET [--force --yes]
```

## Table Operations

```bash
# Read
bigquery tables list PROJECT.DATASET [--max-results 20]
bigquery tables describe PROJECT.DATASET.TABLE

# Write
bigquery tables create TABLE --schema '[{"name":"id","type":"STRING"}]'
bigquery tables update TABLE --description "..."

# Insert (streaming, <1000 rows)
bigquery tables insert TABLE file.jsonl --format jsonl
cat data.jsonl | bigquery tables insert TABLE - --format jsonl

# Load (bulk, >10MB — from Cloud Storage)
bigquery tables load TABLE gs://bucket/data.csv --format csv --write-disposition WRITE_TRUNCATE

# Copy / extract / delete
bigquery tables copy SOURCE DEST [--write-disposition WRITE_TRUNCATE]
bigquery tables extract TABLE gs://bucket/output.csv --format csv
bigquery tables delete TABLE
```

**`tables load` gotcha**: does NOT accept `--yes`; `--write-disposition` requires uppercase (`WRITE_APPEND`, not `append`).

## Job Management

```bash
bigquery jobs list [--state-filter running|done --all-users]
bigquery jobs get JOB_ID
bigquery jobs cancel JOB_ID
```

## Python Subprocess Patterns

```python
# query via stdin
result = subprocess.run(
    ["bigquery", "query", "--format", "jsonl", "--yes", "--stdin"],
    input=sql, capture_output=True, text=True, check=True
)

# bulk load (no --yes for tables load)
subprocess.run(
    ["bigquery", "tables", "load", "--format", "json",
     "--write-disposition", "WRITE_APPEND", table, tmpfile],
    check=True
)
```

## MCP Server

### Starting

```bash
bigquery mcp stdio                 # read-only (default)
bigquery mcp stdio --enable-writes # with write tools
bigquery mcp http --port 3000      # HTTP mode
```

### MCP Tools (read-only by default)

In Claude Code the full identifiers are `mcp__bigquery__*`.

**Read tools** (always available):

| Tool | Description |
|------|-------------|
| `query` | Execute SQL with auto dry-run and cost guard |
| `dry_run` | Estimate cost without executing ($0) |
| `list_datasets` | List datasets; returns `bigquery://project.dataset` URIs |
| `list_tables` | List tables; returns `bigquery://project.dataset.table` URIs |
| `describe_table` | Full schema, row count, metadata |

**Write tools** (require `--enable-writes`):

| Tool | Description |
|------|-------------|
| `create_dataset` | Create a new dataset |
| `create_table` | Create table with schema, partitioning, clustering |
| `insert_rows` | Streaming insert (<1000 rows) |
| `load_data` | Load from GCS URI (bulk) |
| `execute_ddl` | Run DDL/DML (CREATE, INSERT, UPDATE, etc.) |

### MCP Resources

Tables are exposed as resources via `bigquery://{project.dataset.table}`. Fetching a resource returns the same output as `describe_table` — schema, row count, metadata — without consuming a tool call slot.

```
bigquery://easypost-platform.DORA.ai_attribution
```

### Workflow (MCP)

1. `list_datasets` → discover datasets (returns URI list)
2. `list_tables` → explore tables (returns URI list)
3. Read resource `bigquery://project.dataset.table` → get schema
4. `dry_run` → estimate cost
5. `query` → execute

### MCP Config

```json
{
  "mcpServers": {
    "bigquery": {
      "command": "bigquery",
      "args": ["mcp", "stdio"]
    }
  }
}
```

## Append-Only Raw Table Pattern

- `table_raw` — append-only write target; never UPDATE/DELETE in-place
- `table` (VIEW) — read surface; deduplicates via `ROW_NUMBER() OVER (PARTITION BY <key> ORDER BY loaded_at DESC) = 1`
- Always include `loaded_at TIMESTAMP REQUIRED`; set to `CURRENT_TIMESTAMP()` at write time
- To "update" a record: INSERT a new row with corrected values and fresh `loaded_at`
- Never target a VIEW for DML — always write to the raw table

## Writing Data — Insert and Load Patterns

### A: `tables load` silently ignores local file paths

`bigquery tables load` requires a Cloud Storage URI (`gs://...`). Passing a local path returns exit code 0 and prints nothing — the table is not written and downstream reads return 0 rows. **Use `tables insert` for local files.**

### B: Streaming insert command

```bash
bigquery tables insert --format jsonl --yes <project.dataset.table> <local-file.jsonl>
```

`bigquery insert` (without `tables`) does not exist — returns "unknown command". File must be JSONL. `--yes` skips the cost confirmation prompt.

### C: New table propagation delay

After `bigquery tables create`, metadata takes up to ~50 seconds to propagate. Calling `tables insert` immediately returns a "Not found: Table" error. Wrap the insert in a retry loop:

```python
for attempt in range(10):
    result = subprocess.run([...tables insert...], capture_output=True, text=True)
    if result.returncode == 0:
        break
    if "Not found" in result.stderr:
        time.sleep(5)
        continue
    raise RuntimeError(result.stderr)
else:
    raise RuntimeError("table not available after 50s")
```

### D: Streaming buffer blocks DELETE/TRUNCATE for ~90 minutes

After a streaming insert, `DELETE FROM table WHERE TRUE` and `TRUNCATE TABLE` fail:
> `UPDATE or DELETE statement over table would affect rows in the streaming buffer, which is not supported`

This window lasts up to 90 minutes. For WRITE_TRUNCATE semantics (replace all rows on each run), drop and recreate:

```python
subprocess.run(["bigquery", "tables", "delete", table], capture_output=True)
_ensure_table(table)  # recreate with schema
# propagation delay applies after recreate — use retry loop from (C)
```

## Schema Verification Protocol

Run `describe_table` before writing any query against a table not already described in the current session. No exceptions for "familiar" tables — schemas diverge silently between tables assumed to share a shape. This applies equally during **spec and planning phases**: if a spec references a specific column name, run `describe_table` before writing the spec line, not at implementation time. Deferring embeds false assumptions into written requirements. Failure mode: spec assumed `CONVERSATION_START` on `gong_landing.CALL_TRANSCRIPTS`; column didn't exist; discovered at implementation.

When a query fails with a column-not-found error, use `describe_table` immediately — do not guess alternate names.

**Join propagation**: a column on a base table does not automatically propagate through a JOIN. A field may exist on the raw table but be absent from a view that joins it, or return NULL when accessed through a LEFT JOIN. Verify by running a sample query with the actual join before building on it. Failure mode: `unified_identity.team_display_name` exists on the base table but returns NULL through `task_event_durations LEFT JOIN unified_identity` because the column is computed in a view layer that doesn't expose it through that join path.

## Known Gotchas

**DATE columns in JSONL output** return `{"value": "YYYY-MM-DD"}` dicts, not strings. TIMESTAMP columns return epoch float strings (`"1.760730316667E9"`), not ISO strings.

```python
def _parse_date(v) -> str:
    if isinstance(v, dict): return str(v["value"])[:10]
    return str(v)[:10]

def _parse_ts(v) -> datetime:
    try: return datetime.fromisoformat(str(v))
    except ValueError: return datetime.fromtimestamp(float(v), tz=timezone.utc)
```

**Numeric columns arrive as strings.** Cast before aggregation:
```python
df["col"] = pd.to_numeric(df["col"], errors="coerce").fillna(0).astype("int64")
```

**`carrier_accounts` join fan-out**: `ep-core-data.raw.carrier_accounts` has ~77K duplicate IDs. Always deduplicate with `SELECT DISTINCT id, ...` before joining. Validate: COUNT(*) after join ≈ COUNT(*) before join.

**CTE/column alias collision**: BQ resolves `ORDER BY col` to the CTE (a STRUCT) if a CTE and column alias share the same name → "Ordering by expressions of type STRUCT is not allowed." Rename the column alias.

**Pre-resolve dimension lookups**: `shipments` (4.2TB) is not clustered by `user_id`. Joining to `dim.users` to filter by SF account scans the full date partition (77GB+). Instead: resolve dim IDs in a cheap query first, then use IN clause on the fact table — no join needed.

**Salesforce `created_date`** is the Polytomic sync timestamp (Feb 2025+), not the SF creation date. Use `close_date` or SF-native date fields for historical queries.

**`salesforce.tasks.created_date`** is INT64 nanoseconds — convert with `TIMESTAMP_MILLIS(CAST(created_date / 1000000 AS INT64))`.

**UNNEST literal size limit**: When building a SQL query that passes a large set of keys via `UNNEST([key1, key2, ...])` as a literal array in the SQL string (e.g., 50k+ values), the `bigquery` CLI subprocess fails with a JSON parse error like "Expecting ',' delimiter: line 1 column 1517". The SQL itself may be syntactically valid but the CLI hits an input/output limit.

Fix: Don't embed large key sets in SQL literals. Instead, fetch all rows from the target table (with a REGEXP_CONTAINS or similar pre-filter if possible) and do key matching client-side in Python. This is the same approach used in `extract_phab.py`'s `_build_revision_lookup` — fetch all revisions, parse ticket refs in Python, intersect with the target key set.

**View-layer JOIN cost**: When proposing to move computation from application code (Python, Go, etc.) to a BQ view, note the per-query cost implications of any JOINs that will execute on every view read. Example: moving cycle time computation from Python to a BQ view added a ~29k row DORA join that runs on every `classified_tickets` query. The cost is acceptable when immediate effect (no re-processing required) outweighs per-query efficiency, but surface it as a trade-off: "This adds a [N]-row JOIN on every query. Acceptable for [reason], but increases query cost by [estimate]."

**Reserved word aliases**: `ROWS`, `DATE`, `TIME`, `TIMESTAMP`, `VALUE`, `TYPE`, `SCHEMA`, `STATUS`, `NAME` are BigQuery reserved words and cannot be used as column aliases. Using them causes a runtime syntax error ("Unexpected keyword ROWS at ..."). Use neutral aliases: `cnt`, `row_cnt`, `ts`, `val`, `tbl_type`, etc.

**`_PARTITIONTIME` pseudo-column**: Only available on tables partitioned by ingestion time (no explicit partition column — the default DAY or HOUR partition). Tables with an explicit partition column (e.g., `call_date DATE`, `submitted_at TIMESTAMP`) do NOT expose `_PARTITIONTIME` — use the actual column directly (e.g., `WHERE call_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)`).

**`TIMESTAMP_SUB` does not support MONTH/YEAR**: `TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 12 MONTH)` raises a runtime error — MONTH and YEAR date parts are only valid for DATE arithmetic, not TIMESTAMP. For rolling lookback windows on TIMESTAMP columns, use DAY units: `TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY)`. Alternatively, cast to DATE first: `DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)` then compare against `DATE(timestamp_col)` (but note this defeats partition pruning on the raw TIMESTAMP column — prefer the DAY approach).

## Quick Reference

```bash
bigquery auth check
bigquery query --yes "SELECT ..."
bigquery dry-run "SELECT ..."
bigquery datasets list
bigquery tables list PROJECT.DATASET
bigquery tables describe TABLE
bigquery tables insert TABLE file.jsonl --format jsonl
bigquery tables load TABLE gs://bucket/file.csv --write-disposition WRITE_TRUNCATE
bigquery mcp stdio
```
