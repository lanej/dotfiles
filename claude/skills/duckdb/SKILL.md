---
description: Fast SQL analytics and data analysis with DuckDB CLI. Use when analyzing data files (CSV, JSON, Parquet), performing statistical analysis, aggregations, joins, window functions, or complex SQL queries on local datasets. Triggers on "analyze data", "statistics", "aggregate", "query CSV/JSON/Parquet", "data analysis", "SQL query", "join datasets", "calculate metrics", or analytical operations on structured data.
---

# DuckDB Skill

DuckDB is an in-process SQL OLAP database designed for fast analytical queries on local data files. Use this skill for data analysis, statistics, aggregations, and complex queries.

## When to Use DuckDB

**Perfect for:**
- Analyzing CSV, JSON, Parquet, or Excel files
- Statistical analysis (averages, percentiles, distributions)
- Aggregations and GROUP BY operations
- Joining multiple datasets
- Window functions and analytics
- Ad-hoc SQL queries on local data
- Data exploration and profiling
- Generating summary statistics
- Complex transformations before exporting

**NOT for:**
- Simple file viewing (use `xlsx`, `xsv`, or `cat` instead)
- Single-row lookups (use `grep` or `jq`)
- Basic CSV filtering (use `xsv` for simpler cases)
- Persistent database operations (DuckDB is in-memory by default)

## Core Concepts

### In-Memory Analytics
DuckDB reads files directly without importing:
```sql
-- Query CSV directly
SELECT * FROM 'data.csv' LIMIT 10;

-- Query multiple files with glob patterns
SELECT * FROM 'data/*.parquet';

-- Query JSON
SELECT * FROM 'events.json';
```

### Zero-Copy Reading
DuckDB can read files without loading them into memory:
- CSV: Auto-detects headers, types, delimiters
- Parquet: Native columnar format (fastest)
- JSON: Both line-delimited and standard JSON

### Automatic Schema Detection
DuckDB infers schemas automatically:
```sql
-- DuckDB detects column types
DESCRIBE SELECT * FROM 'data.csv';
```

## Essential Patterns

### 1. Interactive SQL (Recommended)
```bash
duckdb -c "SELECT * FROM 'data.csv' WHERE amount > 100"
```

### 2. Persistent Database
```bash
# Create database file
duckdb mydata.db -c "CREATE TABLE users AS SELECT * FROM 'users.csv'"

# Query later
duckdb mydata.db -c "SELECT COUNT(*) FROM users"
```

### 3. Export Results
```bash
# To CSV
duckdb -c "COPY (SELECT * FROM 'data.csv' WHERE x > 10) TO 'filtered.csv'"

# To Parquet (smaller, faster)
duckdb -c "COPY (SELECT * FROM 'data.csv') TO 'data.parquet'"

# To JSON
duckdb -c "COPY (SELECT * FROM 'data.csv') TO 'output.json'"
```

### 4. Multiple Files
```bash
# Union all CSV files
duckdb -c "SELECT * FROM 'data/*.csv'"

# Join across files
duckdb -c "
  SELECT u.name, o.total 
  FROM 'users.csv' u 
  JOIN 'orders.csv' o ON u.id = o.user_id
"
```

## Common Operations

### Statistics & Aggregations
```sql
-- Summary statistics
SELECT 
  COUNT(*) as count,
  AVG(amount) as avg_amount,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount) as median,
  STDDEV(amount) as stddev,
  MIN(amount) as min,
  MAX(amount) as max
FROM 'transactions.csv';

-- Group by analysis
SELECT 
  category,
  COUNT(*) as total_count,
  SUM(amount) as total_amount,
  AVG(amount) as avg_amount
FROM 'sales.csv'
GROUP BY category
ORDER BY total_amount DESC;

-- Percentiles
SELECT 
  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY value) as p25,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY value) as p50,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY value) as p75,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY value) as p95
FROM 'metrics.csv';
```

### Window Functions
```sql
-- Running totals
SELECT 
  date,
  amount,
  SUM(amount) OVER (ORDER BY date) as running_total
FROM 'transactions.csv'
ORDER BY date;

-- Rank by category
SELECT 
  category,
  product,
  sales,
  RANK() OVER (PARTITION BY category ORDER BY sales DESC) as rank
FROM 'products.csv';
```

### Joins
```sql
-- Inner join
SELECT 
  u.name,
  o.order_date,
  o.total
FROM 'users.csv' u
INNER JOIN 'orders.csv' o ON u.id = o.user_id;

-- Left join with aggregation
SELECT 
  u.name,
  COUNT(o.id) as order_count,
  COALESCE(SUM(o.total), 0) as total_spent
FROM 'users.csv' u
LEFT JOIN 'orders.csv' o ON u.id = o.user_id
GROUP BY u.name;
```

