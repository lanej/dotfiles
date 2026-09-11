# Quarto PDF Rendering

Rules for PDF output: project bootstrap, title suppression, figure sizing, LaTeX float behavior.
Read before rendering any QMD to PDF, and when diagnosing a malformed or mis-sized figure.

## Contents

- [PDF Project Bootstrap](#pdf-project-bootstrap)
- [PDF Title Suppression](#pdf-title-suppression) — never use YAML `title:`
- [PDF Figure Rules](#pdf-figure-rules) — panel splitting, legends, date axes
- [LaTeX Max-Runs Warning](#latex-max-runs-warning) — `\needspace` sizing table
- [PDF Figure Sizing — Critical Patterns](#pdf-figure-sizing--critical-patterns) — the five root causes of tiny figures

## PDF Project Bootstrap

Use `epq scaffold` — it handles all of the following automatically:

```bash
epq scaffold ~/workspace/projects/my-project
cd ~/workspace/projects/my-project
just bootstrap    # runs: uv sync + ipykernel install + mkdir data/cache
```

Manual checklist (only if NOT using `epq scaffold`):
1. Create `pyproject.toml` with `[tool.uv] package = false` and run `uv sync`
2. Register kernel: `uv run python -m ipykernel install --user --name=<project>`
3. `_quarto.yml`: set `jupyter: <project>` (must match registered kernel name exactly)
4. Copy `latex-header.tex` locally from `~/src/analysis-doc/templates/` (do not reference it via external path)
5. Never borrow another project's venv or kernel — each project must own its own

## PDF Title Suppression

- **Never use YAML `title:` or `subtitle:`** — they produce `\maketitle` which double-renders with any custom header
- Use a raw LaTeX inline header in the document body instead:

```{=latex}
{\large\textbf{Document Title}}
\hfill
{\small\color{gray} Author \quad\textbullet\quad \today}
\vspace{4pt}
\hrule
\vspace{8pt}
```

- Add `pagetitle: " "` to YAML to suppress the HTML `<title>` without breaking Pandoc

## PDF Figure Rules

### Split multi-story panels
If a combined figure has two sub-panels telling different insights, split into separate `fig-*` cells with their own captions. Ask upfront whether panels should be split — this is cheaper than rework after the fact.

### Legend placement
- Top-right (`loc='upper right'`) when data occupies the bottom portion of the chart
- Below chart when dense: `fig.legend(loc='lower center', ncol=N, bbox_to_anchor=(0.5, -0.02))` + `fig.subplots_adjust(bottom=0.20)`
- Never place legend over data area

### Date axes — always explicit
Never rely on `AutoDateLocator` — it overcrowds on multi-year spans:

```python
ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
ax.tick_params(axis='x', labelsize=8)
```

### Never auto-open artifacts
Justfile render recipes must not include `&& open <file>`. The user opens files manually.

## LaTeX Max-Runs Warning

"WARN: maximum number of runs (9) reached" is **cosmetically harmless** when there are no `\ref{}` cross-references in prose. It is caused by `fancyhdr` + many figures creating layout oscillation. Mitigations:

- Use `\needspace` not `\clearpage` (see needspace sizing table in the `\needspace` section)
- Remove `labelformat=empty` from `\captionsetup` — caption numbering churn drives oscillation
- Use `htbp` float placement rather than forced `H`

`\needspace` sizing reference — X = figure height + 1.2in overhead:

| Figure height | `\needspace` |
|---|---|
| 3.2in | `\needspace{4.5in}` |
| 4.0in | `\needspace{5.2in}` |
| 5.5in | `\needspace{6.8in}` |
| Prose only | `\needspace{2.5in}` |

## PDF Figure Sizing — Critical Patterns

**CRITICAL: Matplotlib figure sizing in Quarto PDF output is failure-prone. Follow these rules exactly.**

### The Working Pattern (copy verbatim)

Every chart chunk that renders to PDF must have ALL of these chunk options:

```python
#| label: fig-my-chart
#| fig-pos: "H"          # force-here via float.sty — prevents deferral/stacking
#| fig-width: 6.5        # must match figsize width in Python code
#| fig-height: 3.5       # must match figsize height in Python code
#| out-width: 100%       # tells LaTeX to scale to full text column width
#| fig-cap: "Caption text with no bare % characters — write 'percent' instead."
```

And in the Python code:

```python
fig, ax = plt.subplots(figsize=(6.5, 3.5))  # must match chunk fig-width/fig-height
# ... chart code ...
plt.tight_layout()
plt.show()
plt.close('all')   # REQUIRED — prevents state leaking between chunks
```

### rcParams That Must Not Be Changed

```python
plt.rcParams.update({
    'savefig.bbox': None,        # fills declared figsize exactly — do NOT set to 'tight'
    'savefig.pad_inches': 0,
    'figure.dpi': 200,
    'savefig.dpi': 300,
})
```

**`savefig.bbox: None`** is counterintuitive but correct for PDF output. Setting it to `'tight'` causes matplotlib to auto-expand the canvas, which fights against the declared figsize and produces malformed figure PDFs.

### Root Causes of "Comically Small" Figures

These are the diagnosed failure modes, in order of frequency:

**1. Text labels extending beyond xlim/ylim — MOST COMMON**

```python
# ❌ BROKEN: annotation text positioned beyond axis limits
for bar, row in zip(bars, df.itertuples()):
    ax.text(bar.get_width() + 4, ..., f"{row.value}")  # +4 may push past xlim
ax.set_xlim(0, 380)  # text at bar.width+4 can exceed 380 → bbox explosion

# ✅ FIX: clip text labels to axes, OR increase xlim to accommodate labels
for bar, row in zip(bars, df.itertuples()):
    t = ax.text(bar.get_width() + 4, ..., f"{row.value}")
    t.set_clip_on(True)   # ← prevents bbox from expanding to include clipped text
# OR: ax.set_xlim(0, 420)  # ensure xlim accommodates largest label
```

When `ax.text()` labels are placed at `bar.get_width() + offset` in data coordinates and those labels extend beyond `xlim`, the PDF backend measures the full artist bounding box (including out-of-bounds text) when computing the figure's page size. This causes the figure PDF to be output at **half or less of the declared figsize** — which LaTeX then renders at postage-stamp size even though `out-width: 100%` is set.

**Rule:** After setting `xlim`, add `t.set_clip_on(True)` to ALL `ax.text()` calls, or add enough xlim headroom to fit the longest annotation.

**2. Mixed coordinate transforms on annotations**

```python
# ❌ BROKEN: mixes data coordinates with axis-fraction transform
ax.annotate("", xy=(x0, y0 + 3), xytext=(x1, y1 + 3), ...)  # data coords
ax.text(0.5, max_val + 9, "label", transform=ax.get_xaxis_transform())  # mixed!

# ✅ FIX: use pure axes fraction for floating annotations
ax.annotate("label text",
            xy=(0.5, 0.85), xycoords='axes fraction',
            ha='center', va='center', fontsize=9, ...)
```

`ax.get_xaxis_transform()` mixes x=axis-fraction with y=data coordinates. When the y-value in data coords exceeds ylim, the PDF backend's bounding box measurement goes pathological, producing figures that are 10-30× taller than declared. **Always use pure coordinate systems** — either all data coords or all `xycoords='axes fraction'`.

**3. Missing `plt.close('all')` between chunks**

Without `plt.close('all')` after each `plt.show()`, matplotlib figure state (transforms, layout engines, bounding boxes) leaks between Jupyter/Quarto execution chunks. This can cause later charts to inherit corrupt layout state from earlier ones. Always end every chart chunk with:

```python
plt.tight_layout()
plt.show()
plt.close('all')
```

**4. `fig-pos: "!ht"` instead of `"H"`**

`"!ht"` (try-here, then top-of-page) causes LaTeX to defer figures when there's insufficient space, stacking them at awkward positions. `"H"` (force-here via `float.sty`) places the figure exactly where declared. Requires `\usepackage{float}` in the LaTeX header.

**5. Missing `#| fig-width` / `#| fig-height` on chunk**

Without explicit chunk-level sizing, Quarto uses YAML defaults and may not pre-allocate the correct float box size before Python renders into it. Always specify both per-chunk.

### Diagnosing Figure Size Issues

To identify which figures are malformed without waiting for a full visual review:

```bash
# Add keep-tex to render temporarily
cd /path/to/doc && uv run quarto render doc.qmd --to pdf -M keep-tex:true

# Check actual page dimensions of each generated figure PDF
for f in doc_files/figure-pdf/*.pdf; do
  echo -n "$f: "
  pdfinfo "$f" 2>/dev/null | grep "Page size"
done

# A correct 6.5×3.5in figure should be ~468×252 pts (at 72 pts/in)
# A figure with width << 440 pts or height >> 400 pts is malformed
```

### The Nuclear Option

If a figure keeps rendering incorrectly despite all fixes, force PNG raster output:

```python
#| label: fig-problematic
#| fig-pos: "H"
#| dev: png            # ← bypass the PDF vector pipeline entirely
#| dpi: 150
#| fig-width: 6.5
#| fig-height: 3.5
#| out-width: 100%
```

PNG output is immune to all the bbox/transform issues because matplotlib renders to a fixed-size raster and Quarto embeds it directly. Use as a last resort since vector PDF is crisper.

### Caption Numbering

```latex
% Restore default numbering (Figure 1., Figure 2., etc.) with bold prefix:
\captionsetup{font={small,it},justification=centering,skip=6pt,labelfont=bf}

% Suppress numbering (caption text only, no "Figure N." prefix):
\captionsetup{font={small,it},justification=centering,skip=6pt,labelformat=empty,labelsep=none}
```

**Never use bare `%` in `fig-cap` strings** — write "percent" or "percentage points" instead. LaTeX may fail to compile depending on pandoc version.

### Reference Lines (axvline/axhline) Opacity

Reference lines (baselines, averages) should be visible context, not dominant elements. Always set `alpha=0.4`:

```python
ax.axvline(48.9, color=NAVY,  linestyle=":",  linewidth=1.6, alpha=0.4, label="Baseline", zorder=3)
ax.axhline(37.8, color=SLATE, linestyle="--", linewidth=1.4, alpha=0.4, label="Avg", zorder=3)
```

At `alpha=1.0` (default), reference lines dominate the chart and compete with the data bars. `alpha=0.4` keeps them readable without visual dominance.

---

