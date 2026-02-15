---
name: bigquery
description: Use bigquery CLI (instead of `bq`) for all Google BigQuery and GCP data warehouse operations including SQL query execution, data ingestion (streaming insert, bulk load, JSONL/CSV/Parquet), data extraction/export, dataset/table management, cost estimation with dry-run, authentication with gcloud, data pipelines, ETL workflows, and MCP server integration for AI-assisted querying. Modern TypeScript/Bun implementation replacing the Python `bq` CLI with instant startup (~10ms vs ~500ms), automatic cost awareness with confirmation prompts, and native streaming support (JSONL). Handles both small-scale streaming inserts (<1000 rows) and large-scale bulk loading (>10MB files) from Cloud Storage.
---
# BigQuery CLI Skill

You are a BigQuery specialist using the `bigquery` CLI tool. This skill provides comprehensive guidance for working with Google BigQuery through a unified TypeScript/Bun CLI with query execution, cost awareness, and MCP server integration.

## Core Capabilities

The `bigquery` CLI provides:

1. **Authentication**: Check status and gcloud integration
2. **Query Execution**: Run SQL queries with automatic cost estimation and confirmation prompts
3. **Dry Run**: Estimate query costs ($0 to run)
4. **Dataset Operations**: List, create, update, delete, describe datasets
5. **Table Operations**: List, describe, insert, load, extract, create, update, delete, copy tables
6. **Job Management**: List, get, and cancel BigQuery jobs
7. **MCP Server**: Built-in stdio and HTTP modes for AI integration (read-only by default, `--enable-writes` flag)
8. **Streaming Support**: Native `--stream` flag for large result sets (outputs JSONL)
9. **Output Formats**: JSON (default), JSONL (streaming), and text (human-readable)

## Authentication

### Check Authentication Status

```bash
# Check if authenticated and verify required scopes
bigquery auth check

# Output shows:
# - Authentication status
# - Active account
# - Token expiration
# - BigQuery scopes availability
```

### Authentication Methods

Uses Google Cloud SDK (`gcloud`) authentication:
1. Application Default Credentials (ADC)
2. OAuth access tokens
3. Service account keys (via `GOOGLE_APPLICATION_CREDENTIALS`)

**No separate BigQuery authentication required** - uses existing gcloud credentials.

**Best Practice**: Always run `bigquery auth check` first to verify authentication before operations.

## Output Format Defaults

Different commands have different default output formats:

| Command | Default Format | Notes |
|---------|----------------|-------|
| `query` | **JSON** | Machine-readable for pipelines, includes metadata |
| `datasets list` | text | Human-readable |
| `tables list` | text | Human-readable |
| `tables describe` | text | Human-readable |
| `jobs list` | text | Human-readable |

All commands support `--format json` or `--format text` to override defaults.

**Available Formats:**
- **JSON**: Structured output with metadata (rows, bytesProcessed, cost, cacheHit)
- **Text**: Human-readable formatted output
- **JSONL**: Newline-delimited JSON (one object per line), ideal for streaming and pipelines

## Query Operations

### Running Queries

```bash
# Basic query execution (automatic dry-run + cost confirmation)
bigquery query "SELECT * FROM dataset.table LIMIT 10"

# Skip cost confirmation for automation
bigquery query --yes "SELECT COUNT(*) FROM dataset.table"

# JSON output (default, includes full metadata)
bigquery query "SELECT * FROM dataset.table LIMIT 5"

# JSONL output (one JSON object per line, ideal for pipelines)
bigquery query "SELECT * FROM dataset.table" --jsonl

# Stream large results (implies JSONL format)
bigquery query "SELECT * FROM large_table" --stream > results.jsonl

# Text format (human-readable)
bigquery query --format text "SELECT * FROM dataset.table LIMIT 5"

# Query from file
bigquery query --file query.sql

# Query from stdin
cat query.sql | bigquery query --stdin --yes

# Custom project
bigquery query --project my-other-project "SELECT 1"
```

**Cost Awareness**: The query command automatically:
1. Runs a dry-run to estimate cost before execution (costs $0)
2. Displays bytes to be processed and estimated cost
3. Prompts for confirmation if cost exceeds threshold (default: 1 GB)
4. Skips confirmation for queries below threshold or when `--yes` is used
5. Includes cost metadata in response (bytesProcessed, estimatedCostUSD, cacheHit)

