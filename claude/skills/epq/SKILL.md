---
name: epq
description: EasyPost Quarto analysis library (~/src/analysis-doc). Use for scaffolding new QMD analysis projects (epq scaffold), auditing for anti-patterns (epq audit), generating fix diffs (epq fix), checking BQ cache freshness (epq check-cache), and as a shared Python library (from epq import style, cache, bq, fmt). Auto-load when creating or auditing QMD analysis projects in ~/workspace/projects/ or ~/workspace/analysis/, working with figures/fig_*.py modules, or when a render produces garbled output (double titles, unrendered markdown, whitespace issues).
---

# epq Skill

`epq` is the EasyPost Quarto analysis library — shared style, cache, BigQuery access,
formatters, and LLM-native audit tooling for `.qmd` analysis documents.

**Library:** `~/src/analysis-doc` | **CLI:** `epq` (globally installed, editable)

## Workflow

```bash
epq scaffold ~/workspace/projects/my-analysis   # bootstrap — all boilerplate generated
cd ~/workspace/projects/my-analysis
just bootstrap                                   # uv sync + ipykernel install
epq audit .                                      # 0 warnings required before render
just render                                      # live BQ validation
epq check-cache .                                # run after render failures
```

## CLI Reference

```bash
epq audit <path>            # scan for violations → JSON (file/line/message/suggestion)
epq audit --strict <path>   # promote info → warn; exit 1 on any violation (use in CI)
epq audit --rule <id> <path># target a specific rule
epq fix <path>              # emit unified diffs for fixable violations (dry-run)
epq fix --apply <path>      # apply fixable diffs directly to files
epq scaffold <dest>         # bootstrap new project (all boilerplate generated)
epq scaffold --force <dest> # overwrite existing directory
epq list-rules              # enumerate all rule IDs, severity, fix status
epq check-cache [path]      # BQ cache freshness + empty-row warnings
epq mcp                     # start MCP server over stdio
```

All output is JSON by default. `--format text` for human reading.
Exit codes: `0` = clean, `1` = violations/warnings, `2` = CLI error.

## Python Library

```python
from epq import style, cache, bq, fmt

# Palette + rcParams (canonical: 150/200 DPI, sans-serif, no spines/grid)
style.apply_style()
style.NAVY, style.TEAL, style.CORAL, style.SLATE, style.LIGHT_SLATE
style.GOLD, style.GREEN, style.WHITE, style.PURPLE, style.LIGHT_BG
tc = style.text_color_for(fill)   # WHITE for dark fills, NAVY for light

# BQ cache (24h TTL, data/cache/*.json)
data = cache.read_cache("name")                  # None if missing; raises StaleCache if stale
data = cache.read_cache("name", on_stale="none") # None if missing OR stale (extraction scripts)
cache.write_cache("name", df.to_dict(orient="records"), scalars={"total": n})
cache.cache_fresh("name")         # bool

# BigQuery (subprocess bigquery CLI)
df = bq.run_bq_query(SQL)                       # max_results=10000
df = bq.run_bq_query(SQL, on_empty='raise')     # fail on empty — use when 0 rows = bug
df["month"] = df["month"].apply(bq.extract_date) # normalize BQ date dict format

# Formatters
ax.yaxis.set_major_formatter(fmt.millions_formatter())   # $1.5M
ax.yaxis.set_major_formatter(fmt.thousands_formatter())  # $12.5K
ax.yaxis.set_major_formatter(fmt.pct_formatter())        # 12.3%
fmt.fmt_millions(1.5e6)   # '$1.5M'
fmt.fmt_pct(0.1234)       # '12.3%'
```

## Standard Setup Cell

```python
#| label: setup
#| include: false
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from IPython.display import Markdown, display

from epq import style, cache, bq, fmt
style.apply_style()
data = {}
```

## Cache Pattern

```python
#| label: load-my-query
#| include: false
cached = cache.read_cache("my_query")
if cached is None:
    df = bq.run_bq_query(_SQL, on_empty='raise')   # raise when 0 rows = bug
    cache.write_cache("my_query", df.to_dict(orient="records"),
                      scalars={"total": float(df["revenue"].sum())})
    cached = cache.read_cache("my_query")

df_my = pd.DataFrame(cached["records"])
total = cached["scalars"]["total"]
data["my_query"] = cached["records"]
```

**Never:** `except Exception: total = 42` — silent fallback masks broken queries.

SQL belongs in `queries/q_<name>.sql`, loaded with `_SQL = (Path(".") / "queries" / "q_name.sql").read_text()`.

- QMD cells: default `read_cache("name")` — stale raises `StaleCache`
- Extraction scripts: `read_cache("name", on_stale="none")` — stale returns `None`

## Title Block

YAML `title:` + `# H1` in body = two titles. Always use `{=latex}`:

```latex
```{=latex}
\renewcommand{\DOCTITLE}{My Analysis}
\renewcommand{\DOCDATE}{Feb 2026}
\renewcommand{\DOCAUTHOR}{Josh Lane}
\renewcommand{\DOCROLE}{}
\input{title-block-standard.tex}
```
```

## Agent Edit Protocol

**After every batch of edits, run a render before returning to the user.**

```bash
cd ~/workspace/projects/<name>
just render              # single-QMD projects
just render-<docname>    # multi-QMD: recipe targeting the doc you edited
epq render .             # fallback: always works, renders all QMDs
```

If render fails: fix, re-render, verify clean before stopping.

## Dev Loop

```bash
just dev-fig revenue      # renders → {project}_files/figure-pdf/fig-revenue-output-1.png
```

Read the PNG with the Read tool. Never use Playwright/HTML preview.

## Reference Files

Read these with the Read tool as needed:

| Topic | File |
|-------|------|
| Audit rules + common mistakes | `~/.claude/skills/epq/references/audit-rules.md` |
| Figure module contract, stub cell, visual checklist | `~/.claude/skills/epq/references/figures.md` |
| `\needspace` whitespace control | `~/.claude/skills/epq/references/whitespace.md` |
| Conform extraction pattern | `~/.claude/skills/epq/references/conform.md` |
| QMD architecture, scaffold output, MCP, report rules | `~/.claude/skills/epq/references/architecture.md` |
