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

## Audit Rules

| Rule | Severity | Fixable | What it catches |
|---|---|---|---|
| `palette/inline` | warn | yes | Workspace palette constant defined inline |
| `palette/nonstandard` | warn | yes | Bootstrap/ad-hoc hex color |
| `bq/duplicated` | warn | no | `run_bq_query` defined inline |
| `cache/duplicated` | warn | no | `_read_cache`/`_write_cache` defined inline |
| `cache/empty-result-silenced` | warn | yes | BQ result cached without `on_empty='raise'` → silent empty → KeyError |
| `style/inline` | warn | yes | `plt.rcParams.update` in QMD cell |
| `figures/inline` | warn | no | Viz code (`ax.bar`, `plt.subplots`) in QMD cell |
| `render/unresolved-expression` | warn | no | Literal `` `{python} expr` `` in prose/caption → renders verbatim |
| `output/raw-markdown` | warn | yes | `display(Markdown(...))` without `#\| output: asis` → literal text in PDF |
| `output/double-title` | warn | yes | YAML `title:` + `# H1` in body → two titles in PDF |
| `output/float-without-needspace` | warn | yes | `fig-pos: H` without `\needspace{Xin}` → figure separates from prose |
| `figure/wrong-devloop-path` | warn | yes | `/tmp/` in `__main__` block → inspection against wrong file |
| `engine/xelatex` | info | yes | Using xelatex (canonical: lualatex) |
| `cache/no-ttl` | info | no | `_read_cache` without TTL check |
| `cache/dot-dir` | info | yes | Cache in `.cache/` instead of `data/cache/` |
| `output/newpage-before-heading` | info | yes | `\newpage` before heading — prefer `\needspace` |

`epq audit` also scans `figures/fig_*.py` (not just `.qmd` files).

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

## QMD Architecture

**The QMD is a thin shell** — prose + data-load cells + stub figure cells only.

```
{name}.qmd            ← prose + data-load cells + stub figure cells
_quarto.yml           ← jupyter: {name} set by epq scaffold
latex-header.tex      ← local copy (no external path dependency)
figures/
  __init__.py
  fig_NAME.py         ← one module per figure; render(data: dict) contract
data/cache/
  *.json              ← BQ cache files (gitignored, 24h TTL)
{name}_files/
  figure-pdf/         ← dev loop writes here; Quarto renders here
```

**Never in QMD cells:**
- Palette constants, `plt.rcParams.update`, `def run_bq_query`, `def _read_cache`
- `ax.bar(...)`, `plt.subplots(...)` — any viz code
- `title:` in YAML frontmatter (causes double title — use `{=latex}` block instead)

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
MY_SQL = """
SELECT month, revenue FROM `ep-core-data.dataset.table`
WHERE ...
"""

cached = cache.read_cache("my_query")
if cached is None:
    df = bq.run_bq_query(MY_SQL, on_empty='raise')   # raise when 0 rows = bug
    cache.write_cache("my_query", df.to_dict(orient="records"),
                      scalars={"total": float(df["revenue"].sum())})
    cached = cache.read_cache("my_query")

df_my = pd.DataFrame(cached["records"])
total = cached["scalars"]["total"]
data["my_query"] = cached["records"]
```

**Never:** `except Exception: total = 42` — silent fallback masks broken queries.

**QMD vs extraction script convention:**
- Figure/QMD cells: use default `read_cache("name")` — stale raises `StaleCache`, which `render_with_refresh.py` catches to trigger a re-run of the extraction script.
- Extraction scripts (`scripts/data/`): use `read_cache("name", on_stale="none")` — stale returns `None`, falling through to re-query BQ naturally.

```python
# scripts/data/extract_foo.py — extraction script pattern
def extract_foo() -> dict:
    cached = cache.read_cache("foo", on_stale="none")  # None on miss OR stale
    if cached is not None:
        return cached
    df = bq.run_bq_query(SQL, on_empty="raise")
    cache.write_cache("foo", df.to_dict(orient="records"), scalars={...})
    return cache.read_cache("foo")
```

## Figure Module Contract

```python
# figures/fig_revenue.py
from pathlib import Path
from epq import style, fmt

LABEL = "fig-revenue"    # matches QMD #| label: fig-revenue
FIG_WIDTH = 8.5
FIG_HEIGHT = 4.0
FIG_CAP = "Insight-focused caption — not a data description."


def render(data: dict) -> None:
    """Called from QMD stub. Do NOT call plt.show/savefig/close here."""
    import matplotlib.pyplot as plt
    style.apply_style()
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    # ... all viz code using data dict ...
    plt.tight_layout()


def _load_sample_data(data: dict):
    """Synthetic fallback for dev loop (no BQ needed)."""
    import pandas as pd
    if "my_query" in data:
        return pd.DataFrame(data["my_query"])
    return pd.DataFrame({"month": ["Q1", "Q2"], "revenue": [1.2e6, 1.4e6]})


