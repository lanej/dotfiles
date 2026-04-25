# EPQ Project Architecture

## QMD Structure

**The QMD is a thin shell** — prose + data-load cells + stub figure cells only.

```
{name}.qmd            ← prose + data-load cells + stub figure cells
_quarto.yml           ← jupyter: {name} set by epq scaffold
latex-header.tex      ← local copy (no external path dependency)
queries/
  q_<name>.sql        ← SQL files (one per data stream)
figures/
  __init__.py
  fig_NAME.py         ← one module per figure; render(data: Data) contract
scripts/data/
  extract_<name>.py   ← BQ extraction scripts (run standalone, not at render time)
data/cache/
  *.json              ← BQ cache files (gitignored, 24h TTL)
{name}_files/
  figure-pdf/         ← dev loop writes here; Quarto renders here
```

**Never in QMD cells:**
- Palette constants, `plt.rcParams.update`, `def run_bq_query`, `def _read_cache`
- `ax.bar(...)`, `plt.subplots(...)` — any viz code
- `title:` in YAML frontmatter (causes double title — use `{=latex}` block instead)
- SQL strings — SQL belongs in `queries/q_<name>.sql`

## SQL Convention

SQL lives in `queries/q_<name>.sql` with canonical header:

```sql
-- What this query does
-- Loaded by: scripts/data/extract_<name>.py
-- Cache key: <name>
-- Scalars written: <list or 'none'>
```

Loaded in the extract script:
```python
_SQL = (_PROJECT_ROOT / "queries" / "q_example.sql").read_text()
```

Exception: f-string interpolated SQL may remain inline (can't live in a static file).

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

## Report vs. Internal Document

EPQ documents are **reports**, not instruction manuals. Never include operational content in the QMD body:

- No "Refreshing This Document" sections with shell commands
- No cache invalidation instructions
- No internal file paths (`areas/staffing/staffing.duckdb`)
- No `just`, `rm`, or CLI snippets aimed at the document author

Operational instructions belong in the project `README.md` or `.claude/CLAUDE.md`.

**Test:** Would you hand this page to a VP of Sales? If not, it does not belong in the QMD.

## Source References

- Source: `~/src/analysis-doc`
- Authoring guide: `~/src/analysis-doc/docs/AGENTS.md`
- Retrofit guide: `~/src/analysis-doc/docs/RETROFIT.md`
- Tests: `cd ~/src/analysis-doc && uv run pytest`
- Reinstall: `uv tool install --editable /Users/joshlane/src/analysis-doc`
