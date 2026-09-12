# UI review

A small local UI quality tool: Playwright captures, deterministic layout rules,
axe accessibility checks, HTML/JSON reports, and a versioned feedback loop.
The Claude skill is `/ui-review`. Tufte-inspired guidance lives in
`claude/ui-review/preferences.json`; reusable executable rules live next to it.
Neither a passing run nor an approved screenshot proves a design is effective.

[Design rules](design-rules.md) defines the intended requirements for analytical
screens. It is the reference for the next detection and enforcement design;
the rules listed there are not all implemented by this tool.

## Setup and first review

Requires Node 22+, npm, and Python 3 (the portable symlink launcher).

```sh
cd ~/.files
make ui-review
# On a new machine, make claude links the existing Claude configuration and skills.
cd ~/src/my-app
ui-review init --url http://localhost:3000
# Edit .ui-review/config.json and .ui-review/rules.json; start your app normally.
ui-review check
```

`init` never replaces an existing configuration. The checker does not execute
application startup commands. It uses a fresh Chromium context for each capture.
For an authenticated local app, set `storageState` to a local Playwright state
file; `.ui-review/auth*.json` is ignored by the generated ignore file. Do not
commit authentication state. `UI_REVIEW_BROWSER_PATH` can select an already
installed Chromium executable. Screenshots remain local unless you commit/share
them deliberately.

To try the tool without an application, run `npm run demo --prefix
~/.files/share/ui-review`. It creates a temporary before/after comparison with
deliberately broken and corrected carrier tables and prints the HTML report path.
The example contains illustrative data and does not record user approval.

The check prints paths to `report.json` and `index.html`. Open the HTML report to
compare current captures with the last approved reference. Each finding includes
its rule, selector, observed value, expected value, and rationale. JSON also records
the evaluated rule IDs and axe checks requiring manual review. Exit codes:
`0` = no errors (warnings allowed), `1` = failed checks/capture, `2` = bad setup or
configuration. Missing/hidden required selectors and invalid rules fail explicitly.

## Project configuration

```json
{
  "version": 1,
  "baseURL": "http://localhost:3000",
  "enforceOnStop": false,
  "sourcePaths": ["src", "public", "package.json"],
  "accessibility": true,
  "pages": [{"name": "carriers", "path": "/carriers", "ready": "[data-testid=carrier-table]"}],
  "viewports": [
    {"name": "desktop", "width": 1440, "height": 900},
    {"name": "mobile", "width": 390, "height": 844}
  ]
}
```

Optional `timeoutMs` controls browser action/navigation timeouts (default 15000).
Use a ready selector that proves the intended data/state has loaded, not a generic
page shell or login page. Routes must stay on the configured origin. Animation is
disabled for captures; fonts are awaited. Supply deterministic fixture data when
comparing runs. Initial captures use light color scheme and reduced motion; this
first version does not model interaction sequences, themes, or other browsers.

`sourcePaths` are relative file/directory prefixes, not globs. They define freshness
coverage: include all files that can affect your UI and fixture data. Default `.`
covers Git-visible files; generated review output, dependencies, and build/cache
directories are excluded. Without Git, the checker walks the project with those
same exclusions. An external server's changing data cannot be detected by a source
hash: rerun captures when data or application state changes.

## Rules

Put an array in `.ui-review/rules.json`. Project rules override global rules by
exact `id`. All rules need `id`, `type`, `selector`, `severity` (`error` or
`warning`), and `reason`. Optional `pages`/`viewports` restrict applicability;
`optional: true` allows a selector to be absent. Keep optional rules for genuinely
optional components, not required evidence.

| Type | Extra fields | Meaning |
| --- | --- | --- |
| `align` | `edge`, `tolerance` | Maximum spread of left/right/top/bottom edges, in CSS pixels; select one peer group |
| `no-overlap` | — | Declared peers must not overlap; ancestor/descendant pairs are excluded |
| `no-clip` | — | Element's own hidden/clip overflow must not truncate content; does not inspect ancestor clipping |
| `visible-count` | `min` | At least this many complete element boxes fit in the initial viewport; does not detect occlusion |
| `max-height` | `max` | Maximum element height in CSS pixels, useful for task-specific density warnings |
| `style` | `property`, `allowed` | Approved computed CSS values (e.g., `font-size`, `["14px", "16px"]`) |
| `context` | `required` | Each matching component contains visible nonempty descendants for these selectors |
| `region-density` | `region`, `measure`, `minCoverage`, `maxVerticalGap` | Union coverage of selected content within the visible part of one region, plus its largest empty vertical band |

Page-level horizontal overflow and axe WCAG A/AA checks run independently of
selector rules. Intentional horizontal scrolling belongs inside a local container.
The checker cannot infer which elements should align, certify the meaning of metric
context, or inspect canvas chart scales. Those need explicit configuration and
visual/domain review. Zero custom rules means only overflow and accessibility are
covered; coverage is recorded in the JSON report.

Example (provisional values for one carrier screen, not global defaults):

```json
[
  {
    "id": "carrier-comparison-rows",
    "type": "visible-count",
    "selector": "[data-testid=carrier-table] tbody tr",
    "min": 8,
    "pages": ["carriers"],
    "viewports": ["desktop"],
    "severity": "error",
    "reason": "Compare eight carriers together without scrolling."
  }
]
```

## Feedback loop

