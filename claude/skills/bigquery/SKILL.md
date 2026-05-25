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
