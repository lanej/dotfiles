---
name: bigquery
description: Use bigquery CLI for Google BigQuery operations including SQL queries, dataset/table management, schema operations, job control, and MCP server integration for semantic search and data analysis.
---
# BigQuery CLI Skill

You are a BigQuery specialist using the `bigquery` CLI tool. This skill provides comprehensive guidance for working with Google BigQuery for data warehousing, SQL queries, dataset management, and semantic search integration.

## Core Capabilities

The `bigquery` CLI provides comprehensive BigQuery integration:

1. **Query Execution**: Run SQL queries with formatting, pagination, and output control
2. **Dataset Operations**: Create, list, describe, and manage datasets
3. **Table Operations**: Create, list, describe, update, and delete tables
4. **Schema Management**: View and modify table schemas
5. **Job Management**: Monitor and manage query jobs
6. **Data Import/Export**: Load data from files and export results
7. **MCP Server**: Semantic search and natural language query interface
8. **LSP Integration**: SQL language server for editor support

## Query Operations

### Running Queries

```bash
# Basic query execution
bigquery query "SELECT * FROM dataset.table LIMIT 10"

# Query with explicit project
bigquery query --project my-project "SELECT COUNT(*) FROM dataset.table"

# Use standard SQL (default)
bigquery query --use-standard-sql "SELECT * FROM \`project.dataset.table\`"

# Use legacy SQL
bigquery query --use-legacy-sql "SELECT * FROM [project:dataset.table]"

# Dry run (estimate costs without executing)
bigquery query --dry-run "SELECT * FROM dataset.table"

# Set maximum bytes billed
bigquery query --max-bytes-billed 1000000 "SELECT * FROM dataset.table"

# Query with parameters
bigquery query --parameter "date:DATE:2025-01-15" \
  "SELECT * FROM dataset.table WHERE date = @date"

# Save results to table
bigquery query --destination-table dataset.results \
  "SELECT * FROM dataset.table WHERE condition"

# Append to existing table
bigquery query --destination-table dataset.results --append \
  "SELECT * FROM dataset.table"

# Overwrite destination table
bigquery query --destination-table dataset.results --replace \
  "SELECT * FROM dataset.table"
```

### Query Output Formats

```bash
# Default table format
bigquery query "SELECT * FROM dataset.table LIMIT 5"

# JSON output
bigquery query --format json "SELECT * FROM dataset.table"

# CSV output
bigquery query --format csv "SELECT * FROM dataset.table"

# Pretty print JSON
bigquery query --format prettyjson "SELECT * FROM dataset.table"

# Quiet mode (no progress, just results)
bigquery query --quiet "SELECT * FROM dataset.table"

# Limit rows returned
bigquery query --max-rows 100 "SELECT * FROM dataset.table"
```

### Interactive Queries

```bash
# Start interactive shell
bigquery shell

# Within shell:
# > SELECT * FROM dataset.table LIMIT 10;
# > \q  -- exit shell
```

## Dataset Operations

### Listing Datasets

```bash
# List all datasets in current project
bigquery ls

# List datasets in specific project
bigquery ls --project my-project

# List with details
bigquery ls --datasets --format prettyjson

# Filter datasets
bigquery ls --filter "labels.env:prod"
```

### Creating Datasets

```bash
# Create dataset in current project
bigquery mk dataset_name

# Create with explicit project
bigquery mk --project my-project dataset_name

# Create with description
bigquery mk --description "Production data" dataset_name

# Set default table expiration (in seconds)
bigquery mk --default-table-expiration 86400 dataset_name

# Set location
bigquery mk --location US dataset_name
bigquery mk --location EU dataset_name

# Create with labels
bigquery mk --label env:prod --label team:data dataset_name

# Complete example
bigquery mk \
  --project my-project \
  --location US \
  --description "Analytics dataset" \
  --default-table-expiration 604800 \
  --label env:prod \
  analytics_dataset
```

### Describing Datasets

```bash
# Show dataset details
bigquery show dataset_name

# Show with JSON output
bigquery show --format prettyjson dataset_name
```

### Updating Datasets

```bash
# Update dataset description
bigquery update --description "New description" dataset_name

# Update default expiration
bigquery update --default-table-expiration 172800 dataset_name

# Add labels
bigquery update --set-label team:analytics dataset_name

# Remove labels
bigquery update --remove-label old_label dataset_name
```

### Deleting Datasets

