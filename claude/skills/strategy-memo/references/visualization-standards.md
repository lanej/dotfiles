# Visualization Standards — Strategy Memo

Everything here is distilled from `pre-read.qmd`. The patterns work for PDF output via lualatex + Quarto.

## Color Palette

Define once in the setup cell. Reference constants in all figure cells — never hardcode hex.

```python
NAVY       = '#1e3a5f'   # Primary: dominant bars, trend lines, headings
TEAL       = '#0d9488'   # Secondary: growth, positive movement, platform
CORAL      = '#e63946'   # Accent: problems, losses, urgency, primary call-out
SLATE      = '#475569'   # Body text, axis labels, secondary annotations
LIGHT_SLATE = '#94a3b8'  # Axis lines, gridlines, de-emphasized data
GOLD       = '#d97706'   # Third stream, warnings, carrier monetization
WHITE      = '#ffffff'
LIGHT_BG   = '#f8fafc'
```

**Semantic use:**
- CORAL for the "bad" thing (losses, threats, the problem)
- TEAL for the "good" thing (recovery, growth, the solution)
- NAVY for structural/neutral dominant elements
- GOLD for a third stream that is neither good nor bad
- LIGHT_SLATE for anything the reader should see but not focus on

## Required rcParams (setup cell)

```python
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica Neue', 'Arial', 'DejaVu Sans'],
    'font.size': 9,
    'axes.titlesize': 10,
    'axes.titleweight': 'bold',
    'axes.labelsize': 8,
    'axes.labelcolor': SLATE,
    'axes.edgecolor': LIGHT_SLATE,
    'axes.linewidth': 0.5,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'xtick.color': SLATE,
    'ytick.color': SLATE,
    'figure.dpi': 200,
    'savefig.dpi': 300,
    'savefig.bbox': None,        # CRITICAL: fills declared figsize exactly
    'savefig.pad_inches': 0,     # do NOT set to 'tight' — causes PDF size issues
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': False,
    'figure.facecolor': WHITE,
    'axes.facecolor': WHITE,
})
```

## Required Cell Options (every figure cell)

```python
#| label: fig-my-chart      # prefix fig- always
#| fig-cap: "Insight-focused caption — what should the reader conclude?"
#| fig-height: 4.0          # must match figsize height in Python code
#| fig-width: 6.5           # must match figsize width in Python code
#| fig-pos: "H"             # force-here via float.sty (requires \usepackage{float})
#| out-width: 100%          # tells LaTeX to scale to full text column width
```

And in the Python code, match the figsize exactly:

```python
fig, ax = plt.subplots(figsize=(6.5, 4.0))   # must match chunk fig-width/fig-height
# ... chart code ...
plt.tight_layout()
plt.show()
plt.close('all')   # REQUIRED — prevents state leaking between chunks
```

## Figure Size Reference

| Figure type | fig-height | fig-width | Notes |
|---|---|---|---|
| Standard figure | 4.0 | 6.5 | Default for most charts |
| Compact figure | 3.2–3.5 | 6.5 | Two-panel or summary charts |
| Wide figure | 4.5 | 6.5 | Sankey, timeline, spine diagrams |
| Full-page figure | 5.5 | 6.5 | Use sparingly — eats prose space |

## Caption Standard

Captions explain the **insight**, not the data:

```python
# ✅ GOOD: tells the reader what to conclude
#| fig-cap: "Lost deal flow (2024+). The dominant flow: customers who evaluated EasyPost and stayed put — not competitive losses."

# ❌ BAD: describes what the chart is, not what it means
#| fig-cap: "Sankey diagram showing deal flow by loss reason and destination."
```

**Captions cannot use `{python}` expressions** (Quarto limitation). If a caption contains a number that may change, add a sync comment in the cell:

```python
# CAPTION-SYNC: ratio={ratio:.0f} — update caption if this value changes
#| fig-cap: "...approximately 4× more spread revenue than SaaS revenue."
```

**Never use bare `%` in captions** — write "percent" or "pct". LaTeX may fail to compile.

## PDF Figure Sizing — Failure Modes

These are the diagnosed causes of "comically small" figures in PDF output, in order of frequency.

### 0. Multi-metric comparison: use separate panels, not dual y-axes (most common design error)

When comparing 3+ categories across 2+ metrics, the instinct is a dual-axis chart (error bars + latency line on the same subplot). **Do not do this in PDF output.** Two annotation layers (error % labels above bars, latency ms labels above line markers) will collide at PDF scale, especially at 4+ categories where x-axis labels also compete for space.

```python
# ❌ BROKEN: dual y-axis with two annotation layers at 4 categories
ax2_r = ax2.twinx()
for i, (e, l) in enumerate(zip(error_pcts, latency_ms)):
    ax2.text(i, e + 0.08, f'{e}%', ...)   # error label
    ax2_r.text(i, l + 3, f'{l}ms', ...)   # latency label — collides

# ✅ CORRECT: 3 separate panels, one metric each
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(6.5, 3.0))
# ax1: volume bars (NAVY)
# ax2: error rate bars (CORAL for outlier, LIGHT_SLATE for others)
# ax3: latency bars (CORAL for outlier, LIGHT_SLATE for others)
fig.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.18, wspace=0.50)
```

**Outlier highlighting:** color the single worst bar CORAL, leave others LIGHT_SLATE. The comparison is immediately readable without competing value labels. Only label the values — don't also label the series name.

**Short x-axis labels:** use 4–8 char abbreviations at 4+ categories. `'GW-A\nAuth'` not `'Gateway A\n(Auth Platform)'`. Parenthetical sub-labels on two-line ticks crowd against each other and overlap neighboring bars at fontsize 7–8.