### Query Options

```bash
# Skip cost confirmation (REQUIRED for automation/scripts)
bigquery query --yes "SELECT * FROM dataset.table"

# Set custom cost threshold (default: 1 GB)
bigquery query --cost-threshold 5 "SELECT * FROM large_table"

# Environment variable for persistent threshold
export BIGQUERY_COST_THRESHOLD_GB=5.0

# Limit rows returned (does NOT reduce cost/bytes scanned)
bigquery query "SELECT * FROM table" --max-results 100

# Stream large results (outputs JSONL)
bigquery query "SELECT * FROM large_table" --stream > results.jsonl
```

**Query Flags:**

| Flag | Description |
|------|-------------|
| `--yes` / `-y` | Skip cost confirmation prompt (for automation) |
| `--format <format>` | Output format: `json` (default), `text`, `jsonl` |
| `--jsonl` | Shorthand for `--format jsonl` |
| `--stream` | Stream results as they arrive (implies JSONL) |
| `--cost-threshold <gb>` | Cost confirmation threshold in GB (default: 1) |
| `--max-results <n>` | Max rows to return (does NOT reduce cost) |
| `--file <path>` | Read query from file |
| `--stdin` | Read query from stdin |
| `-p, --project <id>` | GCP project ID |

**Important Notes:**
- `--max-results` only limits returned rows, NOT bytes scanned (no cost reduction)
- Use `LIMIT` in SQL to reduce scanned data
- Use `--yes` for automation (not `--force`, which doesn't exist)

### Query Output Formats

```bash
# JSON output (default, machine-readable)
bigquery query "SELECT * FROM dataset.table"

# Returns:
# {
#   "rows": [...],
#   "totalRows": 123,
#   "bytesProcessed": 1048576,
#   "bytesProcessedGB": 0.001,
#   "estimatedCostUSD": 0.00000625,
#   "cacheHit": false
# }

# JSONL output (one JSON object per line)
bigquery query "SELECT * FROM dataset.table" --jsonl

# Returns:
# {"col1":"value1","col2":123}
# {"col1":"value2","col2":456}

# Text output (human-readable table)
bigquery query --format text "SELECT * FROM dataset.table"
```

### Dry Run (Cost Estimation)

```bash
# Estimate cost without executing
bigquery dry-run "SELECT * FROM large_dataset.table WHERE date >= '2025-01-01'"

# Returns (JSON):
# {
#   "bytesProcessed": "1073741824",
#   "bytesProcessedGB": 1.0,
#   "bytesProcessedMB": 1024.0,
#   "estimatedCostUSD": 0.00625
# }

# Text format
bigquery dry-run "SELECT * FROM large_table" --format text

# Returns:
# Dry-run Results:
# ──────────────────────────────────────────────────
# Bytes to process: 1.00 GB
# Estimated cost:   $0.0063
```

**Use dry-run to**:
- Estimate costs before running expensive queries
- Validate query syntax
- Check partition pruning effectiveness
- Test queries in CI/CD pipelines

**Cost Formula**: `(bytesProcessed / 1TB) * $6.25`

## Dataset Operations

### Listing Datasets

```bash
# List datasets in current project (text format, default)
bigquery datasets list

# List datasets in another project
bigquery datasets list --project other-project

# JSON output
bigquery datasets list --format json

# Example output shows:
# - Dataset ID
# - Location
# - Creation time
# - Labels (if any)
```

### Describing Datasets

```bash
# Show dataset metadata
bigquery datasets describe project.dataset

# JSON output
bigquery datasets describe project.dataset --format json
```

### Creating Datasets

```bash
# Create dataset in default location
bigquery datasets create my-project.new_dataset

# Create with description and location
bigquery datasets create my-project.new_dataset \
  --description "Analytics data warehouse" \
  --location US

# Create with default table expiration (30 days)
bigquery datasets create my-project.temp_dataset \
  --default-ttl 30 \
  --location US

# Create with labels
bigquery datasets create my-project.new_dataset \
  --labels "env=prod,team=analytics"
```

### Updating Datasets

```bash
# Update description
bigquery datasets update my-project.existing_dataset \
  --description "Updated description"

# Update default table expiration
bigquery datasets update my-project.existing_dataset \
  --default-ttl 30

# Add/update labels
bigquery datasets update my-project.existing_dataset \
  --labels env=staging \
  --labels team=data
```

### Deleting Datasets

```bash
# Delete empty dataset (prompts for confirmation)
bigquery datasets delete my-project.old_dataset

# Delete non-empty dataset (includes all tables)
bigquery datasets delete my-project.old_dataset --force

# Skip confirmation (for automation)
bigquery datasets delete my-project.old_dataset --force --yes
```

## Table Operations

### Listing Tables

```bash
# List tables in a dataset (text format, first 10)
bigquery tables list my-project.my-dataset

# JSON output
bigquery tables list my-project.my-dataset --format json

# With pagination
bigquery tables list my-project.my-dataset --max-results 20 --page-token <token>
```

### Describing Table Schema

```bash
# Show table schema and metadata (text format)
bigquery tables describe my-project.my-dataset.my-table

# JSON output
bigquery tables describe my-project.my-dataset.my-table --format json

# Output includes:
# - Column names and types
# - Nullability (NULLABLE, REQUIRED, REPEATED)
# - Mode information
# - Table metadata (row count, size, location)
```

### Creating Tables

```bash
# Create table with JSON schema
bigquery tables create my-project.dataset.users \
  --schema '[{"name":"id","type":"STRING"},{"name":"email","type":"STRING"}]' \
  --description "User data"
```

### Updating Tables

```bash
# Update description
bigquery tables update my-project.dataset.table --description "Updated description"

# Set expiration (30 days in seconds)
bigquery tables update my-project.dataset.table --expiration 2592000

# Add labels
bigquery tables update my-project.dataset.table \
  --labels owner=team-data \
  --labels environment=production

# Require partition filter for queries
bigquery tables update my-project.dataset.table --require-partition-filter true
```

### Copying Tables

```bash
# Copy table within same project
bigquery tables copy my-project.source.table my-project.dest.table_copy

# Copy to different dataset
bigquery tables copy my-project.source.table my-project.archive.table_backup

# Overwrite destination if exists
bigquery tables copy my-project.source.table my-project.dest.existing_table \
  --write-disposition WRITE_TRUNCATE
```

### Deleting Tables

```bash
# Delete table
bigquery tables delete my-project.dataset.old_table
```

### Inserting Rows (Small Datasets)

**Best for <1000 rows**. Uses streaming insert API for immediate availability.

#### JSONL (Newline-Delimited JSON) Format

**From JSONL File:**

```bash
# Create sample JSONL file
cat > users.jsonl <<EOF
{"id": "1", "name": "Alice Johnson", "email": "alice@example.com", "age": 30}
{"id": "2", "name": "Bob Smith", "email": "bob@example.com", "age": 25}
{"id": "3", "name": "Charlie Brown", "email": "charlie@example.com", "age": 35}
EOF

# Insert from JSONL file
bigquery tables insert my-project.dataset.users users.jsonl --format jsonl
```

**From JSONL Stream (stdin):**

```bash
# Stream from command output
echo '{"id": "1", "name": "Alice", "email": "alice@example.com"}' | \
  bigquery tables insert my-project.dataset.users - --format jsonl

# Stream from heredoc
cat << EOF | bigquery tables insert my-project.dataset.users - --format jsonl
{"id": "1", "name": "Alice", "email": "alice@example.com", "age": 30}
{"id": "2", "name": "Bob", "email": "bob@example.com", "age": 25}
{"id": "3", "name": "Charlie", "email": "charlie@example.com", "age": 35}
EOF

# Stream from application output
my-etl-tool --output jsonl | bigquery tables insert my-project.dataset.events -

# Stream from jq transformation
cat raw_data.json | jq -c '.records[]' | \
  bigquery tables insert my-project.dataset.processed -
```

**JSONL Format Requirements:**
- Each line is a separate JSON object
- Empty lines are automatically skipped
- No commas between objects
- Ideal for streaming and large datasets
- Format: `{"field1":"value1","field2":"value2"}\n`

#### Additional Insert Options

```bash
# Skip invalid rows instead of failing
bigquery tables insert my-project.dataset.users users.jsonl --skip-invalid-rows

# Ignore unknown fields in data
bigquery tables insert my-project.dataset.users users.jsonl --ignore-unknown-values

# Combine options for production pipelines
cat production_data.jsonl | \
  bigquery tables insert my-project.dataset.production - \
    --format jsonl \
    --skip-invalid-rows \
    --ignore-unknown-values
```

**Insert Options:**
- `--format <FORMAT>`: Data format (json or jsonl)
- `--skip-invalid-rows`: Skip invalid rows instead of failing
- `--ignore-unknown-values`: Ignore unknown fields in data

### Loading Data (Large Datasets)

**Best for >10MB files or >1000 rows**. Uses BigQuery load jobs.

```bash
# Load from Cloud Storage URI (RECOMMENDED)
bigquery tables load my-project.dataset.users \
  gs://my-bucket/data.csv --format csv

# Load with schema auto-detection
bigquery tables load my-project.dataset.new_table \
  gs://my-bucket/data.csv --format csv --autodetect

# Load with replace write disposition (truncates table first)
bigquery tables load my-project.dataset.users \
  gs://my-bucket/data.csv --format csv --write-disposition WRITE_TRUNCATE

# Load JSON file
bigquery tables load my-project.dataset.events \
  gs://my-bucket/events.json --format json

# Supported formats: csv, json, jsonl, avro, parquet
bigquery tables load my-project.dataset.table \
  gs://my-bucket/data.parquet --format parquet

# CSV with skip leading rows
bigquery tables load my-project.dataset.table \
  gs://my-bucket/data.csv --format csv --skip-leading-rows 1

# Append to existing table (default)
bigquery tables load my-project.dataset.table \
  gs://my-bucket/data.json --format json --write-disposition WRITE_APPEND
```

**Load Options:**
- `--format <FORMAT>`: Source format (csv, json, jsonl, parquet, avro)
- `--autodetect`: Auto-detect schema from source
- `--skip-leading-rows <N>`: Skip N leading rows (CSV)
- `--write-disposition <MODE>`: WRITE_TRUNCATE (replace), WRITE_APPEND (default), WRITE_EMPTY
- `--create-disposition <MODE>`: CREATE_IF_NEEDED (default), CREATE_NEVER

**When to Use:**
- Large datasets (>1000 rows or >10MB)
- Data already in Cloud Storage
- Bulk data migrations

**When NOT to Use:**
- Small datasets (<1000 rows) → Use `tables insert` instead

### Extracting Data

Export table data to Cloud Storage in various formats:

```bash
# Extract table to Cloud Storage as CSV
bigquery tables extract my-project.dataset.users \
  gs://my-bucket/exports/users.csv --format csv

# Extract as JSON (newline-delimited)
bigquery tables extract my-project.dataset.events \
  gs://my-bucket/exports/events-*.json --format json

# Extract with compression
bigquery tables extract my-project.dataset.large_table \
  gs://my-bucket/exports/data-*.csv.gz --format csv --compression GZIP

# Extract as Parquet
bigquery tables extract my-project.dataset.analytics \
  gs://my-bucket/exports/analytics.parquet --format parquet

# CSV with header
bigquery tables extract my-project.dataset.data \
  gs://my-bucket/data.csv --format csv --print-header
```

**Supported Formats:** CSV, JSON (newline-delimited), Parquet, Avro
**Compression:** NONE (default), GZIP

## Job Management

BigQuery jobs are asynchronous operations for queries, loads, exports, and copies.

### Listing Jobs

```bash
# List recent jobs
bigquery jobs list

# List with pagination
bigquery jobs list --max-results 20 --page-token <token>

# Filter by state
bigquery jobs list --state-filter running
bigquery jobs list --state-filter done

# Show jobs from all users
bigquery jobs list --all-users

# JSON output
bigquery jobs list --format json
```

### Showing Job Details

```bash
# Show job details
bigquery jobs get job_abc123xyz

# JSON output
bigquery jobs get job_abc123xyz --format json
```

### Canceling Jobs

```bash
# Cancel a running job
bigquery jobs cancel job_abc123xyz
```

## MCP Server Integration

The BigQuery MCP server provides AI integration via Model Context Protocol.

### Starting MCP Server

**STDIO Mode** (for local clients):

```bash
# Start MCP server in stdio mode (read-only)
bigquery mcp stdio

# Start with write operations enabled
bigquery mcp stdio --enable-writes

# Server will:
# - Accept MCP protocol messages on stdin
# - Send responses on stdout
# - Expose BigQuery tools to MCP clients
```

**HTTP Mode** (for network clients):

```bash
# Start HTTP MCP server on default port 8080
bigquery mcp http

# Specify custom port
bigquery mcp http --port 3000

# With OAuth and email domain restriction
bigquery mcp http \
  --google-client-id <id> \
  --google-client-secret <secret> \
  --domain example.com

# Enable write operations
bigquery mcp http --enable-writes

# Server provides:
# - HTTP endpoint for MCP protocol
# - JSON-RPC over HTTP
# - Remote access to BigQuery tools
```

### MCP Configuration

Configure in Claude Code or other MCP-enabled applications:

**STDIO Mode** (`.claude/mcp.json` or similar):

```json
{
  "mcpServers": {
    "bigquery": {
      "command": "bigquery",
      "args": ["mcp", "stdio"],
      "env": {
        "GOOGLE_CLOUD_PROJECT": "my-project"
      }
    }
  }
}
```

**STDIO Mode with Writes Enabled**:

```json
{
  "mcpServers": {
    "bigquery": {
      "command": "bigquery",
      "args": ["mcp", "stdio", "--enable-writes"],
      "env": {
        "GOOGLE_CLOUD_PROJECT": "my-project"
      }
    }
  }
}
```

**HTTP Mode**:

```json
{
  "mcpServers": {
    "bigquery": {
      "url": "http://localhost:8080",
      "transport": "http"
    }
  }
}
```

## Common Workflows

### Workflow 1: Exploratory Data Analysis

```bash
# 1. Verify authentication
bigquery auth check

# 2. List available datasets
bigquery datasets list

# 3. List tables in dataset
bigquery tables list my-project.analytics

# 4. Check table schema
bigquery tables describe my-project.analytics.events

# 5. Preview data (text format for readability)
bigquery query --format text \
  "SELECT * FROM my-project.analytics.events LIMIT 10"

# 6. Get row count
bigquery query "SELECT COUNT(*) as total FROM my-project.analytics.events"

# 7. Check data distribution
bigquery query --format text "
  SELECT
    DATE(timestamp) as date,
    COUNT(*) as events
  FROM my-project.analytics.events
  GROUP BY date
  ORDER BY date DESC
  LIMIT 30
"
```

### Workflow 2: Cost-Aware Query Development

```bash
# 1. Dry run to estimate cost
bigquery dry-run "
  SELECT *
  FROM my-project.large_dataset.table
  WHERE date >= '2025-01-01'
"

# 2. If cost is acceptable, run query
bigquery query "
  SELECT *
  FROM my-project.large_dataset.table
  WHERE date >= '2025-01-01'
"

# 3. For automation, skip confirmation
bigquery query --yes "
  SELECT *
  FROM my-project.large_dataset.table
  WHERE date >= '2025-01-01'
" > results.json
```

### Workflow 3: Data Loading Pipeline

```bash
# 1. Load initial data
bigquery tables load my-project.dataset.events \
  gs://bucket/events-2025-01-01.csv \
  --format csv \
  --write-disposition WRITE_TRUNCATE

# 2. Append incremental data
bigquery tables load my-project.dataset.events \
  gs://bucket/events-2025-01-02.csv \
  --format csv \
  --write-disposition WRITE_APPEND

# 3. Verify data loaded
bigquery query "
  SELECT
    DATE(timestamp) as date,
    COUNT(*) as count
  FROM my-project.dataset.events
  GROUP BY date
  ORDER BY date
"
```

### Workflow 4: Real-Time Data Insertion

```bash
# 1. Stream JSONL from application
my-app --output jsonl | bigquery tables insert my-project.dataset.events -

# 2. Stream with transformation and error handling
cat raw_events.json | jq -c '.events[]' | \
  bigquery tables insert my-project.dataset.events - \
    --skip-invalid-rows \
    --ignore-unknown-values
```

### Workflow 5: Streaming Large Results

```bash
# 1. Stream query results to JSONL file
bigquery query "SELECT * FROM my-project.dataset.large_table" \
  --stream > results.jsonl

# 2. Process with DuckDB
duckdb -c "SELECT user_id, COUNT(*) FROM read_json_auto('results.jsonl') GROUP BY user_id"

# 3. Or process line-by-line
cat results.jsonl | while IFS= read -r line; do
  echo "$line" | jq '.field'
done
```

## Best Practices

### Query Development

1. **Always dry-run first**: Use `bigquery dry-run` to estimate costs
2. **Validate before running**: Check syntax and cost before execution
3. **Use text format for exploration**: `--format text` for human-readable tables
4. **Use JSON for automation**: `--format json` for machine processing
5. **Use JSONL for streaming**: `--jsonl` or `--stream` for large results
6. **Skip confirmations in scripts**: Use `--yes` flag for automation

### Cost Management

1. **Dry run expensive queries**: Always estimate with `bigquery dry-run`
2. **Monitor bytes processed**: Check query cost estimates before running
3. **Use partition pruning**: Filter on partitioned columns in WHERE clauses
4. **Limit result sets**: Use LIMIT for exploratory queries
5. **Select only needed columns**: `SELECT col1, col2` not `SELECT *`
6. **Set cost thresholds**: Use `BIGQUERY_COST_THRESHOLD_GB` environment variable

### Authentication

1. **Check auth first**: Run `bigquery auth check` before operations
2. **Use service accounts**: For automation and CI/CD
3. **Verify scopes**: Ensure all required BigQuery scopes are granted
4. **Re-authenticate when needed**: If check fails

### Data Loading

1. **Choose the right method**:
   - Use `insert` for <1000 rows (streaming insert API, immediate availability)
   - Use `load` for >10MB files or >1000 rows (load jobs with Cloud Storage)
2. **Use JSONL for streaming**: Newline-delimited JSON is ideal for streaming pipelines
3. **Stream from stdin**: Use `-` as file argument to pipe data from applications
4. **Handle bad records**: Use `--skip-invalid-rows` for messy data
5. **Choose write disposition**: `WRITE_TRUNCATE` for full refresh, `WRITE_APPEND` for incremental
6. **Use appropriate formats**: CSV for simple data, JSON/JSONL for complex, Parquet for large datasets

### Output Format Selection

- **JSON** (`--format json`): Default, full metadata, parsing with `jq`
- **Text** (`--format text`): Human-readable, terminal inspection
- **JSONL** (`--jsonl` or `--stream`): Streaming, pipelines, DuckDB ingestion

**Examples:**

```bash
# Parse with jq
bigquery query "SELECT * FROM table" | jq '.rows[] | select(.amount > 100)'

# Stream to file
bigquery query "SELECT * FROM large_table" --stream > data.jsonl

# Load into DuckDB
bigquery query "SELECT * FROM table" --jsonl | \
  duckdb -c "SELECT * FROM read_json_auto('/dev/stdin')"
```

### MCP Server

1. **Use stdio for local**: Prefer stdio mode for local MCP clients
2. **Use HTTP for remote**: Use HTTP mode for networked deployments
3. **Read-only by default**: Only enable writes when needed (`--enable-writes`)
4. **Secure HTTP endpoints**: Put HTTP server behind authentication/firewall
5. **Monitor server logs**: Check for errors and performance issues

## Configuration

### Environment Variables

```bash
# Set default project
export GOOGLE_CLOUD_PROJECT=my-project

# Set cost threshold (in GB, default: 1)
export BIGQUERY_COST_THRESHOLD_GB=5.0

# Set credentials (for service accounts)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Add to ~/.zshrc or ~/.bashrc for persistence
echo 'export GOOGLE_CLOUD_PROJECT=my-project' >> ~/.zshrc
echo 'export BIGQUERY_COST_THRESHOLD_GB=5.0' >> ~/.zshrc
```

### Authentication Methods

**User Credentials** (interactive):
```bash
gcloud auth application-default login
bigquery auth check
```

**Service Account** (automation):
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
bigquery auth check
```

## Troubleshooting

### Issue: "Not authenticated" or "Permission denied"

**Solution**: Check authentication and scopes

```bash
# Check current auth status
bigquery auth check

# Re-authenticate if needed
gcloud auth application-default login

# Verify gcloud is set to correct project
gcloud config get-value project

# Set project if needed
gcloud config set project my-project
```

### Issue: "Table not found"

**Solution**: Use fully qualified table names

```bash
# Wrong - missing project/dataset
bigquery query "SELECT * FROM table"

# Correct - fully qualified
bigquery query "SELECT * FROM my-project.my-dataset.my-table"

# Or use backticks for reserved words
bigquery query "SELECT * FROM \`my-project.my-dataset.my-table\`"
```

### Issue: "Query too expensive"

**Solution**: Check cost with dry-run and optimize

```bash
# Check estimated cost
bigquery dry-run "SELECT * FROM large_table WHERE date >= '2025-01-01'"

# Optimize with partition filters
bigquery dry-run "
  SELECT * FROM large_table
  WHERE _PARTITIONDATE = '2025-01-15'
"
```

## Quick Reference

```bash
# Authentication
bigquery auth check                          # Check auth status

# Queries (default: JSON output)
bigquery query "SELECT ..."                  # Execute query (JSON)
bigquery query --yes "SELECT ..."            # Skip confirmation
bigquery query --format text "SELECT ..."    # Human-readable table
bigquery query --jsonl "SELECT ..."          # JSONL output
bigquery query --stream "SELECT ..."         # Stream large results
bigquery dry-run "SELECT ..."                # Estimate cost

# Datasets
bigquery datasets list                       # List datasets
bigquery datasets describe PROJECT.DATASET   # Describe dataset
bigquery datasets create PROJECT.DATASET     # Create dataset
bigquery datasets update PROJECT.DATASET --description "..." # Update dataset
bigquery datasets delete PROJECT.DATASET     # Delete dataset

# Tables - Read Operations
bigquery tables list PROJECT.DATASET         # List tables
bigquery tables describe TABLE               # Show schema

# Tables - Write Operations
bigquery tables create TABLE --schema "..."  # Create table
bigquery tables insert TABLE file.jsonl --format jsonl  # Insert from file
cat data.jsonl | bigquery tables insert TABLE -         # Stream insert
bigquery tables load TABLE gs://bucket/file.csv         # Bulk load
bigquery tables copy SOURCE DEST             # Copy table
bigquery tables delete TABLE                 # Delete table

# Tables - Extract
bigquery tables extract TABLE gs://bucket/output.csv    # Export to GCS

# Jobs
bigquery jobs list                           # List jobs
bigquery jobs get JOB_ID                     # Job details
bigquery jobs cancel JOB_ID                  # Cancel job

# MCP Server
bigquery mcp stdio                           # MCP server (stdio, read-only)
bigquery mcp stdio --enable-writes           # MCP server (stdio, with writes)
bigquery mcp http --port 3000                # MCP server (HTTP)
```

## Summary

**Primary commands:**
- `bigquery auth check` - Authentication management
- `bigquery query` - Execute SQL with automatic cost awareness
- `bigquery dry-run` - Estimate query costs ($0 to run)
- `bigquery datasets {list,describe,create,update,delete}` - Dataset operations
- `bigquery tables {list,describe,insert,load,extract,create,update,delete,copy}` - Table operations
- `bigquery jobs {list,get,cancel}` - Job management
- `bigquery mcp {stdio,http}` - MCP server modes

**Key features:**
- Cost-aware query execution with automatic dry-run and confirmation prompts
- Configurable cost thresholds (`BIGQUERY_COST_THRESHOLD_GB`)
- Streaming insert API for real-time data (<1000 rows)
- Bulk load from Cloud Storage (>10MB files)
- Native streaming support for large results (`--stream` flag outputs JSONL)
- Built-in MCP server for AI integration (stdio and HTTP modes)
- Three output formats: JSON (default, full metadata), JSONL (streaming), text (human-readable)
- Instant startup with TypeScript/Bun (~10ms vs ~500ms for Python `bq`)