```bash
# Delete empty dataset
bigquery rm dataset_name

# Delete dataset with all tables (force)
bigquery rm -r -f dataset_name

# Delete with confirmation
bigquery rm -r dataset_name
```

## Table Operations

### Listing Tables

```bash
# List tables in dataset
bigquery ls dataset_name

# List with details
bigquery ls --format prettyjson dataset_name

# Show table metadata
bigquery ls -l dataset_name
```

### Creating Tables

```bash
# Create table with schema from file
bigquery mk --table dataset.table schema.json

# Create table with inline schema
bigquery mk --table dataset.table \
  name:STRING,age:INTEGER,email:STRING

# Create partitioned table
bigquery mk --table dataset.table \
  --time-partitioning-type DAY \
  --time-partitioning-field date \
  name:STRING,date:DATE,value:FLOAT

# Create clustered table
bigquery mk --table dataset.table \
  --clustering-fields country,city \
  country:STRING,city:STRING,population:INTEGER

# Create table from query
bigquery mk --table dataset.table --as-select \
  "SELECT * FROM source_dataset.source_table WHERE condition"

# Create external table (from GCS)
bigquery mk --external-table-definition \
  gs://bucket/path/*.csv \
  dataset.external_table \
  schema.json
```

### Describing Tables

```bash
# Show table schema and metadata
bigquery show dataset.table

# Show schema only
bigquery show --schema dataset.table

# Output as JSON
bigquery show --format prettyjson dataset.table
```

### Updating Tables

```bash
# Update table description
bigquery update dataset.table --description "Updated description"

# Update expiration time
bigquery update dataset.table --expiration 86400

# Update schema (add columns)
bigquery update dataset.table --schema new_schema.json

# Update labels
bigquery update dataset.table --set-label version:v2
```

### Deleting Tables

```bash
# Delete table
bigquery rm dataset.table

# Force delete without confirmation
bigquery rm -f dataset.table
```

## Schema Operations

### Viewing Schemas

```bash
# Show table schema
bigquery show --schema dataset.table

# Output schema as JSON
bigquery show --schema --format prettyjson dataset.table > schema.json
```

### Schema Files

Schema file format (JSON):

```json
[
  {
    "name": "id",
    "type": "INTEGER",
    "mode": "REQUIRED",
    "description": "Unique identifier"
  },
  {
    "name": "name",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "created_at",
    "type": "TIMESTAMP",
    "mode": "NULLABLE"
  },
  {
    "name": "metadata",
    "type": "RECORD",
    "mode": "REPEATED",
    "fields": [
      {
        "name": "key",
        "type": "STRING"
      },
      {
        "name": "value",
        "type": "STRING"
      }
    ]
  }
]
```

## Data Import/Export

### Loading Data

```bash
# Load from local CSV file
bigquery load dataset.table data.csv schema.json

# Load from GCS
bigquery load dataset.table gs://bucket/data.csv schema.json

# Load with autodetect schema
bigquery load --autodetect dataset.table data.csv

# Load JSON data
bigquery load --source-format NEWLINE_DELIMITED_JSON \
  dataset.table data.jsonl schema.json

# Load Parquet
bigquery load --source-format PARQUET \
  dataset.table gs://bucket/data.parquet

# Load with options
bigquery load \
  --skip-leading-rows 1 \
  --field-delimiter "," \
  --null-marker "NULL" \
  --allow-jagged-rows \
  dataset.table data.csv schema.json

# Append to existing table
bigquery load --noreplace dataset.table data.csv

# Replace table contents
bigquery load --replace dataset.table data.csv
```

### Extracting Data

```bash
# Extract to GCS as CSV
bigquery extract dataset.table gs://bucket/export.csv

# Extract as JSON
bigquery extract --destination-format NEWLINE_DELIMITED_JSON \
  dataset.table gs://bucket/export.jsonl

# Extract as Avro
bigquery extract --destination-format AVRO \
  dataset.table gs://bucket/export.avro

# Extract compressed
bigquery extract --compression GZIP \
  dataset.table gs://bucket/export.csv.gz

# Extract with wildcard (for large exports)
bigquery extract dataset.table gs://bucket/export-*.csv
```

## Job Management

### Listing Jobs

```bash
# List recent jobs
bigquery ls -j

# List jobs in specific project
bigquery ls -j --project my-project

# List with details
bigquery ls -j --format prettyjson

# Filter by status
bigquery ls -j --min-creation-time "2025-01-01T00:00:00"
bigquery ls -j --max-creation-time "2025-01-31T23:59:59"
```

