# Carrier comparison review

Reviewed at 1280 × 800 in Chromium. Primary task: compare eight carriers together.

Baseline: `.ui-review/runs/2026-09-12T14-13-31-732Z-45dafcae/` — 6 errors, 1 warning. Horizontal overflow was 244 px; no complete row boxes fit the initial viewport; header height was 450 px. Metric tops differed by 20 px and overlapped. Average cost lacked context and the service label clipped at 60 px.

Corrected: `.ui-review/runs/2026-09-12T14-14-35-639Z-654ae4cb/` — 0 errors, 0 warnings. All 7 existing rules and axe checks ran, with no accessibility items requiring review. Configuration, rules, and enforcement were preserved.

Manual review of both screenshots and the rendered corrected HTML report:

- Hierarchy: 62.6 px header, aligned summary ranges, then the comparison table. No oversized empty header.
- Comparison: eight 40 px rows span y=370.1–690.1. All fit together. Numeric columns align right and costs use two decimal places.
- Legibility: 14 px table values, restrained alternating rows, complete labels; horizontal overflow is 0 px.
- Quantitative integrity: ranges and spreads derive directly from the eight original row values. Removed unsupported aggregate/prior-period claims. Explicitly marks unavailable data context rather than inventing a baseline or denominator. There are no charts to assess.
- Interaction states: this static HTML has no interactive controls or loading/empty/error branches (0 buttons, links, inputs, selects, or textareas). Keyboard interaction testing is therefore not applicable. This review does not certify future interactive implementations.

Remaining limitations: only the configured 1280 × 800 desktop viewport was tested. No approved reference existed; no user approval or feedback was recorded. Fixture data lacks reporting dates, shipment counts, currency identity, cost basis, and service windows; the UI discloses this, and operational suitability remains unverified.

The runtime isolates loopback between shell invocations. Captures succeeded by running the local server and CLI in the same invocation; this is unrelated to application layout. Earlier connection-error runs are retained as evidence.