### Filtering & Transformation
```sql
-- Complex WHERE clauses
SELECT * FROM 'data.csv'
WHERE date >= '2024-01-01'
  AND category IN ('A', 'B', 'C')
  AND amount > 100;

-- CASE expressions
SELECT 
  name,
  amount,
  CASE 
    WHEN amount < 100 THEN 'Small'
    WHEN amount < 1000 THEN 'Medium'
    ELSE 'Large'
  END as size_category
FROM 'transactions.csv';
```

### Data Profiling
```sql
-- Inspect schema
DESCRIBE SELECT * FROM 'data.csv';

-- Count nulls
SELECT 
  COUNT(*) - COUNT(column_name) as null_count,
  COUNT(*) as total_count,
  (COUNT(*) - COUNT(column_name))::FLOAT / COUNT(*) as null_percentage
FROM 'data.csv';

-- Find duplicates
SELECT 
  column_name,
  COUNT(*) as count
FROM 'data.csv'
GROUP BY column_name
HAVING COUNT(*) > 1;

-- Value distribution
SELECT 
  column_name,
  COUNT(*) as frequency,
  COUNT(*)::FLOAT / SUM(COUNT(*)) OVER () as percentage
FROM 'data.csv'
GROUP BY column_name
ORDER BY frequency DESC
LIMIT 20;
```

## File Format Support

### CSV
```sql
-- Auto-detect everything
SELECT * FROM 'data.csv';

-- Manual options
SELECT * FROM read_csv('data.csv', 
  delim=';', 
  header=true, 
  columns={'id': 'INTEGER', 'name': 'VARCHAR'}
);

-- Handle messy CSV
SELECT * FROM read_csv('messy.csv',
  auto_detect=true,
  ignore_errors=true,
  max_line_size=1048576
);
```

### JSON
```sql
-- Line-delimited JSON
SELECT * FROM 'events.ndjson';

-- Standard JSON array
SELECT * FROM read_json('data.json', format='array');

-- Nested JSON
SELECT 
  data->>'$.user.name' as user_name,
  data->>'$.event.type' as event_type
FROM 'events.json';
```

### Parquet
```sql
-- Direct query (fastest for large files)
SELECT * FROM 'data.parquet';

-- Multiple parquet files
SELECT * FROM 'data/*.parquet';
```

### Excel
```sql
-- Requires spatial extension
INSTALL spatial;
LOAD spatial;

SELECT * FROM st_read('data.xlsx');
```

## Advanced Features

### CTEs (Common Table Expressions)
```sql
WITH monthly_totals AS (
  SELECT 
    DATE_TRUNC('month', date) as month,
    SUM(amount) as total
  FROM 'transactions.csv'
  GROUP BY month
)
SELECT 
  month,
  total,
  total - LAG(total) OVER (ORDER BY month) as month_over_month_change
FROM monthly_totals;
```

### Subqueries
```sql
SELECT 
  category,
  total,
  total / (SELECT SUM(amount) FROM 'sales.csv') as percentage_of_total
FROM (
  SELECT category, SUM(amount) as total
  FROM 'sales.csv'
  GROUP BY category
) subquery
ORDER BY percentage_of_total DESC;
```

### PIVOT
```sql
-- Pivot data
PIVOT (
  SELECT category, month, amount FROM 'sales.csv'
) ON month USING SUM(amount);
```

## Output Formatting

### Pretty Tables
```bash
# Default table format
duckdb -c "SELECT * FROM 'data.csv' LIMIT 10"

# Markdown table
duckdb -markdown -c "SELECT * FROM 'data.csv' LIMIT 10"

# JSON output
duckdb -json -c "SELECT * FROM 'data.csv' LIMIT 10"

# CSV output
duckdb -csv -c "SELECT * FROM 'data.csv' LIMIT 10"
```

### Box Drawing
```bash
# Use box drawing for tables (default)
duckdb -box -c "SELECT * FROM 'data.csv' LIMIT 10"

# ASCII-only output
duckdb -ascii -c "SELECT * FROM 'data.csv' LIMIT 10"
```

## Performance Tips

### Use Parquet for Large Files
```bash
# Convert CSV to Parquet once
duckdb -c "COPY (SELECT * FROM 'large.csv') TO 'large.parquet'"

# Query Parquet (much faster)
duckdb -c "SELECT * FROM 'large.parquet' WHERE x > 100"
```

### Filter Early
```sql
-- Good: Filter before aggregation
SELECT category, COUNT(*) 
FROM 'data.csv' 
WHERE date >= '2024-01-01'
GROUP BY category;

-- Less efficient: Filter after aggregation
SELECT * FROM (
  SELECT category, COUNT(*) as cnt FROM 'data.csv' GROUP BY category
)
WHERE cnt > 100;
```

### Use Column Selection
```sql
-- Better: Select only needed columns
SELECT id, name, amount FROM 'large.csv';

-- Slower: Select all columns
SELECT * FROM 'large.csv';
```

### Limit Results
```sql
-- Use LIMIT for exploration
SELECT * FROM 'large.csv' LIMIT 100;

-- Use TABLESAMPLE for random sample
SELECT * FROM 'large.csv' USING SAMPLE 1000 ROWS;
```

## Integration with Other Tools