### Showing Job Details

```bash
# Show job information
bigquery show -j job_id

# Show with full details
bigquery show -j --format prettyjson job_id
```

### Canceling Jobs

```bash
# Cancel running job
bigquery cancel job_id

# Cancel job in specific project
bigquery cancel --project my-project job_id
```

### Waiting for Jobs

```bash
# Wait for job to complete
bigquery wait job_id

# Wait with timeout (seconds)
bigquery wait --wait-timeout 300 job_id
```

## MCP Server Integration

The BigQuery MCP server provides semantic search and natural language query capabilities.

### Starting MCP Server

```bash
# Start MCP server for stdio communication
bigquery mcp stdio

# With specific project
bigquery mcp stdio --project my-project

# With dataset context
bigquery mcp stdio --dataset analytics

# With debug logging
bigquery mcp stdio --log-level debug
```

### MCP Server Capabilities

The MCP server exposes these tools:

1. **semantic_search**: Search tables using natural language
2. **execute_query**: Run SQL queries with automatic formatting
3. **get_schema**: Retrieve table schemas
4. **list_tables**: List available tables
5. **explain_query**: Get query execution plan
6. **optimize_query**: Suggest query optimizations

### MCP Client Usage

When using BigQuery MCP through Model Context Protocol:

```typescript
// Example MCP client code
const result = await client.callTool('semantic_search', {
  query: 'find customers who made purchases in the last 30 days',
  dataset: 'analytics',
  limit: 100
});

// Execute query through MCP
const queryResult = await client.callTool('execute_query', {
  sql: 'SELECT * FROM dataset.table LIMIT 10',
  format: 'json'
});

// Get table schema
const schema = await client.callTool('get_schema', {
  table: 'dataset.table'
});
```

### MCP Configuration

Configure in MCP settings (`.claude/mcp.json` or similar):

```json
{
  "mcpServers": {
    "bigquery": {
      "command": "bigquery",
      "args": ["mcp", "stdio"],
      "env": {
        "GOOGLE_CLOUD_PROJECT": "my-project",
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json"
      }
    }
  }
}
```

## LSP Integration

The BigQuery LSP provides SQL language features in editors.

### Starting LSP Server

```bash
# Start LSP server
bigquery lsp stdio

# With specific project context
bigquery lsp stdio --project my-project
```

### LSP Features

- **SQL syntax highlighting**: Proper tokenization
- **Schema completion**: Table and column suggestions
- **Query validation**: Syntax and semantic checks
- **Hover documentation**: Table and column info on hover
- **Go to definition**: Navigate to table definitions
- **Query formatting**: Auto-format SQL

### Editor Configuration

**Neovim:**

```lua
-- In nvim/lua/bigquery-lsp.lua
vim.api.nvim_create_autocmd("FileType", {
  pattern = { "sql", "bq", "bigquery" },
  callback = function(args)
    local client_id = vim.lsp.start({
      name = "bigquery-lsp",
      cmd = { "bigquery", "lsp", "stdio" },
      root_dir = vim.fn.getcwd(),
    })
  end,
})
```

**VS Code:**

```json
{
  "bigquery-lsp": {
    "command": "bigquery",
    "args": ["lsp", "stdio"],
    "filetypes": ["sql", "bq"]
  }
}
```

## Common Workflows

### Workflow 1: Exploratory Data Analysis

```bash
# 1. List available datasets
bigquery ls

# 2. List tables in dataset
bigquery ls analytics

# 3. Check table schema
bigquery show --schema analytics.events

# 4. Preview data
bigquery query "SELECT * FROM analytics.events LIMIT 10"

# 5. Get row count
bigquery query "SELECT COUNT(*) as total FROM analytics.events"

# 6. Check data distribution
bigquery query "
  SELECT
    DATE(timestamp) as date,
    COUNT(*) as events
  FROM analytics.events
  GROUP BY date
  ORDER BY date DESC
  LIMIT 30
"
```

### Workflow 2: Create and Populate Table

