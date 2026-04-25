# EPQ Audit Rules

`epq audit` scans `.qmd` files, `figures/fig_*.py`, `scripts/data/*.py`, and `queries/*.sql`.

## Rule Table

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
| `output/needspace-value-mismatch` | warn | yes | `\needspace` value < `fig-height + 2.5` → insufficient; increase for multi-paragraph sections |
| `output/needspace-placed-after-prose` | warn | no | `\needspace` between prose and figure (must be before the prose) |
| `figure/synthetic-data` | error | no | Fallback/sample data in figure module — any function/var prefixed `sample*`, `fallback*`, `mock*`, `dummy*`, `fake*`, `synthetic*` |
| `figure/wrong-devloop-path` | warn | yes | `/tmp/` in `__main__` block → inspection against wrong file |
| `figure/no-style-import` | warn | yes | `fig_*.py` missing `from epq import style` → uncontrolled colors and rcParams |
| `figure/palette-hex` | warn | yes | Workspace palette hex literal in `fig_*.py` — use `style.CONST` instead |
| `figure/nonpalette-color` | warn | no | Hex literal in `fig_*.py` not in any recognized palette |
| `figure/named-color` | warn | no | Matplotlib named color (`"blue"`, `"steelblue"`, `"b"`, etc.) in a `color=` kwarg |
| `engine/xelatex` | info | yes | Using xelatex (canonical: lualatex) |
| `cache/no-ttl` | info | no | `_read_cache` without TTL check |
| `cache/dot-dir` | info | yes | Cache in `.cache/` instead of `data/cache/` |
| `output/newpage-before-heading` | info | yes | `\newpage` before heading — prefer `\needspace` |
| `format/header-includes-latex` | error | yes | `latex-header.tex` in `header-includes:` — fontspec not loaded yet; `\setsansfont` silently fails |
| `format/koma-section-sans` | error | yes | `\addtokomafont{section}{\bfseries}` in `latex-header.tex` — inherits KOMA sans default; headings become LMSans Bold |
| `sql/inline-in-script` | warn | yes | `SQL = """..."""` triple-quoted string in `scripts/data/*.py` — SQL belongs in `queries/q_<name>.sql` |
| `sql/no-header` | warn | yes | `queries/*.sql` missing canonical header (`-- Loaded by:`, `-- Cache key:`, `-- Scalars written:`) |
| `bq/inline-sql` | warn | no | SQL string defined inline in QMD cell — belongs in `queries/q_<name>.sql` |

## Common Mistakes

| Mistake | Fix |
|---|---|
| `title: "My Doc"` in YAML | Remove — use `{=latex}` block. YAML title + H1 = two titles |
| `fig-pos: H` without `\needspace` | `\needspace{Xin}` BEFORE the section heading; X = FIG_HEIGHT + prose + heading |
| `\needspace` after the heading | Move BEFORE the heading |
| `\needspace` between prose and figure | Move before the heading |
| `\needspace` value too small | Use generous values — early page break beats prose/figure separation |
| `\newpage` before figure | `\needspace{Xin}` — soft break, not forced |
| `display(Markdown(...))` | Add `#\| output: asis` or markdown renders as literal text |
| `/tmp/fig-NAME.png` in `__main__` | Write to `{project}_files/figure-pdf/{LABEL}-output-1.png` |
| `fig_*.py` without `from epq import style` | Add import + `style.apply_style()` in `render()` |
| Hardcoded `"#1e3a5f"` in `fig_*.py` | Use `style.NAVY` etc |
| `bq.run_bq_query()` + cache, no `on_empty='raise'` | Empty BQ result silently cached → KeyError at render |
| `plt.savefig()` after `plt.close()` | `render(data)` → `savefig()` → `close("all")` |
| `_load_sample_data`, `render({})`, hardcoded rows | Use real cache — `RuntimeError` on miss |
| `render(data: dict)` signature | Use typed `@dataclass class Data` |
| Inline `ax.bar()` in QMD | Extract to `figures/fig_*.py` |
| `suptitle(y=1.02)` | `y=1.0` + `subplots_adjust(top=0.85)` |
| `pdf-engine: xelatex` | `lualatex` |
| `header-includes: - \input{latex-header.tex}` | Use `include-in-header: - file: latex-header.tex` |
| `\usepackage{fontspec}` in `latex-header.tex` | Do NOT add font config — body uses LM Roman; figures use Helvetica Neue via `style.apply_style()` |
| `\addtokomafont{section}{\bfseries}` in `latex-header.tex` | Use `\setkomafont{section}{\normalfont\bfseries}` |
| `SQL = """..."""` in extract script | Extract to `queries/q_<name>.sql`, load with `read_text()` |
