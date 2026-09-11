---
name: duckdb
description: Use DuckDB for analytical SQL over local CSV, JSON, Parquet, and Excel files - aggregations, joins, window functions, statistics, and data profiling without an import step.
---

# DuckDB

SQL over local files with no import step. Standard SQL and DuckDB's file-reading functions work as
documented; this file covers tool selection, local database locations, and the Python API traps.

## When to reach for it

**Yes**: aggregations, GROUP BY, window functions, joins across datasets, percentiles and summary
statistics, profiling, transformations before export.

**No**: viewing a file (`xsv`, `xlsx`, `cat`), single-row lookups (`grep`, `jq`), simple column
filtering (`xsv` is less ceremony).

## Local databases in this workspace

- `areas/staffing/staffing.duckdb` — org headcount (use the `staffing` skill)
- `data/slack_qa.duckdb` — Slack Q&A pipeline storage
- `data/*.duckdb` — project-specific pipeline databases

## Reading files

Query paths directly — globs, and format detection, both work:

```sql
SELECT * FROM 'data.csv' LIMIT 10;
SELECT * FROM 'data/*.parquet';
DESCRIBE SELECT * FROM 'data.csv';   -- inspect inferred types before trusting them
```

Parquet is fastest (columnar, predicate pushdown). Convert large CSVs once if you'll query them
repeatedly: `COPY (SELECT * FROM 'big.csv') TO 'big.parquet' (FORMAT PARQUET);`

## Piping

DuckDB reads stdin via `/dev/stdin`, so it chains with the rest of the toolchain:

```bash
xsv search -s status "active" data.csv | duckdb -c "SELECT AVG(amount) FROM read_csv('/dev/stdin')"
jq -c '.' events.json | duckdb -c "SELECT COUNT(*) FROM read_json_auto('/dev/stdin')"
conform extract messy_report.pdf --output invoices.csv && duckdb -c "SELECT vendor, SUM(amount) FROM 'invoices.csv' GROUP BY 1"
duckdb -c "COPY (SELECT * FROM 'local.csv' WHERE important) TO 'important.csv'" && bigquery insert dataset.table important.csv
```

## Python API gotchas

### `rowcount` is always negative for UPDATE/DELETE

`con.execute("UPDATE ...")` then `.rowcount` returns `-1` (or a negative multiple in a loop), not
the affected row count. The statement *did* run. To report a count, run the equivalent
`SELECT COUNT(*)` with the same WHERE clause first:

```python
affected = con.execute(
    "SELECT COUNT(*) FROM users WHERE last_login < '2024-01-01'"
).fetchone()[0]
con.execute("UPDATE users SET active = false WHERE last_login < '2024-01-01'")
```

`.fetchall()` / `.df()` on SELECT are unaffected — they return real results.

### `.df().to_dict(orient="records")` coerces types

SQL NULLs arrive as typed pandas NA, not `None`, and several types are not JSON-serializable:

| DuckDB type | pandas representation | symptom |
|---|---|---|
| NULL VARCHAR/INTEGER | `float('nan')` | `AttributeError: 'float' object has no attribute 'lower'` |
| NULL TIMESTAMP | `pd.NaT` | `fromisoformat: argument must be str`; not JSON serializable |
| TIMESTAMP | `pd.Timestamp` | not JSON serializable — needs `.isoformat()` |
| ARRAY/LIST | `numpy.ndarray` | not JSON serializable — needs `.tolist()` |

Sanitize before passing rows downstream:

```python
import math, numpy as np, pandas as pd

row = {
    k: (None if (isinstance(v, float) and math.isnan(v)) or v is pd.NaT
        else v.isoformat() if isinstance(v, pd.Timestamp)
        else v.tolist() if isinstance(v, np.ndarray)
        else v)
    for k, v in row.items()
}
```

Pass `allow_nan=False` to `json.dumps` as a safety net — it raises on a leftover NaN rather than
silently emitting invalid `NaN`.
