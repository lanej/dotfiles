---
name: qmd
description: Use qmd for workspace search — hybrid BM25+vector search with Qwen3-4B reranking over indexed workspace documents. Not to be confused with Quarto documents (.qmd files) — use epq/quarto skills for those.
---
# QMD — Workspace Search

QMD is the workspace search tool. Not to be confused with Quarto documents (`.qmd` extension) — those use the `epq` and `quarto` skills.

Use this skill when searching the workspace knowledge base for prior work, context, analyses, or decisions.

## MCP Tools (primary interface for agents)

- `query(searches, intent, limit, minScore)` — Hybrid search with query expansion + Qwen3-4B reranking. Best for most queries.
- `get(file)` — Fetch a specific document by path or docid (`#abc123`). Supports line slice (`file.md:100`).
- `multi_get(pattern)` — Batch fetch by glob or comma-separated paths.
- `status()` — Index health: document count, embedding coverage.

## Query Construction

Always provide `intent` to disambiguate. Combine search types for best recall:

```python
# Quick keyword lookup
searches=[{"type": "lex", "query": "NSA migration revenue"}]

# Semantic search
searches=[{"type": "vec", "query": "how does EasyPost handle USPS rate negotiation"}]

# Best recall: combine lex + vec
searches=[
    {"type": "lex", "query": "insurance attach rate"},
    {"type": "vec", "query": "insurance product growth small customers PLG"}
]

# Complex: add hyde for nuanced topics
searches=[
    {"type": "lex", "query": "carrier ROI analysis"},
    {"type": "vec", "query": "carrier economics and profitability"},
    {"type": "hyde", "query": "This document analyzes carrier ROI by comparing revenue contribution against integration and support costs across EasyPost's carrier portfolio."}
]
```

## CLI (for maintenance)

```bash
qmd query "your question"     # hybrid search (expansion + reranking)
qmd search "keywords"         # BM25 only, fast, no LLM
qmd vsearch "semantic query"  # vector only
qmd update                    # re-index changed files (hash-deduplicated, fast)
qmd embed                     # generate/refresh embeddings
qmd status                    # index health
qmd ls projects               # list indexed files in collection
```

## Collections

- `projects` — 5,459 documents: active work, analyses, strategy docs, EPQ reports, Quarto documents
- Excludes: `data/batch/`, `data/cache/`, `gong-inputs/` (raw pipeline data, not knowledge)

## Score Interpretation

- ≥0.85 — strong match, high confidence
- 0.5–0.85 — relevant, inspect snippet
- <0.5 — weak, likely noise; use `minScore: 0.5` to filter

## Index Maintenance

After adding or committing new files, the post-commit hook runs `qmd update` automatically.
To force a full re-embed (e.g., after adding many new files): `qmd embed`.
Log: `/tmp/qmd-post-commit.log`

## When to Load This Skill

Auto-load when the user:
- Asks to search the workspace, find prior analyses, or recall context
- Uses phrases like "search for", "find in workspace", "what have we done about", "do we have anything on"
- Needs cross-project context before starting new work