```bash
# 1. Create dataset
bigquery mk --location US --description "User analytics" user_analytics

# 2. Create table with schema
bigquery mk --table user_analytics.events \
  user_id:STRING,event_type:STRING,timestamp:TIMESTAMP,properties:JSON

# 3. Load data from GCS
bigquery load \
  --source-format NEWLINE_DELIMITED_JSON \
  user_analytics.events \
  gs://my-bucket/events/*.jsonl

# 4. Verify data loaded
bigquery query "SELECT COUNT(*) FROM user_analytics.events"

# 5. Query the data
bigquery query "
  SELECT
    event_type,
    COUNT(*) as count
  FROM user_analytics.events
  GROUP BY event_type
  ORDER BY count DESC
"
```

### Workflow 3: Daily ETL Pipeline

```bash
# 1. Create partitioned table for daily data
bigquery mk --table analytics.daily_metrics \
  --time-partitioning-type DAY \
  --time-partitioning-field date \
  date:DATE,metric:STRING,value:FLOAT

# 2. Run daily aggregation query
bigquery query \
  --destination-table analytics.daily_metrics \
  --append \
  --parameter "date:DATE:$(date +%Y-%m-%d)" \
  "
  SELECT
    @date as date,
    metric_name as metric,
    SUM(value) as value
  FROM analytics.raw_events
  WHERE DATE(timestamp) = @date
  GROUP BY metric_name
  "

# 3. Verify partition
bigquery query "
  SELECT COUNT(*)
  FROM analytics.daily_metrics
  WHERE date = CURRENT_DATE()
"
```

### Workflow 4: Cost Optimization

```bash
# 1. Dry run query to estimate cost
bigquery query --dry-run "
  SELECT * FROM large_dataset.table
  WHERE date >= '2025-01-01'
"

# 2. Set maximum bytes billed
bigquery query --max-bytes-billed 10000000 "
  SELECT * FROM large_dataset.table
  WHERE date >= '2025-01-01'
"

# 3. Use clustering and partitioning
bigquery mk --table dataset.optimized \
  --time-partitioning-type DAY \
  --time-partitioning-field date \
  --clustering-fields customer_id,region \
  date:DATE,customer_id:STRING,region:STRING,amount:FLOAT

# 4. Query with partition and cluster filters
bigquery query "
  SELECT * FROM dataset.optimized
  WHERE date = '2025-01-15'
    AND customer_id = 'CUST123'
    AND region = 'US'
"
```

### Workflow 5: Schema Evolution

```bash
# 1. View current schema
bigquery show --schema dataset.table > current_schema.json

# 2. Edit schema file to add new columns
# (Edit current_schema.json)

# 3. Update table schema
bigquery update dataset.table --schema current_schema.json

# 4. Verify new schema
bigquery show --schema dataset.table

# 5. Backfill new columns if needed
bigquery query \
  --destination-table dataset.table \
  --replace \
  "
  SELECT
    *,
    CAST(NULL AS STRING) as new_column
  FROM dataset.table
  "
```

### Workflow 6: Data Export and Analysis

```bash
# 1. Run analysis query
bigquery query --format json "
  SELECT
    region,
    product,
    SUM(revenue) as total_revenue
  FROM sales.transactions
  WHERE date >= '2025-01-01'
  GROUP BY region, product
  ORDER BY total_revenue DESC
" > analysis.json

# 2. Export large dataset to GCS
bigquery extract \
  --destination-format CSV \
  --compression GZIP \
  sales.transactions \
  gs://exports/transactions-*.csv.gz

# 3. Create external table for analysis
bigquery mk --external-table-definition \
  gs://exports/transactions-*.csv.gz \
  analysis.external_transactions \
  schema.json

# 4. Query external table
bigquery query "
  SELECT * FROM analysis.external_transactions
  WHERE revenue > 1000
"
```

## Best Practices

### Query Performance

1. **Use partitioning**: Partition large tables by date
2. **Cluster tables**: Cluster on frequently filtered columns
3. **Limit scanned data**: Use WHERE clauses on partitioned columns
4. **Avoid SELECT ***: Select only needed columns
5. **Use approximate aggregation**: APPROX_COUNT_DISTINCT for large datasets
6. **Cache results**: Leverage BigQuery's automatic caching

### Cost Management

1. **Dry run queries**: Always estimate costs with `--dry-run`
2. **Set byte limits**: Use `--max-bytes-billed` for protection
3. **Use materialized views**: Pre-aggregate frequently queried data
4. **Partition pruning**: Filter on partition columns
5. **Streaming inserts**: Use batch loading when possible
6. **Delete old data**: Set table expiration times

### Schema Design

