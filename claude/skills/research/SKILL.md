---
name: research
description: Delegate research and context-gathering tasks to a sub-agent to protect the primary context window. Use when the user asks to "research X", "look into X", "find out about X", "gather context on X", or any investigative framing where answering requires 2+ searches or multiple sources. Also use proactively before starting substantive work when prior context is unknown. Never run research inline — always delegate.
---

# Research

Delegate all research to a sub-agent. The primary agent receives a synthesized result, not raw search output.

## When to Delegate

Delegate any research task that:
- Requires 2+ searches or source lookups
- Is exploratory (unknown territory, open-ended questions)
- Spans multiple systems (workspace KB + BQ, codebase + Jira, etc.)
- Would accumulate significant raw output inline

Single targeted lookups (one `grep`, one file read, one known query) can run inline.

## Sub-agent Type

- **Explore** — read-only search across filesystem, workspace KB, grep, BQ queries. Use for most research.
- **general-purpose** — when research requires writing intermediate files, running scripts, or multi-step computation.

## Research Protocol (Brief the Sub-agent)

The sub-agent should work through these sources in order, stopping when it has sufficient confidence:

1. **Workspace KB** — `qmd query --no-rerank "<query>"` — prior analyses, domain docs, BQ data dictionary, strategy, headcount, customer context
2. **Codebase** — Glob/Grep/Read — source of truth for implementation details
3. **BigQuery** — `mcp__bigquery__query` — live warehouse data; always `dry_run` first
4. **Jira** — `mcp__jira__jira_issues_search` JQL — ticket status, project decisions, delivery context
5. **Web** — `mcp__codex__codex` — external docs, standards, anything not internal

## Sub-agent Briefing Template

Every Agent tool call for research must include:

```
Context: [What the overall question is and why it matters — 1-2 sentences]
Question: [The specific research question to answer]
Sources: [Which layers of the research protocol to check, in order]
Output: Synthesized summary — findings, gaps, and confidence level. Under 300 words unless the question demands more detail. No raw search output.
```

## Output Contract

The sub-agent returns a synthesized summary. The primary agent then:
1. Reads the summary (not the raw search transcripts)
2. Surfaces the findings to the user
3. Proceeds with the task informed by the research

If the sub-agent reports gaps or uncertainty, surface those explicitly before proceeding.
