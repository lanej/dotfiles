# Diagram geometry and series consistency

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