### Conform + DuckDB Pipeline
```bash
# Extract structured data from unstructured source, then analyze
conform extract messy_report.pdf --schema invoice_schema.json > invoices.json
duckdb -c "
  SELECT 
    vendor,
    SUM(amount) as total_amount,
    COUNT(*) as invoice_count
  FROM 'invoices.json'
  GROUP BY vendor
  ORDER BY total_amount DESC
"

# Parse unstructured text → structured CSV → analysis
conform extract survey_responses.txt --output survey.csv
duckdb -c "
  SELECT 
    sentiment,
    COUNT(*) as count,
    AVG(satisfaction_score) as avg_score
  FROM 'survey.csv'
  GROUP BY sentiment
"
```

### Pipe from xsv/jq
```bash
# xsv filter → DuckDB aggregate
xsv search -s status "active" data.csv | duckdb -c "SELECT AVG(amount) FROM read_csv('/dev/stdin')"

# jq → DuckDB
jq -c '.' events.json | duckdb -c "SELECT COUNT(*) FROM read_json_auto('/dev/stdin')"
```

### Export to xlsx
```bash
# DuckDB query → CSV → xlsx
duckdb -c "COPY (SELECT * FROM 'data.parquet' WHERE x > 100) TO 'filtered.csv'"
xlsx view filtered.csv
```

### Chain with BigQuery
```bash
# DuckDB local analysis → BigQuery upload
duckdb -c "COPY (SELECT * FROM 'local.csv' WHERE important = true) TO 'important.csv'"
bigquery insert dataset.table important.csv
```

## Common Patterns

### Time Series Analysis
```sql
SELECT 
  DATE_TRUNC('day', timestamp) as day,
  COUNT(*) as event_count,
  COUNT(DISTINCT user_id) as unique_users,
  AVG(duration) as avg_duration
FROM 'events.csv'
GROUP BY day
ORDER BY day;
```

### Cohort Analysis
```sql
WITH first_purchase AS (
  SELECT user_id, MIN(purchase_date) as cohort_date
  FROM 'purchases.csv'
  GROUP BY user_id
)
SELECT 
  DATE_TRUNC('month', cohort_date) as cohort_month,
  COUNT(DISTINCT user_id) as cohort_size,
  COUNT(DISTINCT CASE WHEN purchase_date < cohort_date + INTERVAL 30 DAYS THEN user_id END) as retained_30d
FROM 'purchases.csv' p
JOIN first_purchase f ON p.user_id = f.user_id
GROUP BY cohort_month;
```

### Distribution Analysis
```sql
-- Histogram bins
SELECT 
  FLOOR(value / 10) * 10 as bin,
  COUNT(*) as frequency
FROM 'metrics.csv'
GROUP BY bin
ORDER BY bin;
```

## Troubleshooting

### Quote Handling
```bash
# Use single quotes for file paths
duckdb -c "SELECT * FROM 'data.csv'"

# Escape quotes in nested queries
duckdb -c "SELECT * FROM 'data.csv' WHERE name = 'O''Brien'"
```

### Large Result Sets
```bash
# Use .mode for better formatting
duckdb -c ".mode line; SELECT * FROM 'large_result.csv'"

# Or export instead of displaying
duckdb -c "COPY (SELECT * FROM 'data.csv') TO 'output.csv'"
```

### Type Inference Issues
```sql
-- Force type casting
SELECT CAST(column AS INTEGER) FROM 'data.csv';

-- Or specify schema
SELECT * FROM read_csv('data.csv', columns={'id': 'INTEGER', 'date': 'DATE'});
```

## Best Practices

1. **Explore first**: Use `LIMIT` and `DESCRIBE` to understand data before complex queries
2. **Use Parquet**: Convert large CSV files to Parquet for faster repeated queries
3. **Filter early**: Apply WHERE clauses before aggregations
4. **Name columns**: Use aliases for readability
5. **Check nulls**: Always check for NULL values in statistical calculations
6. **Test queries**: Start with small datasets or LIMIT before running on full data
7. **Export results**: Save query results rather than re-running expensive queries

## Quick Reference

```bash
# Basic query
duckdb -c "SELECT * FROM 'data.csv' LIMIT 10"

# Statistics
duckdb -c "SELECT COUNT(*), AVG(amount), STDDEV(amount) FROM 'data.csv'"

# Group by
duckdb -c "SELECT category, SUM(amount) FROM 'data.csv' GROUP BY category"

# Join files
duckdb -c "SELECT * FROM 'users.csv' u JOIN 'orders.csv' o ON u.id = o.user_id"

# Export
duckdb -c "COPY (SELECT * FROM 'data.csv' WHERE x > 10) TO 'filtered.csv'"

# Markdown output
duckdb -markdown -c "SELECT * FROM 'data.csv' LIMIT 5"
```

## Resources

- Official docs: https://duckdb.org/docs/
- SQL reference: https://duckdb.org/docs/sql/introduction
- Data import: https://duckdb.org/docs/data/overview
- Functions: https://duckdb.org/docs/sql/functions/overview
