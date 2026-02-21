#!/usr/bin/env python3
"""Screenshot specific figures from the rendered HTML for visual iteration.

Usage:
    /tmp/pw-venv/bin/python3 scripts/preview-fig.py [fig_id]

Setup (one-time):
    python3 -m venv /tmp/pw-venv
    /tmp/pw-venv/bin/pip install playwright
    /tmp/pw-venv/bin/playwright install chromium

fig_id options:
    fig1 .. figN    Quarto label ID (fig-your-label-name)
    all             Full page screenshot

Add entries to FIG_IDS to map short names (fig1, fig2, ...) to
your actual Quarto label IDs (fig-deal-flow, fig-revenue-waterfall, ...).
"""

import sys
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
DOC_STEM = "pre-read"  # ← change to your .qmd filename (without extension)

# Map short fig IDs to Quarto label IDs (the #| label: value in each cell).
# Add entries here as you add figures to your document.
FIG_IDS = {
    "fig1": "fig-situation",  # ← update these to match your actual labels
    "fig2": "fig-evidence",
    "fig3": "fig-dependencies",
    # "fig4": "fig-your-label",
    # "fig5": "fig-your-label",
}
# ─────────────────────────────────────────────────────────────────────────────

HTML = Path(__file__).parent.parent / f"{DOC_STEM}.html"
URL = f"file://{HTML.resolve()}"

fig_key = sys.argv[1] if len(sys.argv) > 1 else "fig1"
fig_name = FIG_IDS.get(fig_key, fig_key)  # allow raw Quarto label IDs too
out_path = f"/tmp/{DOC_STEM}-{fig_key}.png"

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    page.goto(URL)
    page.wait_for_load_state("networkidle")

    if fig_key == "all":
        page.screenshot(path=out_path, full_page=True)
    else:
        # Quarto wraps figures in <div id="fig-xxx"> or <figure id="fig-xxx">
        selector = f"#{fig_name}"
        el = page.locator(selector).first
        if el.count() == 0:
            print(
                f"Warning: selector {selector!r} not found, falling back to full page",
                file=sys.stderr,
            )
            page.screenshot(path=out_path, full_page=True)
        else:
            el.screenshot(path=out_path)

    browser.close()

print(f"✓ {out_path}")
