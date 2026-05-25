---
name: qmd
description: Use qmd for workspace search — hybrid BM25+vector search with Qwen3-4B reranking over indexed workspace documents. Not to be confused with Quarto documents (.qmd files) — use epq/quarto skills for those.
---
# QMD — Workspace Search

QMD is the workspace search tool. Not to be confused with Quarto documents (`.qmd` extension) — those use the `epq` and `quarto` skills.

Use this skill when searching the workspace knowledge base for prior work, context, analyses, or decisions.

## CLI (primary interface)

```bash
qmd query --no-rerank "your question"   # hybrid search (always use --no-rerank)
qmd search "keywords"                   # BM25 only, fast, no LLM
qmd vsearch "semantic query"            # vector only
qmd get "path/to/file.md"              # fetch a specific document
qmd get "path/to/file.md:100" -l 50   # fetch with line slice
qmd multi-get "projects/**/*.md"        # batch fetch by glob
qmd update                              # re-index changed files (hash-deduplicated, fast)
qmd embed                               # generate/refresh embeddings
qmd status                              # index health
qmd ls projects                         # list indexed files in collection
```

## Reranking

**Always use `--no-rerank`.** The Qwen3-4B reranker is slow and degrades result quality: it favors prose over markdown tables (roster.md disappeared from reranked results in testing), does not fix bad top-1 hits, and compresses score variance in a way that obscures rank signal.

## Query Construction

**Start with a simple expand query.** When the topic name matches document titles, a single-line query outperforms a structured lex+vec query. Add structure only when the simple form returns off-topic results.

```bash
# Step 1: try this first
qmd query --no-rerank "EasyPost carrier economics"

# Step 2: if results are off, add structure
qmd query --no-rerank $'intent: carrier revenue and profitability\nlex: carrier margin revenue\nvec: carrier economics unit economics'
```

For structured queries, pass a multi-line query document using `$'...\n...'`:

```bash
# lex+vec combined (best recall for most topics)
qmd query --no-rerank $'intent: insurance product growth\nlex: insurance attach rate\nvec: insurance product growth small customers'

# Add hyde for nuanced topics without a short keyword summary
qmd query --no-rerank $'intent: international expansion trade-offs\nvec: international shipping markets regulatory complexity\nhyde: This document analyzes the strategic trade-offs of expanding into international shipping, covering regulatory complexity, carrier partnerships, and revenue opportunity by region.'
```

Query type semantics:
- `lex:` — BM25 keyword match. Supports negation (`-term`). **Use domain-specific terms only** — cross-domain vocabulary (e.g., "attach rate" in a carrier query) pulls in off-topic results. Quoted phrases (`"exact phrase"`) behave as proximity/bag-of-words, not true exact match.
- `vec:` — vector similarity. No negation support (parse error).
- `hyde:` — hypothetical document embedding. Unreliable as the sole query type — cached Google Docs with dense prose produce false positives at rank 1. Use as a secondary signal alongside `lex:` or `vec:`.
- `intent:` — disambiguation hint, not a search type. Metadata only.

**Negation only works in `lex:` legs.** Using `-term` in `vec:` or `hyde:` is a parse error.

## Score Interpretation

With `--no-rerank`, scores are RRF ordinal values — always the same cascade regardless of semantic relevance: rank 1 = 1.0, rank 2 = 0.5, rank 3 = 0.33, rank 4 = 0.25, rank 5 = 0.2. These indicate rank order only, not semantic distance. Do not use score values to assess result quality — use `qmd get` to inspect the actual document.

## Verifying Results

Use `qmd get` to inspect a result before trusting it — especially for structured data or when the snippet looks ambiguous:

```bash
qmd get "areas/headcount/roster.md" -l 50
```

Duplicate paths occasionally appear (same file indexed from multiple project directories). If the same content appears at ranks 1 and 4, it's a dedup artifact — treat as one result.

## Collections

- `projects` — active work, analyses, strategy docs, EPQ reports, Quarto documents
- Excludes: `data/batch/`, `data/cache/`, `gong-inputs/` (raw pipeline data, not knowledge)

## Index Maintenance

After adding or committing new files, the post-commit hook runs `qmd update` automatically.
To force a full re-embed (e.g., after adding many new files): `qmd embed`.
Log: `/tmp/qmd-post-commit.log`

## Batch Similarity — use sentence-transformers, not qmd

For N × M pairwise similarity (duplicate detection, question-to-document coverage over 1,000+ items), qmd CLI is the wrong tool. Even with `--no-rerank`, `qmd query` still runs HyDE expansion (LLM call, ~25s/query). Use `vec:` prefix to skip expansion, but even then per-call overhead makes 1,000+ queries take hours.

For batch operations: use `sentence-transformers` directly. `all-MiniLM-L6-v2` is already cached at `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/`. Embed in batch, compute pairwise similarity with numpy — handles 2,000 × 2,000 in under 5 minutes. qmd's index is for search/discovery; for bulk similarity, read source files directly.

## Sub-Agent Briefings

When briefing a sub-agent to search the workspace, give it the CLI command explicitly — do not just say "search the workspace." MCP tools can be unavailable in sub-agent contexts (disconnected server, cold-start).

Include in the briefing:

```
Search the workspace using the qmd CLI:
  qmd query --no-rerank "your topic here"
Do NOT use mcp__qmd__* tools — they may be unavailable.
```

## When to Load This Skill

Auto-load when the user:
- Asks to search the workspace, find prior analyses, or recall context
- Uses phrases like "search for", "find in workspace", "what have we done about", "do we have anything on"
- Needs cross-project context before starting new work