Tell Claude or Codex: "This looks good; keep this as the reference", or "The
summary pushes the table down; I need eight complete rows on desktop."

```sh
ui-review feedback --report .ui-review/runs/RUN/report.json \
  --decision adjust --note 'Show eight complete carrier rows on desktop.'
# Returns a feedback ID. Put the concrete rule above (one object) into /tmp/row-rule.json.
ui-review learn --feedback FEEDBACK_ID --rule /tmp/row-rule.json
ui-review check
ui-review feedback --report .ui-review/runs/NEW_RUN/report.json \
  --decision approve --note 'This comparison layout works.'
```

`learn` validates the rule, requires recorded feedback, and preserves its
`feedbackId`. It never turns prose into thresholds automatically. The coding agent
does the translation, tests it, and explains the scope. Subjective notes remain
guidance via `ui-review guidance` and the report. Approval preserves that exact
run's images under `.ui-review/approved/`; it never clears failing checks. The
next report shows the most recent approved run's matching page/viewport images.
There is no pixel-difference gate in this version.

## Large screens and assessment fidelity

New configs include 1440×900, 1920×1080, 2560×1440, 3840×2160, and 390×844.
These are **CSS viewport dimensions**, not monitor hardware resolutions. Replace
them with your actual browser sizes as needed. Existing configs are preserved.

Every page also produces overlapping detail PNGs at one image pixel per CSS pixel,
defaulting to 1024×800 with at least 64px overlap. Use the overview for composition and
open individual tiles at original size for labels, type, and alignment. The HTML
report preserves each tile's width in a scrollable container instead of shrinking
it. The JSON manifest records coordinates, dimensions, expected/captured counts,
and coverage. The program verifies capture coverage; an agent or person still
has to inspect the images. A passing geometry check does not certify that review.

Optional capture limits:

```json
"detailCapture": {"width": 1000, "height": 800, "overlap": 64, "maxTiles": 64}
```

Exceeding `maxTiles` produces an error with the missing capture count; it never
silently declares the page fully captured. Narrow a very long page's fixture state
or deliberately raise the limit. This captures the document surface, not hidden
scroll-container content or interaction states. Keep those in separate app tests.

For density, `region-density` clips to the intersection of the region and the
initial viewport, and unions rectangles so nested/overlapping elements don't
inflate coverage. `measure: "text"` uses rendered text line rectangles;
`measure: "boxes"` uses selected element bounding boxes (useful for plot areas).
Neither measures semantic relevance or actual data ink. Select content, not whole
dashboard containers. Ancestor clipping and occlusion still require visual review.
Reports include coverage, selected element count per 100,000 CSS px², and largest
vertical gap. Element counts depend on selector granularity; compare the same
selectors across runs. Do not trade away legibility to improve a density metric.
Use the reserved region `"viewport"` to measure the whole visible screen, including
space outside a fixed-width content wrapper. Use a CSS selector for one workspace
region. A tightly fitted wrapper cannot reveal unused space outside itself.

Example only—calibrate these thresholds against an accepted large-screen layout:

```json
{
  "id": "comparison-workspace-use",
  "type": "region-density",
  "region": "viewport",
  "selector": "[data-testid=metric-value], [data-testid=carrier-table] td",
  "measure": "text",
  "minCoverage": 0.04,
  "maxVerticalGap": 200,
  "viewports": ["large", "4k"],
  "severity": "error",
  "reason": "Keep comparison evidence visible and avoid large unused bands."
}
```

These are proposed geometric constraints, not universal Tufte rules. Add the
visible-row and type-scale checks appropriate to the task; a screen can satisfy
coverage while communicating poorly.

Use `--scope global` on both feedback and learn only for deliberately reusable
preferences. Global notes/rules live in dotfiles; project notes, configuration,
rules, and approved references stay with the project. Review before committing
screenshots, particularly in public repos. Commit rules and notes you want to
reuse; `.ui-review/runs/` and `latest.json` are disposable and ignored.

## Claude and CI enforcement

The dotfiles Stop hook does nothing unless the current project has enabled
`enforceOnStop: true`. It requires a passing result with a matching fingerprint
of configured source files, local/global rules, and checker implementation. It
does not run a browser on every stop. Claude's `stop_hook_active` continuation is
allowed through to avoid loops; report unresolved errors honestly. This is an
iteration aid, not an unbypassable enforcement boundary.

For a required merge gate, install the pinned dependencies, install Chromium,
start the app with fixtures, and run `ui-review check` in CI. Preserve the run
directory as an artifact on failure. This repository's `ui-review.yml` exercises
one representative CLI regression workflow on Linux.

## Development

```sh
npm ci --prefix share/ui-review
npm exec --prefix share/ui-review -- playwright install chromium
npm test --prefix share/ui-review
```

Keep one regression test for the UI review workflow: a sparse 4K page fails,
feedback becomes a rule, the repaired page passes with full-resolution details,
and a later source change invalidates that pass. Improve this detector when a
regression occurs instead of adding a helper or edge-case test matrix.
Use concrete rejected/accepted examples to calibrate new rules. Do not promote a
rule because it passes only the example used to invent it.

References: [Tufte](https://www.edwardtufte.com/book/the-visual-display-of-quantitative-information/),
[Playwright accessibility](https://playwright.dev/docs/accessibility-testing),
[Claude hooks](https://code.claude.com/docs/en/hooks-guide).