### 1. Text labels beyond xlim/ylim (most common)

```python
# ❌ BROKEN: annotation text positioned beyond axis limits
for bar in bars:
    ax.text(bar.get_width() + 4, ..., f"${val:.0f}M")
ax.set_xlim(0, 80)   # text at bar.width+4 can exceed 80 → bbox explosion

# ✅ FIX: clip all text labels
for bar in bars:
    t = ax.text(bar.get_width() + 4, ..., f"${val:.0f}M")
    t.set_clip_on(True)
# OR: ax.set_xlim(0, 95)  — add enough headroom for the longest label
```

When `ax.text()` labels extend beyond `xlim`, the PDF backend measures the full artist bounding box. The figure renders at half-size even though `out-width: 100%` is set.

**Rule:** After setting xlim, add `t.set_clip_on(True)` to ALL `ax.text()` calls, or add headroom.

### 2. Mixed coordinate transforms

```python
# ❌ BROKEN: mixes data coordinates with axis-fraction transform
ax.text(0.5, max_val + 9, "label", transform=ax.get_xaxis_transform())

# ✅ FIX: use pure axes fraction for floating annotations
ax.text(0.5, 0.85, "label", transform=ax.transAxes,
        ha='center', va='center')
```

`ax.get_xaxis_transform()` mixes x=axis-fraction with y=data coordinates. When y exceeds ylim, the bounding box measurement goes pathological.

### 3. Missing `plt.close('all')`

Without `plt.close('all')` after each `plt.show()`, figure state leaks between Quarto execution chunks. End every chart chunk with:

```python
plt.tight_layout()
plt.show()
plt.close('all')
```

### 4. `fig-pos: "!ht"` instead of `"H"`

`"!ht"` defers figures when space is tight, stacking them awkwardly. `"H"` forces placement exactly where declared. Requires `\usepackage{float}` in YAML header.

### 5. Nuclear option: force PNG raster

If a figure keeps failing despite all fixes:

```python
#| label: fig-problematic
#| dev: png       # bypass PDF vector pipeline entirely
#| dpi: 150
#| fig-pos: "H"
#| fig-width: 6.5
#| fig-height: 3.5
#| out-width: 100%
```

PNG output is immune to all bbox/transform issues. Less crisp than vector PDF but guaranteed to work.

## Chart Patterns

### Sankey / Flow diagram

Custom Bezier implementation — no library needed (pre-read.qmd has the full pattern):

```python
from matplotlib.patches import PathPatch
from matplotlib.path import Path

def bezier_flow(ax, x0, y0, h0, x1, y1, h1, color, alpha=0.5):
    """S-curve Bezier flow between two nodes."""
    cx = (x0 + x1) / 2
    verts_top    = [(x0 + nw, y0 + h0/2), (cx, y0 + h0/2), (cx, y1 + h1/2), (x1 - nw, y1 + h1/2)]
    verts_bottom = [(x1 - nw, y1 - h1/2), (cx, y1 - h1/2), (cx, y0 - h0/2), (x0 + nw, y0 - h0/2)]
    codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
             Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.CLOSEPOLY]
    verts = verts_top + verts_bottom + [verts_top[0]]
    ax.add_patch(PathPatch(Path(verts, codes), facecolor=color, edgecolor='none', alpha=alpha))
```

### Waterfall chart

```python
# YoY delta waterfall: positive bars in full color, negative in faded alpha
def plot_stream(ax, x, values, color, bottom_pos, bottom_neg, label):
    pos = np.where(values > 0, values, 0)
    neg = np.where(values < 0, values, 0)
    if pos.any():
        ax.bar(x, pos, width=w, color=color, alpha=1.0, bottom=bottom_pos, label=label)
    if neg.any():
        ax.bar(x, neg, width=w, color=color, alpha=0.35, bottom=bottom_neg)
    return bottom_pos + pos, bottom_neg + neg
```

### Two-panel figure

```python
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.5, 3.2),
                                gridspec_kw={'width_ratios': [1, 1.5]})
# Remove spines on both axes
for ax in [ax1, ax2]:
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
```

### Reference lines

Always set `alpha=0.4` — reference lines should be visible but not dominate:

```python
ax.axhline(baseline, color=LIGHT_SLATE, lw=0.8, alpha=0.4, zorder=1)
ax.axvline(event_x, color=SLATE, lw=1.2, ls='--', alpha=0.4, label='Event')
```

## Caption Numbering (LaTeX)

Default (Figure N. prefix, bold):
```latex
\captionsetup{font={small,it},justification=centering,skip=6pt,labelfont=bf}
```

Suppress numbering (caption text only):
```latex
\captionsetup{font={small,it},justification=centering,skip=6pt,labelformat=empty,labelsep=none}
```

Set in the YAML `include-in-header` block.

## Chart Selection Guide

| Situation | Chart type | Notes |
|---|---|---|
| Deal/money/customer flow | Sankey (custom Bezier) | Makes dominant flows visually unmistakable |
| YoY delta by revenue stream | Waterfall (stacked bar + net line) | Full color positive, faded negative |
| Growth over time + forecast | Bar (actuals) + line (trend + CI band) | Log-linear fit if CAGR > 15% |
| Composition by customer segment | Stacked bar, quarterly | intelligence_gap at bottom (easiest to track) |
| Customer count by cohort | Line chart, symlog y-axis | Handles wide range across cohorts |
| Two related metrics side by side | Two-panel (1:1.5 width ratio) | |
| Capability or architecture diagram | Custom `FancyBboxPatch` + arrows | No Mermaid in PDF — use matplotlib directly |
| Rate shopping / accuracy data | Line chart per carrier, monthly | Carriers as separate series |
