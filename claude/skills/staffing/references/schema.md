# Staffing DuckDB — Schema Reference

**DB path:** `~/workspace/areas/staffing/staffing.duckdb`

**Source:** HRIS "Opex TD" export, company code 80405 (Engineering, CS, CX, Professional Services, Product, UX, WeSupply, post-sales). Does NOT include G&A, Finance, Sales, Marketing, Legal — use BigQuery `dim.users` for company-wide data.

**Load workflow:** Replace `areas/staffing/data/active-headcount.xlsx` with latest "Opex TD.xlsx", then `just load-date YYYY-MM-DD` from within `areas/staffing/`.

---

## Tables and Views

| Object | Type | Contents |
|---|---|---|
| `headcount_history` | TABLE | All rows (active + inactive), append-only; keyed by `(snapshot_date, employee_id)` |
| `current_headcount` | VIEW | Active employees from the latest snapshot only (`status_code = 'A'`) |
| `current_all` | VIEW | All employees (active + inactive) from the latest snapshot |
| `departures` | TABLE | Voluntary/Involuntary departure records parsed from Carly Anderson's weekly People Team emails (Jun 2025–May 2026). Company-wide scope (~350 headcount, not just Josh's org). 85 unique people. Zero conflicts with HRIS `status_change_reason`. Use as authoritative departure type source for people with NULL `status_change_reason`. Refresh: `uv run scripts/extract_departures_from_email.py` |

### departures schema

| Column | Notes |
|---|---|
| `week_date` | Friday date of the status update email |
| `full_name` | "First Last" — join via `TRIM(first_name \|\| ' ' \|\| last_name)` |
| `title` | Job title at time of departure (from email) |
| `departure_type` | `'Voluntary'` or `'Involuntary'` — full strings, enforced by CHECK constraint. Never abbreviated as V/I. |
| `departure_date` | Effective date stated in email |
| `is_pending` | TRUE if sourced from "Resignations Pending Last Day" section |
| `source_email_id` | Gmail message ID for audit trail |

---

## Column Reference

| Column | Type | Notes |
|---|---|---|
| `snapshot_date` | DATE | Date the HRIS export was taken |
| `employee_id` | VARCHAR | HRIS numeric ID |
| `person` | VARCHAR | Raw: `"EMPID, First Last"` (e.g. `"24449, Josh Lane "`) |
| `first_name` | VARCHAR | Parsed from `person` |
| `last_name` | VARCHAR | Parsed from `person` |
| `company_code` | VARCHAR | Always `"80405"` in this dataset |
| `status_code` | VARCHAR | `A` = Active, `T` = Inactive (no longer in org — departed, transferred out of scope, contract ended, etc.; not exclusively terminated) |
| `position_description` | VARCHAR | Formal position title from HR |
| `position_families` | VARCHAR | OpEx budget bucket: `R&D`, `COGS`, `S&M`, `G&A` |
| `cc1_description` | VARCHAR | Top-level org group (see CC1 Values below) |
| `cc2_description` | VARCHAR | Team (e.g. `"200 - USPS"`, `"335 - Customer Success"`) |
| `adj_seniority_date` | DATE | Adjusted seniority (may differ from hire date for re-hires) |
| `hire_date` | DATE | Original hire date |
| `rehire_date` | DATE | If re-hired, the re-hire date |
| `most_recent_hire_date` | DATE | Most recent hire date (accounts for re-hires); 100% populated |
| `supervisor` | VARCHAR | `"Last, First"` format (e.g. `"Lane, Joshua"`) — note full first name, not "Josh" |
| `employment_type` | VARCHAR | `RFT` = Regular Full Time, `EOR` = Employer of Record, `TPT` = Temporary Part Time |
| `employment_type_desc` | VARCHAR | Human-readable (e.g. `"Regular Full Time"`) |
| `job_title` | VARCHAR | Point-in-time job title |
| `job_title_override` | VARCHAR | Usually `"No"` or blank; HR override |
| `eeo_class` | VARCHAR | Numeric EEO class code |
| `eeo_class_desc` | VARCHAR | `"First/Mid-Level Officials & Mgrs."`, `"Professionals"`, `"Technicians"`, etc. |
| `position_change_reason` | VARCHAR | Last HR action reason (e.g. `"Promotion"`, `"Reorganization"`, `"New Position"`) |
| `termination_date` | DATE | For terminated employees |
| `deactivation_date` | DATE | System account deactivation date; 99% populated for inactive employees; NULL for active |
| `status_change_reason` | VARCHAR | Why the person left: e.g. "Voluntary - New Opportunity", "Involuntary - Reduction in Force", "Voluntary - Job Dissatisfaction". Top values in current data: RIF=62, Voluntary=37, Involuntary=21, Involuntary - Lack of Performance=21, Voluntary - New Opportunity=19 |
| `annual_salary` | DECIMAL | Annual salary; ~85% populated; sanity-capped at $5M during load |
| `pay_grade_code` | VARCHAR | Comp grade (e.g. `ENPGPGM6`); ~85% populated for active |
| `work_location` | VARCHAR | `"Remote Worker - N/A"`, `"345 Office"`, etc.; 100% populated |
| `work_country` | VARCHAR | See Work Country Values below; 100% populated |
| `visa_status` | VARCHAR | Empty in current export |
| `leave_date` | DATE | Leave of absence date; empty in current export |

---

## CC1 Values (current_headcount)

As of 2026-05-18:

| CC1 | Count |
|---|---|
| Engineering | 93 |
| Customer Support | 23 |
| Customer Success | 22 |
| Customer Support - Cedona | 21 |
| Engineering EasyPost Enterprise | 19 |
| Professional Services Enterprise | 15 |
| Customer Support EasyPost Enterprise | 12 |
| Product | 9 |
| Engineering - WeSupply | 8 |
| Customer Support - Summit | 7 |
| Sales | 6 |
| Platform Analytics | 3 |

---

## Work Country Values

| work_country | Meaning |
|---|---|
| `HOME` | Domestic / US remote (209 active, 85%) |
| `IND` | India (24 active) |
| `ROU` | Romania — WeSupply (7 active) |
| `CAN` | Canada |
| `BRA` | Brazil |
| `IRL` | Ireland |
| `PHL` | Philippines |

---

## Gotchas

- **Supervisor format**: `"Lane, Joshua"` not `"Lane, Josh"` — full first name. The `just reports` recipe uses `"Lane, Josh"` and returns 0 rows (broken for Josh). Use raw SQL: `WHERE supervisor LIKE 'Lane%'`
- **person field**: Always has a trailing space: `"24449, Josh Lane "` — use `TRIM()` or `LIKE` for matching
- **CC1 is not normalized**: `"Customer Support"`, `"Customer Support - Cedona"`, `"Customer Support - Summit"`, and `"Customer Support EasyPost Enterprise"` are all distinct groups. Use `LIKE 'Customer Support%'` to aggregate.
- **May 2026 headcount spike**: May 6 snapshot shows 247 active (jump from 221 on Apr 28). May 18 shows 245. The jump may be a scoping change in the HRIS pull, not real hiring.
- **annual_salary NULL**: ~15% of active employees are missing salary data; don't use `AVG(annual_salary)` without `WHERE annual_salary IS NOT NULL`
- **Terminated rows persist**: All terminated employees appear in `headcount_history` across all snapshots where they were present. `current_headcount` is active-only; `current_all` includes terminated from the latest snapshot only.
