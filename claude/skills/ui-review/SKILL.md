---
name: ui-review
description: Review rendered web UIs against project layout rules and Josh's design preferences; capture screenshots, repair findings, and turn his feedback into reusable rules and approved references. Use for UI design, layout refinement, or explicit /ui-review requests.
---

# UI review

Use the `ui-review` CLI from Josh's dotfiles. If it is not on PATH, use
`~/.files/bin/ui-review`. Setup and rule types are documented in
`~/.files/docs/ui-review.md`. This supplements the project's design system.

## Design and verify

1. Identify the user's primary decision and the information needed to make it.
   Run `ui-review guidance --project <project>` and inspect relevant approved
   screenshots under `<project>/.ui-review/approved/` before designing.
2. If unconfigured, run `ui-review init --url <dev-url> --project <project>`.
   Set routes, representative viewport sizes, and a page-specific ready selector.
   Use stable application state and realistic data. Add a small set of relevant
   selector rules to `.ui-review/rules.json`; do not invent universal thresholds.
3. Implement the UI, run `ui-review check --project <project>`, and read the
   returned JSON plus every affected screenshot. Open the HTML report to compare
   with the last approved reference. A screenshot capture is not a visual review.
   Use the full-page image for hierarchy and open the detail tiles individually
   at original size for text, alignment, clipping, and chart labels. Read every
   tile covering the affected regions, including the right and bottom edges of
   large screens. A resized overview cannot establish detail quality. Report
   which page/viewport and tiles were reviewed; incomplete capture coverage fails.
4. Fix objective errors. Review hierarchy, comparison quality, legibility, chart
   truthfulness, and interaction states separately. DOM checks do not assess these
   reliably. Report concrete elements and measurements, never an arbitrary score.
5. Rerun affected checks after changes. Stop after three unsuccessful repair rounds
   and explain the remaining blocker with evidence. Do not weaken rules, remove
   failing selectors, disable enforcement, or approve screenshots merely to pass.

For an already scoped small edit, reuse the existing configuration and references.
Do not force every UI into a dashboard or add unrelated redesign work. The CLI
captures configured initial states; exercise relevant keyboard, loading, empty,
error, and interaction states through the project's browser tests as needed.

## Learn from Josh's feedback

When Josh says a design looks good or asks for an adjustment, preserve his actual
feedback against the exact report he viewed:

```sh
ui-review feedback --report <report.json> --decision approve --note '<his feedback>'
ui-review feedback --report <report.json> --decision adjust --note '<his feedback>'
```

Use shell-safe quoting or a subprocess argument array for notes. Approval copies
screenshots to the project's approved references; it does not waive automated
failures. Never record model self-approval as Josh's approval.

For measurable feedback, translate it into a rule JSON file and run:

```sh
ui-review learn --feedback <returned-id> --rule <rule.json>
```

Scope selectors and thresholds to the applicable page and viewport. Check the rule
against both the rejected layout and the accepted layout before calling it useful.
For subjective feedback, retain the note as guidance instead of manufacturing a
numeric proxy. "Looks good" alone approves that reference; it does not establish a
universal font size, spacing scale, or density target.

For density, use `region-density` with a meaningful `region` and content selectors.
Use `measure: text` to detect text diluted inside large containers; use `boxes`
for plots or other visual content whose outer area matters. These are geometric
proxies, not semantic information density or Tufte's data-ink ratio. Combine them
with required visible item counts and readable typography. Calibrate each screen
size against accepted examples; do not improve density by shrinking type or
padding the screen with irrelevant content. Check actual browser CSS viewport
dimensions, not the monitor's physical pixel count.

Default to project scope. When Josh explicitly makes a preference cross-project,
pass `--scope global` to both feedback and learn. Global entries live in
`~/.files/claude/ui-review/`; they retain notes/rules, not project screenshots.
Summarize the exact rule or preference change and its scope. Commit the intended
feedback/rules through the normal repository workflow, keeping private app data
and authentication state out of public dotfiles.

## Enforcement

The global Stop hook acts only where `.ui-review/config.json` enables
`enforceOnStop`. It checks the last result and source/rule freshness; it does not
launch a browser. A hook continuation is bounded, so use `ui-review check` in CI
for required gates. Explicit requests to configure enforcement authorize that
configuration; do not add extra approval steps.
