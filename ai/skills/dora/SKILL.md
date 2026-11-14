---
name: dora
description: Use when querying DORA metrics, interpreting GitHub review evidence, or operating the DORA ingestion pipeline and its infrastructure contracts.
---

# DORA

Use the DORA repository's `AGENTS.md` and `docs/bigquery-data-dictionary.md` for current contracts. Read [metrics](references/metrics.md) for GitHub evidence queries, [pipeline](references/pipeline.md) for collection/backfill operations, and [infrastructure](references/infra.md) for schema/view ownership. These references describe the GitHub review-evidence capability; consult the data dictionary for other domains.

For analysis, query `DORA_silver` deduplicated entities or `DORA` analytical views. Never analyze append-only `DORA_bronze` tables directly. Team attribution uses `DORA.unified_identity`; emit canonical display names with `COALESCE(ui.team_display_name, ui.team)`. ADO email-prefix matching strips `+` tags with `r'^[^@+]+'`.

Cloud Workflows is the sole production orchestrator. `runner.py --stage <name>` runs one stage; there is no local full-pipeline or sink-skip mode. Pipeline changes write to BigQuery. Retain the existing repository scope and assessment behavior; App installation breadth is not authorization to expand scope.

Observation, capture completion, current-version evaluation, pending/retry/limited work, staleness and search completeness are different outcomes. An association does not establish causality. A successful job or a newly created subscription does not establish historical completeness. Require the user's existing authorization for production operations; this skill grants none.
