---
name: quarto
description: Render computational documents to markdown (DEFAULT), PDF, HTML, Word, and presentations using Quarto. PREFER markdown output for composability. Use for static reports, multi-format publishing, scientific documents with citations/cross-references, or exporting Jupyter notebooks. Triggers on "render markdown", "render PDF", "publish document", "create presentation", "quarto render", or multi-format publishing needs.
---

# Quarto

Quarto's own CLI and YAML surface are documented at <https://quarto.org> — consult it for format
options rather than guessing. This file is the workspace playbook: the conventions that are
non-obvious, plus the failure modes that have already cost renders.

## Bootstrap: always `epq scaffold`

New QMD analysis projects must come from the `epq` CLI. Do **not** hand-write `pyproject.toml`,
`_quarto.yml`, `justfile`, `figures/_style.py`, or `latex-header.tex`:

```bash
epq scaffold ~/workspace/projects/my-analysis
cd ~/workspace/projects/my-analysis
just bootstrap      # uv sync + ipykernel install + mkdir data/cache
epq audit .         # verify clean (0 warnings)
```

It generates `_quarto.yml` (with `jupyter:` set), a **local** `latex-header.tex` (no external path
dependency at render time), a thin `justfile` importing the canonical recipes, `pyproject.toml`
(`package = false`, epq editable install), `.gitignore`, `figures/fig_example.py`, and a
pre-created `{name}_files/figure-pdf/`.

For existing projects: `epq audit <path>` (JSON violations with file/line/suggestion),
`epq fix <path>` (unified diffs to review and apply), `epq list-rules`.

Every analysis QMD setup cell imports the shared library — never redefine these inline:

```python
from epq import style, cache, bq, fmt

style.apply_style()          # canonical rcParams (150/200 DPI, sans-serif fallbacks)
style.NAVY, style.TEAL, ...  # workspace palette
cache.read_cache("name")     # 24h TTL file cache → None if stale/missing
bq.run_bq_query(SQL)         # BigQuery wrapper → Iterator[DataFrame]
fmt.millions_formatter()     # for ax.yaxis.set_major_formatter()
```

Each project owns its own venv and kernel. Never borrow another project's.

## Non-negotiable defaults

1. **Markdown-first**: `format: gfm` with `wrap: none`. Render PDF/HTML only when distribution
   needs it.
2. **No TOC** — clear section headings instead. Exception: documents over ~20 pages.
3. **`Markdown()` for all text output**, never `print()`/`printf()` — `print` renders as plain
   text, not formatted markdown.
4. **Charts and formatted tables, never raw dumps** — no `df.head()`, `df.info()`, bare variables.
5. **LaTeX for all math** — `$\alpha = 0.15$`, not "alpha = 0.15".
6. **Dark mode on HTML**: dual themes plus the `auto-dark` filter.
7. **PDF titling**: suppress YAML `title`/`author`/`date` (they emit `\maketitle`, which
   double-renders against a custom header). Use `##` markdown headings for sections — raw LaTeX
   headings fight Quarto's float placement.
8. **Data sources stay in code, not prose** — table, field, database, and tool names belong in
   code cells; prose describes the data and the method.
9. **Professional tables**: booktabs for PDF, Great Tables for HTML.
10. **Blank line before every list**, bullet or numbered — no exceptions.
11. **No appendix for sources** — data sources live in code blocks. The appendix carries only
    external sources the code doesn't already reference.
12. **Never auto-open artifacts** — no `&& open <file>` in render recipes.

## Every PDF chart chunk

```python
#| label: fig-name
#| fig-pos: "H"        # force-here; "!ht" defers and stacks figures
#| fig-width: 6.5      # must match figsize
#| fig-height: 3.5     # must match figsize
#| out-width: 100%
```

End every chunk with `plt.close('all')`, call `.set_clip_on(True)` on annotation text, and never
mix coordinate transforms. Skipping any of these is the usual cause of postage-stamp figures —
see `references/pdf.md` for the full diagnosis.

## BigQuery + pandas in QMD

- BigQuery integer columns come back as nullable `Int64` — `.astype('float64')` before `fillna()`.
- Quarterly data on a monthly axis: `df.set_index('quarter').reindex(monthly_idx, method='ffill')`
  plus `ax.step(..., where='post')`.
- No `\n` inside BigQuery SQL string literals in f-strings — use spaces.
- Define intermediate variables **before** the `Markdown(f"""...""")` call; f-strings evaluate at
  call time.

## References

- **`references/figures.md`** — the external Python figures architecture (`figures/fig_NAME.py`,
  the `render(data)` contract, the dev loop, and the mandatory visual-inspection protocol).
  **Read this before any figure work** — code-only review of a figure is incomplete.
- **`references/pdf.md`** — PDF rendering: title suppression, figure sizing root causes,
  `\needspace` sizing, caption numbering, LaTeX max-runs.
- **`references/authoring.md`** — document content: visual expression, narrative structure,
  `/think` document shape, data provenance and caching, the prose/code boundary, and the
  Google Docs handoff via this repo's `gdocs.css`.

Full authoring reference: `~/src/analysis-doc/docs/AGENTS.md`.
Retrofit guide: `~/src/analysis-doc/docs/RETROFIT.md`.
Reference implementations: `~/workspace/projects/luma-revenue-forecast/`,
`~/workspace/projects/revenue-forecast-2026/`.