1. **Use appropriate types**: Choose smallest suitable data types
2. **Denormalize wisely**: Balance query performance vs storage
3. **Nested fields**: Use STRUCT for related data
4. **Repeated fields**: Use ARRAY for collections
5. **Partition keys**: Choose partition columns carefully
6. **Clustering keys**: Order matters - most selective first

### Security

1. **Service accounts**: Use service account credentials
2. **Least privilege**: Grant minimal necessary permissions
3. **Encrypt data**: Use customer-managed encryption keys
4. **Audit logs**: Enable data access logging
5. **Column-level security**: Use policy tags for sensitive columns
6. **Row-level security**: Implement row-level access policies

## Configuration

### Authentication

```bash
# Authenticate with user credentials
gcloud auth login

# Use service account
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Set default project
gcloud config set project my-project
bigquery --project my-project query "SELECT 1"
```

### Environment Variables

```bash
# Set default project
export GOOGLE_CLOUD_PROJECT=my-project

# Set default dataset
export BIGQUERY_DATASET=analytics

# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Set location
export BIGQUERY_LOCATION=US
```

### Configuration File

Create `~/.bigqueryrc`:

```
[core]
project = my-project
dataset = analytics

[query]
use_legacy_sql = false
maximum_bytes_billed = 10000000

[load]
autodetect = true
```

## Troubleshooting

### Issue: "Permission denied"

**Solution**: Check service account permissions:
```bash
gcloud projects get-iam-policy PROJECT_ID
# Ensure account has bigquery.jobs.create permission
```

### Issue: "Table not found"

**Solution**: Use fully qualified table names:
```bash
# Wrong
bigquery query "SELECT * FROM table"

# Correct
bigquery query "SELECT * FROM \`project.dataset.table\`"
```

### Issue: "Quota exceeded"

**Solution**: Check quotas and request increases:
```bash
# View current quotas
gcloud compute project-info describe --project PROJECT_ID

# Request quota increase through Cloud Console
```

### Issue: "Invalid schema"

**Solution**: Validate schema file format:
```bash
# Schema must be valid JSON array
# Use bigquery show --schema to see correct format
bigquery show --schema existing.table > template_schema.json
```

### Issue: "Query too complex"

**Solution**: Break into steps with intermediate tables:
```bash
# Create intermediate result
bigquery query --destination-table temp.step1 "SELECT ..."

# Use in next step
bigquery query "SELECT * FROM temp.step1 WHERE ..."
```

## Quick Reference

```bash
# Queries
bigquery query "SELECT * FROM dataset.table"
bigquery query --dry-run "SELECT ..."
bigquery query --format json "SELECT ..."

# Datasets
bigquery ls
bigquery mk dataset_name
bigquery show dataset_name
bigquery rm -r dataset_name

# Tables
bigquery ls dataset_name
bigquery mk --table dataset.table schema.json
bigquery show dataset.table
bigquery show --schema dataset.table
bigquery rm dataset.table

# Data loading
bigquery load dataset.table data.csv schema.json
bigquery load --autodetect dataset.table data.csv
bigquery extract dataset.table gs://bucket/export.csv

# Jobs
bigquery ls -j
bigquery show -j job_id
bigquery cancel job_id

# MCP Server
bigquery mcp stdio --project PROJECT

# LSP
bigquery lsp stdio
```

## Integration with MCP Clients

When using BigQuery through MCP-enabled applications:

1. **Semantic search**: Natural language queries converted to SQL
2. **Schema discovery**: Automatic table and column suggestions
3. **Query optimization**: AI-powered query improvements
4. **Data exploration**: Interactive data analysis
5. **Visualization**: Chart and graph generation from queries

## Summary

**Primary commands:**
- `bigquery query` - Execute SQL queries
- `bigquery mk` - Create datasets/tables
- `bigquery ls` - List resources
- `bigquery show` - Display details
- `bigquery load` - Import data
- `bigquery extract` - Export data

**Key features:**
- Standard SQL support with legacy fallback
- Partitioned and clustered table support
- Streaming and batch data loading
- Job management and monitoring
- MCP server for semantic search
- LSP for editor integration

**Best practices:**
- Always dry-run expensive queries
- Use partitioning and clustering
- Set byte limits for cost control
- Choose appropriate data types
- Leverage caching
- Monitor query performance

**MCP Integration:**
- Natural language to SQL translation
- Semantic search across datasets
- Automated schema discovery
- Query optimization suggestions
