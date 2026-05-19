# Staffing Query Patterns

DB path: `~/workspace/areas/staffing/staffing.duckdb`

Always run queries from within `~/workspace/areas/staffing/` to use `just` recipes, or use the full path for raw `duckdb` calls.

---

## Justfile Recipes (fast path)

```bash
cd ~/workspace/areas/staffing

just summary                          # active headcount by cc1
just summary-team                     # by cc1 + cc2
just by-family                        # R&D / COGS / S&M / G&A breakdown
just snapshots                        # all snapshot dates with active/inactive counts
just delta 2026-03-02 2026-05-18      # who joined/left (active only, between two dates)
just managers                         # all managers (by eeo_class_desc)
just reports "Lane, Josh"             # direct reports (NOTE: broken for Josh — supervisor is "Lane, Joshua")
just find-person espinoza             # search by last or first name across all snapshots
```

---

## Custom DuckDB Queries

```bash
duckdb ~/workspace/areas/staffing/staffing.duckdb "YOUR SQL HERE"
```

### Active headcount by country

```sql
SELECT work_country, COUNT(*) n
FROM current_headcount
GROUP BY 1 ORDER BY 2 DESC;
```

### Josh's direct reports (correct form)

```sql
SELECT first_name, last_name, job_title, cc1_description, cc2_description
FROM current_headcount
WHERE supervisor LIKE 'Lane%'
ORDER BY cc1_description, last_name;
```

### Aggregate customer support (all variants)

```sql
SELECT COUNT(*) FROM current_headcount WHERE cc1_description LIKE 'Customer Support%';
```

### Engineering headcount (all variants)

```sql
SELECT COUNT(*) FROM current_headcount WHERE cc1_description LIKE 'Engineering%';
```

### Headcount by pay grade (comp leveling)

```sql
SELECT pay_grade_code, COUNT(*) n
FROM current_headcount
WHERE pay_grade_code IS NOT NULL
GROUP BY 1 ORDER BY 2 DESC;
```

### Who was added between two snapshots

```sql
WITH prev AS (
    SELECT employee_id FROM headcount_history WHERE snapshot_date = '2026-04-28' AND status_code = 'A'
),
curr AS (
    SELECT employee_id, first_name, last_name, cc1_description, job_title
    FROM headcount_history WHERE snapshot_date = '2026-05-18' AND status_code = 'A'
)
SELECT curr.*
FROM curr LEFT JOIN prev USING(employee_id)
WHERE prev.employee_id IS NULL
ORDER BY cc1_description, last_name;
```

### Who was removed between two snapshots

```sql
WITH prev AS (
    SELECT employee_id, first_name, last_name, cc1_description, job_title
    FROM headcount_history WHERE snapshot_date = '2026-04-28' AND status_code = 'A'
),
curr AS (
    SELECT employee_id FROM headcount_history WHERE snapshot_date = '2026-05-18' AND status_code = 'A'
)
SELECT prev.*
FROM prev LEFT JOIN curr USING(employee_id)
WHERE curr.employee_id IS NULL
ORDER BY cc1_description, last_name;
```

### Offboarding lag (days from termination to deactivation)

```sql
SELECT
    first_name, last_name,
    termination_date,
    deactivation_date,
    DATEDIFF('day', termination_date, deactivation_date) AS lag_days
FROM current_all
WHERE status_code = 'T'
  AND termination_date IS NOT NULL
  AND deactivation_date IS NOT NULL
ORDER BY lag_days DESC
LIMIT 20;
```

### International employees (non-HOME)

```sql
SELECT work_country, first_name, last_name, cc1_description, cc2_description, job_title
FROM current_headcount
WHERE work_country != 'HOME'
ORDER BY work_country, cc1_description, last_name;
```

### Headcount trend across all snapshots

```sql
SELECT
    snapshot_date,
    COUNT(*) FILTER (WHERE status_code = 'A') AS active,
    COUNT(*) FILTER (WHERE status_code = 'T') AS inactive
FROM headcount_history
GROUP BY 1 ORDER BY 1;
```

### Find person across all snapshots (including inactive)

```sql
SELECT snapshot_date, status_code, first_name, last_name, job_title, cc1_description, supervisor
FROM headcount_history
WHERE lower(last_name) LIKE lower('%espinoza%')
   OR lower(first_name) LIKE lower('%espinoza%')
ORDER BY snapshot_date DESC, last_name;
```

### Salary analysis by org (exclude nulls)

```sql
SELECT
    cc1_description,
    COUNT(*) FILTER (WHERE annual_salary IS NOT NULL) AS n_with_salary,
    ROUND(AVG(annual_salary) FILTER (WHERE annual_salary IS NOT NULL)) AS avg_salary,
    ROUND(MEDIAN(annual_salary) FILTER (WHERE annual_salary IS NOT NULL)) AS median_salary
FROM current_headcount
GROUP BY 1 ORDER BY avg_salary DESC;
```

---

## Departures / Offboarding

The `departures` table stores `departure_type` as the full string `'Voluntary'` or `'Involuntary'`. Always display it as-is in query output — never abbreviate to V/I.

```sql
-- All departures with type
SELECT week_date, full_name, title, departure_type, departure_date
FROM departures
ORDER BY week_date DESC, full_name;

-- Voluntary departures only
SELECT * FROM departures WHERE departure_type = 'Voluntary';

-- Involuntary departures only
SELECT * FROM departures WHERE departure_type = 'Involuntary';

-- Departure type breakdown by year
SELECT YEAR(week_date) AS yr, departure_type, COUNT(*) AS n
FROM departures
GROUP BY 1, 2 ORDER BY 1, 2;

-- Join departures with headcount_history for org context
SELECT d.week_date, d.full_name, d.departure_type, h.cc1_description, h.cc2_description
FROM departures d
LEFT JOIN headcount_history h
    ON TRIM(h.first_name || ' ' || h.last_name) = d.full_name
    AND h.snapshot_date = (
        SELECT MAX(snapshot_date) FROM headcount_history
        WHERE snapshot_date <= d.week_date
    )
ORDER BY d.week_date DESC;
```

---

## Available Snapshot Dates

Check current state with:
```bash
just snapshots
```

Or:
```sql
SELECT snapshot_date, COUNT(*) FILTER (WHERE status_code='A') AS active
FROM headcount_history GROUP BY 1 ORDER BY 1;
```
