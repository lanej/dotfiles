---
name: staffing
description: "Query and analyze Josh Lane's org headcount from the staffing DuckDB at ~/workspace/areas/staffing/staffing.duckdb. Use when asked about headcount counts, org structure, direct reports, team breakdown, hiring/attrition trends, international employees, salary/pay grade distribution, offboarding lag, or any question about people in Josh's org. Triggers on questions about how many people, who reports to whom, headcount by team/country/level, who joined or left, org size, staffing, headcount trend."
---

# Staffing Skill

Queries Josh Lane's org headcount from a DuckDB at `~/workspace/areas/staffing/staffing.duckdb`.

**Source**: HRIS "Opex TD" export, company code 80405 (Engineering, CS, CX, Professional Services, Product, UX, WeSupply, post-sales). Does NOT include G&A, Finance, Sales, Marketing, Legal — use BigQuery `dim.users` for company-wide data.

**Current snapshot**: 2026-05-18 — 245 active, 233 inactive/past

---

## Execution

For predefined queries, use `just` from within `~/workspace/areas/staffing/`. For custom queries, use the DuckDB CLI directly:

```bash
duckdb ~/workspace/areas/staffing/staffing.duckdb "SELECT ..."
```

See [references/query-patterns.md](references/query-patterns.md) for copy-paste SQL for all common scenarios.

---

## Views

- `current_headcount` — active employees only from the latest snapshot
- `current_all` — active + terminated from the latest snapshot
- `headcount_history` — all snapshots; use `WHERE snapshot_date = 'YYYY-MM-DD'` to pin to a specific date

---

## Key Gotchas

**Supervisor lookup for Josh**: `supervisor = 'Lane, Joshua'` (not "Lane, Josh" — the `just reports` recipe is broken for this case). Use `WHERE supervisor LIKE 'Lane%'`.

**Customer Support is fragmented**: Four separate CC1 values — aggregate with `WHERE cc1_description LIKE 'Customer Support%'`.

**Engineering is fragmented**: Multiple CC1 values — aggregate with `WHERE cc1_description LIKE 'Engineering%'`.

**work_country = 'HOME'** means domestic/US remote (85% of headcount). International employees: IND=24, ROU=7 (WeSupply Romania), CAN=2, BRA/IRL/PHL=1 each.

**annual_salary**: ~15% NULL for active employees. Always filter `WHERE annual_salary IS NOT NULL` before averaging.

---

## Full Schema

See [references/schema.md](references/schema.md) for the complete column catalog, CC1 values, and work_country reference table.
