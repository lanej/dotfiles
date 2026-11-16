---
name: data-pipeline
description: Use when designing or implementing data pipelines in a project that selects this source-code capability, including warehouse layers, schema management, and ETL workflows.
---

# Data Pipeline Patterns

This is optional project engineering guidance installed through `source-code setup --skills data-pipeline`. Read [source-code lifecycle](../source-code-lifecycle/SKILL.md) for the selected stage, authority, and adoption. Preserve established pipeline architecture under hold/new and follow project agreement for shared/upstream changes; this package does not authorize a warehouse migration.

Architecture patterns and best practices for data pipeline design, with focus on the medallion architecture (Raw → Staging → Enriched) and declarative schema management.

## Medallion Architecture

The three-layer pattern for organizing data warehouses:

- **Raw / Bronze:** Preserve source data exactly as received (append-only)
- **Staging / Silver:** Cleaned, deduplicated, conformed data
- **Enriched / Gold:** Business-ready, joined, aggregated data

Read [references/medallion-architecture.md](references/medallion-architecture.md) for:
- Layer definitions and purposes
- Deduplication patterns
- View vs materialized table choices
- Temporal joins for slowly-changing dimensions
- Refresh strategies

## YAML Schema Management

Prefer YAML files over inline SQL DDL or JSON for schema definitions:

**Benefits:**
- Version control friendly (line-by-line diffs)
- Human readable with comments
- Separation of concerns (schema vs infrastructure)
- Consistent across upload scripts, docs, and IaC

Read [references/yaml-schema-patterns.md](references/yaml-schema-patterns.md) for:
- YAML structure examples
- Terraform integration via `jsonencode(yamldecode(file()))`
- Schema evolution patterns (safe vs unsafe changes)
- Field naming conventions
- Deprecation workflow
- Multi-source schema strategies

## Quick Reference

### Layer Selection

| Need | Layer |
|------|-------|
| Historical source data, re-processable | Raw |
| Cleaned records, ready for joining | Staging |
| Joined across sources, with metrics | Enriched |

### Schema Change Safety

| Change | Safe? | Notes |
|--------|-------|-------|
| Add nullable column | ✅ Yes | No data loss |
| Rename column | ❌ No | Use view-layer aliasing |
| Delete column | ❌ No | Deprecate first, delete later |
| Widen type (INT→FLOAT) | ✅ Yes | Usually safe |
| Narrow type (FLOAT→INT) | ❌ No | Requires migration |

### Common Gotchas

- **Deduplication:** Always use `ROW_NUMBER()` window functions in Staging layer, not `DISTINCT` (DISTINCT is non-deterministic for ties)
- **Field order:** When using Terraform `jsonencode(yamldecode())` for BigQuery, field order in YAML must match BQ (see opentofu skill)
- **Extraction idempotency:** Make extract scripts safe to re-run (upsert logic, deduplication in Raw layer)
