---
name: matplotlib
description: Figure engineering patterns, gotchas, and reusable helpers for matplotlib. Use when directly building standalone figure scripts, diagram generators, or canvas visuals outside the epq render pipeline — e.g., generate_layer_icons.py, vision project banners, morning-brief charts, competitive analysis figures. Covers shape boundary math, arrow/edge geometry, series consistency, font registration, zorder, Unicode rendering, and canvas clipping. Distinct from the epq skill (which covers the Quarto/LaTeX analysis pipeline). Load alongside epq when figure work involves both the pipeline and standalone diagram construction.
---

## Gotchas

**`ax.text()` does not accept `set_clip_on` as a kwarg**: Pass it after the fact — `t = ax.text(...); t.set_clip_on(True)`. Passing as a keyword argument raises a TypeError silently or is ignored depending on matplotlib version.

**Unicode arrows `↑↓→` (U+2191/U+2193/U+2192) do not render**: They appear as boxes or missing glyphs in matplotlib via Helvetica Neue or any lualatex-rendered font. Use ASCII `+`/`-`/`>` instead. Safe Unicode in prose and annotations: `≥ ≤ ≠ ≈` only.

**`$` in f-strings gets consumed as LaTeX math**: Inside any matplotlib text that passes through a LaTeX renderer, `f"${val:.1f}M"` renders a math-mode dollar sign, not a literal one. Escape with `\\$`: `f"\\${val:.1f}M"`.

**`plt.savefig()` must be called before `plt.close()`**: Calling `plt.close("all")` first produces a blank/white PNG with no error. Canonical `__main__` pattern:
```python
render({})
plt.savefig(out, dpi=150, bbox_inches="tight")
plt.close("all")
```
The `plt.close` intercept pattern (overriding `plt.close` to prevent premature closing) is obsolete — do not use it. The `render()` function should never call `plt.show()` or `plt.close()`; those are the caller's responsibility.

**Always read the output PNG before reporting done**: After any `plt.savefig()` / `uv run python script.py`, use the Read tool on the generated PNG and inspect before declaring done. Check: (1) color-on-color invisibility — white icon on white background is invisible; (2) arrow/line clipping through icons — an icon centered at an arrow origin means the arrow runs through the icon; (3) stale visual artifacts from removed elements. Do NOT report "done" until the image has been visually inspected.

**`bbox_inches="tight"` breaks series consistency**: `tight` trims each figure to its content bounds independently, producing different output dimensions across figures with different content extents. For a series that must be identical pixel dimensions, use `fig.subplots_adjust(left=0, right=1, top=1, bottom=0)` to fill the full figure area and omit `bbox_inches` entirely: `fig.savefig(path, dpi=N, facecolor=bg)`.

**Font family name after `addfont()` differs from filename**: `font_manager.fontManager.addfont(path)` registers a font using its internal family name. `"IBMPlexMono-Regular.ttf"` registers as `"IBM Plex Mono"`, not `"IBMPlexMono"`. Verify before use: `from matplotlib import font_manager as fm; fm.FontProperties(fname=path).get_name()`. Using the wrong name silently falls back to the default font.

**`FancyBboxPatch round,pad=rad` extends beyond the specified rect**: `FancyBboxPatch((cx-w/2, cy-h/2), w, h, boxstyle="round,pad=rad")` draws a shape whose OUTER boundary extends `rad` units beyond the specified rect on all sides — actual extents are `(cx ± w/2 ± rad, cy ± h/2 ± rad)`. Placing a box near a canvas edge silently clips the rounded corners without error. Before drawing, verify `cy + h/2 + rad ≤ YM` and `cy - h/2 - rad ≥ 0` (and equivalent for x). Reduce `h`, `w`, or `rad` if clipping is possible. The bug is invisible in code and shows as flat/angled corners in the PNG.

## Diagram Patterns

**Geometric edge attachment for arrows**: Hardcoded offsets for arrow endpoints drift inside or outside shape borders as layouts change. Compute intersection points from shape geometry instead:
```python
def rect_edge(cx, cy, w, h, rad, tx, ty):
    """Outer AABB boundary of rounded rect toward (tx, ty)."""
    dx, dy = tx - cx, ty - cy
    dist = np.hypot(dx, dy)
    if dist < 1e-9: return cx, cy
    nx, ny = dx / dist, dy / dist
    ax, ay = w / 2 + rad, h / 2 + rad
    t = min(ax / abs(nx) if abs(nx) > 1e-9 else np.inf,
            ay / abs(ny) if abs(ny) > 1e-9 else np.inf)
    return cx + t * nx, cy + t * ny

def circ_edge(cx, cy, r, tx, ty):
    """Circle boundary toward (tx, ty)."""
    dx, dy = tx - cx, ty - cy
    dist = np.hypot(dx, dy)
    if dist < 1e-9: return cx + r, cy
    return cx + r * dx / dist, cy + r * dy / dist
```
Usage: `s = rect_edge(src_cx, src_cy, src_w, src_h, src_rad, dst_cx, dst_cy)` for the arrow tail; `e = rect_edge(dst_cx, ...)` for the arrowhead. Then `arr(ax, *s, *e, ...)`. For a filled destination box (opaque fc), draw the box first at lower zorder, then the arrow at higher zorder so the arrowhead is visible at the boundary.

**Diagram series consistency — anchor shared elements to module-level constants**: Any element that must appear at the same position, size, or style across all frames in a series (e.g., N layer banners) must be defined as a module-level constant before the per-frame functions. Without this, per-function choices drift independently and realignment requires user correction. Pattern:
```python
EP_X_STD = 6.20              # shared x-center across all frames
EP_W, EP_H, EP_RAD = 1.9, 1.05, 0.12  # shared size and pad

def ep_box(ax, cx, cy, ...):  # single drawing function used by all frames
    rr(ax, cx, cy, EP_W, EP_H, ...)
```
Any element the user might compare side-by-side across frames — position, size, stroke weight, color — should be a named constant, not a per-function literal.

**Icon semantic value — don't annotate what the shape already communicates**: Before placing an icon, ask whether it adds information not already conveyed by the shape's position, grouping, or context. Carrier dots in a fan pattern already communicate "carriers" — a van icon beside one dot reads as "one carrier is a van," not "these are carriers." Reserve icons for: (a) distinguishing actor type when ambiguous (e.g., shipper vs. carrier card in a bilateral layout), (b) labeling a resolved output state with no other visual identity, (c) providing a group label when the group has no enclosing shape. When in doubt, omit.
