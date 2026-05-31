---
name: looker
description: "Manage and search EasyPost's Looker BI catalog. Use when: (1) finding what data exists in Looker — search via qmd; (2) retrieving BigQuery SQL from Looker explores; (3) rebuilding the explore catalog after Looker changes; (4) fetching a specific saved Look by ID."
---

# Looker Catalog Guide

Looker explore docs live at `~/src/kb-md/looker-explores/` — one markdown file per explore,
one SQL file per query. Both are indexed by the `kb-md` qmd collection.

## Searching

Use `qmd query --no-rerank` via Bash. No MCP tools needed.

```bash
# Business-intent search
qmd query --no-rerank "USPS claim recovery by carrier"

# Find explores by domain
qmd query --no-rerank "lex: looker claims explore"

# Find queries referencing a specific BQ table
qmd query --no-rerank "lex: carrier_claims"
```

Results above 0.65 cosine similarity are strong matches. SQL files surface on table/field
name queries; markdown files surface on business-concept queries.

## Fetch a Look by ID

`mcp__looker__get_look(id)` — numeric ID from the Looker URL (`/looks/57` → `57`).
Returns title, folder, query_id, URL. Requires credentials.

## Admin Tools (Credentials Required)

Run when the explore catalog is missing or stale (new explores or dashboards added):

1. **`mcp__looker__verify_auth`** — Confirm API connectivity.
2. **`mcp__looker__catalog`** — Crawl the instance; writes JSONL to `~/.looker/catalog/`. Incremental.
   - Key params: `folder_id` (scope crawl), `workers` (default 4)
3. **`mcp__looker__enrich`** — Generate per-explore markdown + per-query SQL files for qmd indexing.
   - Defaults: `out_dir` → `~/src/kb-md/looker-explores/`, `dict_dir` → `~/workspace/resources/bigquery/domains/`, `cache_dir` → `~/.looker/annotation_cache`
   - Use `no_annotate: true` to skip Claude Haiku annotation.
4. **`mcp__looker__index_build`** — Runs `qmd update` to refresh the search index.

After enrich + index_build, `qmd query` will surface the new content.

## Storage Paths

```
~/.looker/catalog/                    # JSONL from catalog crawl
~/.looker/annotation_cache/           # Claude Haiku annotation cache
~/src/kb-md/looker-explores/          # Per-explore markdown (thin, no SQL)
~/src/kb-md/looker-explores/{explore}/ # Per-query .sql files with metadata headers
```
