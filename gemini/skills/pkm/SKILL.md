---
name: qmd
description: Use qmd for workspace search — hybrid BM25+vector search with Qwen3-4B reranking over indexed workspace documents. Not to be confused with Quarto documents (.qmd files).
---
# QMD — Workspace Search

QMD is the workspace search tool. Not to be confused with Quarto documents (`.qmd` extension).

## MCP Tools

- `query(searches, intent, limit)` — Hybrid search with expansion + reranking. Best for most queries.
- `get(file)` — Fetch a document by path or docid.
- `multi_get(pattern)` — Batch fetch by glob.
- `status()` — Index health.

## Query Construction

```python
# Best recall: combine lex + vec
searches=[
    {"type": "lex", "query": "NSA migration revenue"},
    {"type": "vec", "query": "USPS NSA migration financial impact EasyPost"}
]
intent="context about USPS NSA account migration"
```

## When to Load

Auto-load when searching workspace, finding prior analyses, or surfacing context.