if __name__ == "__main__":
    """Dev loop — saves to {project}_files/figure-pdf/{LABEL}-output-1.png."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _project_root = Path(__file__).parent.parent
    _out_dir = _project_root / f"{_project_root.name}_files" / "figure-pdf"
    _out_dir.mkdir(parents=True, exist_ok=True)
    out = str(_out_dir / f"{LABEL}-output-1.png")

    render({})                                         # synthetic data fallback
    plt.savefig(out, dpi=150, bbox_inches="tight")    # savefig BEFORE close
    print(f"Saved {out}")
    plt.close("all")
```

## QMD Figure Stub Cell

```python
#| label: fig-revenue
#| fig-cap: "Revenue by stream — note divergence after Q3."
#| fig-height: 4.0
#| fig-width: 8.5
#| fig-pos: "H"
#| out-width: 100%
import sys; sys.path.insert(0, str(Path("."))) if "." not in sys.path else None
from figures import fig_revenue
fig_revenue.render(data)
```

## Whitespace Control

**Always `\needspace` before figure cells with `fig-pos: H`.**

Formula: `\needspace{(FIG_HEIGHT + 0.5)in}`

```markdown
The following chart shows revenue by stream. Note the divergence after Q3.

\needspace{4.5in}

```{python}
#| label: fig-revenue
#| fig-pos: "H"
...
```
```

| FIG_HEIGHT | needspace value |
|---|---|
| 3.0in | `\needspace{3.5in}` |
| 4.0in | `\needspace{4.5in}` |
| 5.0in | `\needspace{5.5in}` |

**Never `\newpage` before a figure** — use `\needspace` (soft break, not forced).
**Never `\clearpage`** — always forces a break and flushes all floats.

`latex-header.tex` sets `\floatplacement{figure}{H}` globally — figures default to
hard placement. Individual cells can opt out with `#| fig-pos: "htbp"`.

## Title Block (No YAML `title:`)

YAML `title:` + `# H1` in body = two titles in PDF. Always use `{=latex}` instead:

```latex
```{=latex}
\renewcommand{\DOCTITLE}{My Analysis}
\renewcommand{\DOCDATE}{Feb 2026}
\renewcommand{\DOCAUTHOR}{Josh Lane}
\renewcommand{\DOCROLE}{}
\input{title-block-standard.tex}
```
```

`epq scaffold` generates QMDs without `title:` key — this is handled automatically.

## Agent Edit Protocol

**After every batch of edits, run a render before returning to the user.**

Decision (check in order):
1. Project justfile has a recipe targeting the QMD you edited → `just render-<docname>`
2. Single QMD in project → `just render`
3. Multiple QMDs or no specific recipe → `epq render .` (renders all)

```bash
cd ~/workspace/projects/<name>
just render              # single-QMD projects
just render-<docname>    # multi-QMD: recipe targeting the doc you edited
epq render .             # fallback: always works, renders all QMDs
```

This is non-negotiable — code review alone is insufficient. Render errors surface LaTeX
issues, missing imports, broken figure paths, and cell execution failures invisible from source.

If render fails: fix, re-render, verify clean before stopping.

## Dev Loop

```bash
just dev-fig revenue      # renders → {project}_files/figure-pdf/fig-revenue-output-1.png
```

Read the PNG with the Read tool. **Never use Playwright/HTML preview** — it screenshots
HTML chrome, not the raw figure.

**Visual checklist (inspect PNG, not code):**
- [ ] `\needspace` present before this figure's stub cell
- [ ] `suptitle(y=1.0)` not `y=1.02` (clips in PDF)
- [ ] All text readable without zooming (>1.5× zoom = illegible at print scale)
- [ ] 3-panel figures: `FIG_HEIGHT ≥ 4.0`
- [ ] Dark fills (NAVY/TEAL/CORAL/PURPLE/GOLD) → WHITE text
- [ ] Pale fills (LIGHT_BG, LIGHT_SLATE) → NAVY text (SLATE fails contrast)
- [ ] Bar labels within xlim — `set_clip_on(True)` makes them invisible
- [ ] `plt.savefig()` called before `plt.close()` (wrong order = blank PNG)

## Conform Extraction Pattern

Conform batch jobs take hours. They cannot run at render time. Use the three-phase
extract script pattern: cache hit → job in flight → job succeeded/submit new.

**The QMD never calls Conform.** It reads `cache.read_cache()` with a long TTL.

```python
# QMD data-load cell (pending-safe):
try:
    cached = cache.read_cache("name", ttl_hours=168)
except cache.StaleCache:
    cached = None

if cached is None:
    if cache.is_conform_pending("name"):
        print("  conform: name job in progress — using placeholder")
    data["name"] = None   # figure modules handle None → placeholder
else:
    data["name"] = cached["records"]
```

**Figure module** — handle `None` so the document renders while Conform is running:

```python
def render(data: dict) -> None:
    import matplotlib.pyplot as plt
    style.apply_style()
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    records = data.get("name")
    if records is None:
        style.render_pending_placeholder(ax, "Conform extraction in progress")
        return
    df = pd.DataFrame(records)
    # ... viz ...
    plt.tight_layout()
```

`cache.is_conform_pending(name, *, project_root=None)` — returns `True` if
`data/conform/<name>_job.json` exists (job submitted, not yet downloaded).

`style.render_pending_placeholder(ax, message="Analysis pending")` — draws a
`LIGHT_BG`-filled panel with centered `SLATE` text, no ticks, no spines.

**Extract script** (`scripts/data/extract_<name>.py`) — copy from scaffold template
`scripts/data/_extract_conform_example.py`. It manages:
- **Phase 1**: cache fresh → exit 0
- **Phase 2**: job running → print status, exit 0 (non-blocking)
- **Phase 3a**: job SUCCEEDED → download, `write_cache(ttl_hours=168)`, clear state
- **Phase 3b**: no job → `conform batch submit`, write `data/conform/<name>_job.json`

**Write TTL at write time** (for observability — `epq check-cache` shows intended TTL):
```python
cache.write_cache(_NAME, records, ttl_hours=168)
```

**Input hash invalidation**: schema + source file hashes are stored in job state.
If either changes, old job is discarded and a new submission is triggered.

**Job state file** (`data/conform/<name>_job.json`) — gitignored, ephemeral.
Cleared after successful download.

**Schemas**: `schemas/<name>.json` — add alongside the extract script.

**Polling recipe** (add to project justfile):
```just
wait-conform name:
    #!/usr/bin/env bash
    while true; do
        uv run python scripts/data/extract_{{name}}.py
        python -c "from epq import cache; cache.read_cache('{{name}}', ttl_hours=168)" 2>/dev/null && break
        echo "Still running, sleeping 5m..."; sleep 300
    done
```

## Common Mistakes

| Mistake | Fix |
|---|---|
| `title: "My Doc"` in YAML | Remove — use `{=latex}` block. YAML title + H1 = two titles |
| `fig-pos: H` without `\needspace` | `\needspace{(FIG_HEIGHT+0.5)in}` before the cell |
| `\newpage` before figure | `\needspace{Xin}` — soft break, not forced |
| `display(Markdown(...))` | Add `#\| output: asis` or markdown renders as literal text |
| `/tmp/fig-NAME.png` in `__main__` | Write to `{project}_files/figure-pdf/{LABEL}-output-1.png` |
| `bq.run_bq_query()` + cache, no `on_empty='raise'` | Empty BQ result silently cached → KeyError at render |
| `plt.savefig()` after `plt.close()` | `render({})` → `savefig()` → `close("all")` |
| Inline `ax.bar()` in QMD | Extract to `figures/fig_*.py` |
| `suptitle(y=1.02)` | `y=1.0` + `subplots_adjust(top=0.85)` |
| `pdf-engine: xelatex` | `lualatex` |
| `#3498db` etc | `style.TEAL`, `style.CORAL` etc |

## Scaffold Output

`epq scaffold <dest>` generates:

| File | What it contains |
|---|---|
| `_quarto.yml` | `jupyter: {name}` already set, `daemon: false` |
| `latex-header.tex` | Local copy — no external path dependency |
| `title-block-standard.tex` | Single-line title block |
| `title-block-memo.tex` | Two-column memo title block |
| `{name}.qmd` | Thin-shell template with `{=latex}` title, `\needspace` before figure |
| `justfile` | Thin import wrapper for canonical recipes |
| `pyproject.toml` | `package = false`, epq editable install |
| `.gitignore` | Includes `{name}_files/` |
| `figures/fig_example.py` | Canonical figure module template |
| `{name}_files/figure-pdf/` | Pre-created so dev loop works before first render |

After scaffold: `cd <dest> && just bootstrap` (uv sync + ipykernel install).

## MCP Server

Add to `.mcp.json`:
```json
"epq": {"command": "epq", "args": ["mcp"]}
```

Tools: `epq_audit`, `epq_fix`, `epq_scaffold`, `epq_list_rules`, `epq_check_cache`.

## References

- Source: `~/src/analysis-doc`
- Authoring guide: `~/src/analysis-doc/docs/AGENTS.md`
- Retrofit guide: `~/src/analysis-doc/docs/RETROFIT.md`
- Contributor guide: `~/src/analysis-doc/AGENTS.md`
- Tests: `cd ~/src/analysis-doc && uv run pytest` (281 tests)
- Reinstall: `uv tool install --editable /Users/joshlane/src/analysis-doc`
