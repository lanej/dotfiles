# EPQ Figure Modules

## Figure Module Contract

Each figure module defines a typed `Data` dataclass — the explicit contract between
the QMD data-load cell and the figure. The QMD constructs the dataclass; `render()`
receives it. No untyped dict access inside `render()`. No fallback/sample data.

```python
# figures/fig_revenue.py
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from epq import style, fmt

LABEL = "fig-revenue"    # matches QMD #| label: fig-revenue
FIG_WIDTH = 8.5
FIG_HEIGHT = 4.0
FIG_CAP = "Insight-focused caption — not a data description."


@dataclass
class Data:
    """Typed input for render(). Lists every field this figure consumes."""
    records: list[dict[str, Any]]
    total: float  # example scalar — add only what render() needs


def render(data: Data) -> None:
    """Called from QMD stub. Do NOT call plt.show/savefig/close here."""
    import matplotlib.pyplot as plt
    import pandas as pd
    style.apply_style()
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    df = pd.DataFrame(data.records)
    # ... all viz code ...
    plt.tight_layout()


if __name__ == "__main__":
    """Dev loop — saves to {project}_files/figure-pdf/{LABEL}-output-1.png."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from epq import cache

    cached = cache.read_cache("my_query")
    if cached is None:
        raise RuntimeError("Cache miss — run scripts/data/extract_my_query.py first")

    fig_data = Data(
        records=cached["records"],
        total=cached["scalars"]["total"],
    )

    _project_root = Path(__file__).parent.parent
    _out_dir = _project_root / f"{_project_root.name}_files" / "figure-pdf"
    _out_dir.mkdir(parents=True, exist_ok=True)
    out = str(_out_dir / f"{LABEL}-output-1.png")

    render(fig_data)
    plt.savefig(out, dpi=150, bbox_inches="tight")    # savefig BEFORE close
    print(f"Saved {out}")
    plt.close("all")
```

**Never:** `_load_sample_data`, `render({})`, hardcoded rows, or any synthetic fallback.
Cache miss → `RuntimeError`. Always.

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
fig_revenue.render(fig_revenue.Data(records=data["my_query"], total=total_revenue))
```

## Visual Checklist

Inspect the PNG after every `just dev-fig <name>` run. Never rely on code review alone.

- [ ] `\needspace` present BEFORE the section heading (not after, not between prose and figure)
- [ ] `\needspace` value ≥ fig-height + 2.5 (more for multi-paragraph sections)
- [ ] Section heading is on the same page as its figure
- [ ] No prose paragraph appears alone on a page without its figure
- [ ] `suptitle(y=1.0)` not `y=1.02` (clips in PDF)
- [ ] All text readable without zooming (>1.5× zoom = illegible at print scale)
- [ ] 3-panel figures: `FIG_HEIGHT ≥ 4.0`
- [ ] Dark fills (NAVY/TEAL/CORAL/PURPLE/GOLD) → WHITE text
- [ ] Pale fills (LIGHT_BG, LIGHT_SLATE) → NAVY text (SLATE fails contrast)
- [ ] Bar labels within xlim — `set_clip_on(True)` makes them invisible
- [ ] `plt.savefig()` called before `plt.close()` (wrong order = blank PNG)
