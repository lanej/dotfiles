---
name: looker
description: "Semantic search over EasyPost's Looker BI instance via MCP tools (mcp__looker__*). Use when: (1) finding what data exists in Looker ('what dashboard shows carrier revenue?', 'which explore has claims data?'); (2) retrieving BigQuery SQL from existing Looker queries to inspect or reuse; (3) discovering available fields/dimensions/measures for an explore; (4) rebuilding or refreshing the Looker index after the instance changes; (5) fetching a specific saved Look by ID."
---

# Looker MCP Tool Guide

Semantic search over EasyPost's Looker instance. Search is backed by the local qmd index — no credentials needed. Catalog/auth tools require Looker API credentials (env vars).

## Primary Tool: `search_all`

Use by default. Searches queries, explores, and dashboards in one call.

```
mcp__looker__search_all(query, limit?, catalog_dir?)
```

Returns `{ queries[], explores[], dashboards[] }` — each ranked by cosine similarity.

**Score interpretation:** ≥ 0.65 = strong match. 0.50–0.65 = related but weaker. < 0.50 = likely noise.

## Individual Search Tools

Use when you only need one result type:

**`mcp__looker__search_queries`** — Returns full generated BigQuery SQL per query. Use when you need actual SQL to inspect or run.
- Result fields: `score`, `query_id`, `explore`, `model`, `dashboard_titles[]`, `element_titles[]`, `fields[]`, `sources[]`, `generated_sql`

**`mcp__looker__search_explores`** — Aggregated view per explore. Use for "which explore covers X?" questions.
- Result fields: `score`, `explore`, `domain`, `model`, `n_queries`, `bq_tables[]`

**`mcp__looker__search_dashboards`** — Search by dashboard title and panel content.
- Result fields: `score`, `dashboard_id`, `dashboard_title`, `n_elements`, `explores[]`

**`mcp__looker__search_looks`** — Search saved Looks by title, explore, and fields.
- Result fields: `score`, `look_id`, `title`, `explore`, `bq_tables[]`

All search tools accept: `query` (required), `limit` (default 5, max 20), `catalog_dir` (default `~/.looker/catalog`).

## Fetch a Look by ID

**`mcp__looker__get_look(id)`** — Fetch a saved Look by numeric ID (from the Looker URL: `/looks/57` → `57`). Returns title, folder, query_id, and URL. Requires credentials.

## Admin Tools (Credentials Required)

Run in sequence when the index is missing or stale:

1. **`mcp__looker__verify_auth`** — Confirm API connectivity before crawling.
2. **`mcp__looker__catalog`** — Crawl the instance; writes JSONL to `~/.looker/catalog/`. Incremental (checkpoint-aware).
   - Key params: `folder_id` (scope crawl), `workers` (default 4), `out_dir` (default `~/.looker/catalog`)
3. **`mcp__looker__enrich`** — Add BQ table lineage, domain classification, and per-explore markdown for qmd indexing. Annotates with Claude Haiku via Vertex AI.
   - Defaults: `out_dir` → `~/workspace/resources/looker-queries/`, `dict_dir` → `~/workspace/resources/bigquery/domains/`, `cache_dir` → `~/.looker/annotation_cache`
   - Use `no_annotate: true` to skip Claude annotation.
4. **`mcp__looker__index_build`** — Runs `qmd update` to refresh the search index. No credentials needed.

## Usage Patterns

**"What dashboard shows carrier revenue?"**
→ `search_all("carrier revenue")` → check dashboards + queries

**"Find the SQL for shipment volume by state"**
→ `search_queries("shipment volume by state")` → read `generated_sql`

**"Which explore covers claims data?"**
→ `search_explores("claims")` → check `bq_tables` and `domain`

**"I need to build a query about X — what fields exist?"**
→ `search_queries` for similar queries → inspect `fields[]` to see available dimensions/measures

**Search returns weak results (low scores or wrong domain)**
→ Index may be stale. Run: `verify_auth` → `catalog` → `enrich` → `index_build`

## Storage Paths

```
~/.looker/catalog/              # JSONL from catalog crawl
~/.looker/catalog/queries.jsonl
~/.looker/catalog/checkpoint.json
~/.looker/annotation_cache/    # Claude Haiku annotation cache
~/workspace/resources/looker-queries/  # Per-explore markdown (qmd-indexed)
```
