# Looker MCP Tool Guide

Semantic search over EasyPost's Looker BI instance. Local ONNX embeddings (BGE-small-en-v1.5, 384 dims) stored in SQLite at `~/.looker/index.db`. No credentials needed for search.

## Primary Tool: `search_all`

Search queries, explores, and dashboards in one call. Use this by default.

```
Parameters:
  query (string, required): Natural language search
  limit (number, optional): Max results per category (default: 5, max: 20)
  db (string, optional): Index DB path (default: ~/.looker/index.db)

Returns: { queries: QuerySearchResult[], explores: ExploreSearchResult[], dashboards: DashboardSearchResult[] }
```

## Individual Search Tools

Use when you only need one result type:

**`search_queries`** — Returns full generated BigQuery SQL per query. Use when you need actual SQL.
- Fields: `score`, `query_id`, `explore`, `model`, `dashboard_titles[]`, `element_titles[]`, `fields[]`, `sources[]`, `generated_sql`

**`search_explores`** — Aggregated view across all queries for each explore. Use for "which explore covers X?" questions.
- Fields: `score`, `explore`, `domain`, `model`, `n_queries`, `bq_tables[]`
- Domains: revenue, operations, claims, customers, engineering, finance, unknown

**`search_dashboards`** — Search dashboards by title and panel content.
- Fields: `score`, `dashboard_id`, `dashboard_title`, `n_elements`, `explores[]`

All search tools share same `query`, `limit`, `db` parameters.

## Score Interpretation

- Cosine similarity [0, 1]
- **≥ 0.65**: Strong match — high confidence result
- **0.50–0.65**: Related but weaker — worth reviewing
- **< 0.50**: Likely noise

## Admin Tools (Credentials Required)

**`verify_auth`** — Check Looker API connectivity. Run before `catalog`.
- Params: `base_url`, `client_id`, `client_secret`, `token_cmd` (all optional, fallback to env vars)

**`catalog`** — Crawl Looker instance: dashboards, looks, queries with generated SQL.
- Params: `base_url`, `client_id`, `client_secret`, `token_cmd`, `folder_id`, `out_dir` (default: `~/.looker/catalog`), `workers` (default: 4), `checkpoint`
- Output: `queries.jsonl`, `dashboard_elements.jsonl`, `looks.jsonl`, `errors.jsonl`, `checkpoint.json`
- Incremental: checkpoint-aware, re-runs only fetch new queries

**`index_build`** — Build/refresh local search index from catalog JSONL.
- Params: `queries_path`, `elements_path`, `db`, `force`
- Three phases: query embeddings → explore embeddings → dashboard embeddings
- No API key needed (local ONNX model)

**`enrich`** — Add BigQuery table lineage, domain classification, per-explore markdown for PKM.
- Params: `queries_path`, `elements_path`, `looks_path`, `dict_dir`, `out_dir`, `cache_dir`, `no_annotate`
- Optional Claude Haiku annotation (needs ANTHROPIC_API_KEY)
- Outputs per-explore `.md` files with YAML frontmatter

## CLI Equivalents

```bash
looker search all "shipment volume by carrier"
looker search queries "revenue last 30 days"
looker search explores "carrier claims"
looker search dashboards "sales pipeline"
looker auth check
looker catalog --folder-id N --out-dir DIR
looker index build --queries PATH --db PATH
looker mcp stdio
```

## Storage Paths

```
~/.looker/index.db                         # Main SQLite index
~/.looker/catalog/                         # JSONL from catalog crawl
~/.looker/catalog/queries.jsonl            # Query metadata + SQL
~/.looker/catalog/dashboard_elements.jsonl
~/.looker/catalog/checkpoint.json          # Incremental tracking
~/.cache/looker/fastembed/                 # ONNX model cache
```

## Usage Patterns

**"What dashboard shows carrier revenue?"**
→ `search_all` with query "carrier revenue" → check dashboards + queries

**"Find the SQL for shipment volume by state"**
→ `search_queries` with query "shipment volume by state" → read `generated_sql`

**"Which explore covers claims data?"**
→ `search_explores` with query "claims" → check `bq_tables` and `domain`

**"I need to build a query about X — what fields exist?"**
→ `search_queries` for similar queries → inspect `fields[]` to see available dimensions/measures

**Rebuilding the index after Looker changes:**
→ `verify_auth` → `catalog` → `index_build` → optionally `enrich`
