---
name: dora
description: "DORA engineering metrics project at ~/src/dora. Load when: querying DORA BigQuery views (deployment frequency, lead time, change failure rate, alerts, review time) from any project; joining against DORA.unified_identity or DORA_clean.* views from any project; running the data pipeline (just refresh, just download-*, just upload-*); making OpenTofu infrastructure changes to DORA tables or views; working with team attribution, team identity, or engineer roster data."
---

# DORA — EasyPost Engineering Metrics

Project: `~/src/dora` | BQ project: `easypost-platform`

## Dataset Layers

| Dataset | Purpose | When to query |
|---------|---------|---------------|
| `DORA_raw` | Append-only raw inputs — accumulate duplicates | **Never query directly** |
| `DORA_clean` | Deduplicated views — one authoritative row per entity | Direct entity access (bugs, deployments, revisions, ADO PRs) |
| `DORA` | Analytical views + curated tables | All reporting and metric computation |

## Core Rules

- **Never query `DORA_raw.*`** — always use `DORA_clean` or `DORA` views
- **`dora_team_name` must be canonical display names** — e.g. `'Platform'`, `'Carriers'`, `'USPS'`; never HR cost-center codes like `'236 - Enterprise'`
- **Always `dry_run` before executing BQ queries** — use `mcp__bigquery__dry_run` or `bigquery dry-run "..."`
- **Staleness**: `docs/bigquery-data-dictionary.md` is authoritative and kept in sync by commit policy; when a view name is uncertain, check there first

## Auth / Environment

```bash
gcloud auth application-default login   # BQ auth
```

Required CLIs: `gh` (GitHub), `az` (Azure DevOps), `pd` (PagerDuty), `phab` (Phabricator)

## Domain References

Read the relevant file with the Read tool before working in that domain:

| Domain | File | Covers |
|--------|------|--------|
| Metrics / BQ queries | `~/.claude/skills/dora/references/metrics.md` | Primary views per DORA pillar, secondary views, query patterns, team + date filters |
| Data pipeline | `~/.claude/skills/dora/references/pipeline.md` | `just` commands, upload CLI taxonomy (3 CLIs), troubleshooting |
| Team attribution / identity | `~/.claude/skills/dora/references/identity.md` | `unified_identity`, email_prefix join key, taxonomy anti-patterns, PHAB overrides |
| Infrastructure | `~/.claude/skills/dora/references/infra.md` | Schema authoring (`infra/schemas/*.yml`), view/table workflow, column rename rules |
| Enterprise / Azure DevOps | `~/.claude/skills/dora/references/enterprise.md` | Two ADO orgs, PR/commit/bug/task tables, email join pattern, CLS deployments |
