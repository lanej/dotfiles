# Medallion Architecture: Raw → Staging → Enriched

A three-layer data architecture pattern for organizing data pipelines, also known as Bronze → Silver → Gold.

## Layer Definitions

### Raw / Bronze Layer
**Purpose:** Preserve source data exactly as received

- Append-only tables (never update or delete)
- Minimal or no transformation
- Include extraction metadata (`extracted_at`, `source`, etc.)
- May contain duplicates or multiple versions of the same record
- Schema matches source system closely

**Example:** `engineering_demand_staging.jira_tickets_raw`, `engineering_demand_staging.phab_tasks_raw`

**Characteristics:**
- Allows re-processing without re-extraction
- Historical versioning of source records
- Cheap storage (compressed, partitioned)
- Deduplication happens in next layer

### Staging / Silver Layer
**Purpose:** Cleaned, conformed, deduplicated data

- Deduplicated records (typically "latest version wins" via `ROW_NUMBER() OVER`)
- Light transformation and normalization
- Business logic validation
- Type casting and standardization
- May still be source-system oriented (one staging table per source)

**Example:** Views that deduplicate raw tables, or materialized tables with basic cleaning

**Characteristics:**
- Queryable for analysis
- Still relatively close to source
- Multiple silver tables may feed one gold entity

### Enriched / Gold Layer
**Purpose:** Business-ready, aggregated, joined data

- Joins across source systems
- Derived metrics and calculations
- Business entity modeling (not source-system modeling)
- Optimized for consumption (denormalized, pre-aggregated)
- May include slowly-changing dimensions (SCD Type 2)

**Example:** `engineering_demand.classified_tickets_enriched` (joins classified_tickets with DORA, user identity, carrier integration)

**Characteristics:**
- Ready for BI/reporting/ML
- High-value transformations (customer attribution, team mapping)
- May be materialized for performance

## Workflow Pattern

```
Source API → extract.py → raw.jsonl → upload.sh → Raw Layer (append-only)
                                                         ↓
                                            Staging Layer (deduplicate via view/query)
                                                         ↓
                                      Enriched Layer (join, derive, aggregate)
                                                         ↓
                                             Analytics / Reports
```

## Implementation Choices

### View vs Materialized Table

**Use views for:**
- Staging deduplication (cheap, always fresh)
- Gold layer when underlying data changes frequently
- Transformations that are fast to compute

**Use materialized tables for:**
- Expensive joins or aggregations
- Gold layer serving dashboards (pre-compute for speed)
- When freshness SLA allows periodic refresh

### Refresh Strategy

**Raw:** Continuous append (event-driven or scheduled extraction)
**Staging:** On-demand via view, or incremental refresh if materialized
**Gold:** Scheduled refresh (daily/hourly) or triggered by upstream changes

## Schema Management

Prefer YAML-based schema definitions over inline SQL DDL:
- Version-controlled schema changes
- Diff-friendly (line-by-line changes, not one-line JSON blobs)
- Separation of schema (YAML) from infrastructure (Terraform/OpenTofu)
- Tooling integration (linters, validators)

See engineering-demand repo for reference: `infra/schemas/*.yml` → Terraform `jsonencode(yamldecode(file()))`.

## Common Patterns

**Deduplication in staging:**
```sql
SELECT * FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY key ORDER BY extracted_at DESC) AS rn
  FROM raw_table
) WHERE rn = 1
```

**Temporal joins in enriched (SCD Type 2):**
```sql
LEFT JOIN dimension_table d
  ON fact.entity_id = d.entity_id
  AND fact.created >= d.effective_from
  AND (fact.created < d.effective_to OR d.effective_to IS NULL)
```

**Avoid re-extraction when possible:**
- Store data in Raw even if not immediately needed
- Add fields to extraction early (easier than backfilling)
- Extraction scripts should be idempotent (safe to re-run)
