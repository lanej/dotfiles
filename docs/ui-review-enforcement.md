# Detecting and enforcing design rules

The [design rules](design-rules.md) define the intended outcomes. `ui-review`
checks configured, observable conditions and cites the relevant rule IDs in its
HTML report, JSON output, and Stop-hook findings. Each run preserves a local
design-rule reference and its source hash so the cited text stays with the report.

## Coverage and evidence

| Design rule | Available detection | What still needs judgment or integration |
| --- | --- | --- |
| [DR-001](design-rules.md#dr-001--comparable-charts-use-comparable-scales) — Comparable scales | `consistent` checks declared units, periods, domains, transformations, and computed plot dimensions for a comparison identity. | The app must expose metadata from its actual renderer configuration. Equality of attributes cannot prove the drawn scales are correct or the comparison appropriate. |
| [DR-002](design-rules.md#dr-002--visual-magnitude-reflects-numerical-magnitude) — Proportional magnitude | `attribute` checks explicit baseline, area-encoding, or projection declarations. | Actual mark-to-value proportionality requires the renderer and data; generic DOM checks do not measure canvas marks or validate the underlying quantities. |
| [DR-003](design-rules.md#dr-003--quantities-carry-the-context-needed-to-interpret-them) — Context | `context` requires visible, nonempty labels within the declared component or shared group. | The source, denominator, period, and baseline must actually describe the data. |
| [DR-004](design-rules.md#dr-004--missing-and-estimated-values-remain-distinguishable) — Missing/estimated values | `context` can require labels on elements the app identifies as estimates, forecasts, or missing values. | Detection of null-to-zero coercion, undeclared interpolation, or fabricated uncertainty requires data integration. |
| [DR-005](design-rules.md#dr-005--visual-meanings-stay-consistent) — Consistent meanings | `consistent` compares computed colors/styles and declared symbols by stable identity, within the same page and across viewports. | The identity and semantics must be correct. Theme and interaction-state comparisons are not implemented. |
| [DR-006](design-rules.md#dr-006--related-evidence-stays-visible-together) — Simultaneous comparison | `comparison-set`, alignment, overlap, clipping, and visible-count checks. | Decide which alternatives and relationships matter; geometry alone cannot select the task. |
| [DR-007](design-rules.md#dr-007--larger-screens-expose-useful-detail-and-preserve-legibility) — Larger screens | `comparison-set` preserves identities, requires configured counts and readable type, plus density and full-resolution capture checks. | Useful additional information and comfortable reading still require visual review. |
| [DR-008](design-rules.md#dr-008--decoration-earns-its-space-and-visual-weight) — Decoration | Scoped `max-height` and `style` checks can limit headers, shadows, borders, and other known sources of clutter. | Whether a boundary, label, or control earns its place is a design judgment; start these checks as warnings. |

Each page/viewport lists all eight IDs as `checks-passed`, `findings`, or
`unassessed`. `checks-passed` means the configured conditions passed; it does not
certify the complete requirement. Optional selectors with no visible matches
remain unassessed. An unavailable capture cannot establish coverage.

## Project requirements

Keep routes, readiness selectors, and viewports in `.ui-review/config.json`.
Choose representative CSS viewport sizes and stable data for the same page state.
Add a coverage requirement when a design rule must have executed evidence:

```json
"requiredDesignRules": ["DR-001", "DR-003", "DR-006", "DR-007"]
```

This fails the check if any configured page/viewport has no executed check with
visible evidence for a required ID. It prevents an absent or skipped check from
satisfying the gate. It does not transform a partial check into proof of the
whole design rule. Scope the configured pages/states to the evidence you require.

In `.ui-review/rules.json`, `severity: "error"` blocks a pass; `"warning"`
reports a concern without blocking. Cite `designRules` explicitly when a check
serves a different requirement from its default type mapping. Attribute checks
always require an explicit citation. Unknown IDs and unknown check fields fail
configuration validation.

## Preserve comparisons across viewports

Give each selected observation a stable identity generated from the underlying
entity and measure. Repeated elements with the same identity count only once.

```html
<tr data-comparison="carrier-a">...</tr>
```

Example rule for a fixture with at least twelve relevant alternatives. The
counts and type size below are illustrative project choices, not global defaults:

```json
{
  "id": "carrier-comparison",
  "type": "comparison-set",
  "selector": "tbody tr",
  "keyAttribute": "data-comparison",
  "requiredKeys": ["carrier-a", "carrier-b"],
  "preserveFrom": "desktop",
  "minVisibleByViewport": {"desktop": 8, "4k": 12},
  "minFontSize": 14,
  "viewports": ["desktop", "4k"],
  "designRules": ["DR-006", "DR-007"],
  "severity": "error",
  "reason": "Keep the primary alternatives together and expose more at 4K."
}
```

The check requires complete boxes inside the initial viewport and their clipping
ancestors, counts distinct identities, and checks the text sizes inside each
selected element. At viewports at least as wide and tall as `preserveFrom`, it
also requires every identity visible in the reference to remain visible. The
reference must be among the check's active captures; each active viewport needs
a count. It does not detect every form of occlusion, CSS transform scaling, or
text drawn in canvas. Use clipping/accessibility checks and inspect detail tiles.

## Compare renderer metadata and styles

An app can expose its real configuration on the chart container. Generate these
attributes from the same values passed to the renderer; independently maintained
annotations would provide weak evidence. This example compares magnitudes:

```html
<figure data-comparison-group="carrier-cost"
        data-unit="USD/parcel" data-period="2026-08"
        data-y-domain="[0,10]" data-y-scale="linear">...</figure>
```

```json
{
  "id": "carrier-cost-scales",
  "type": "consistent",
  "selector": "[data-comparison-group='carrier-cost']",
  "keyAttribute": "data-comparison-group",
  "properties": ["width", "height"],
  "attributes": ["data-unit", "data-period", "data-y-domain", "data-y-scale"],
  "designRules": ["DR-001"],
  "severity": "error",
  "reason": "Comparable cost plots share units, periods, scales, and dimensions."
}
```

Use the actual plot-area element if the outer container includes variable labels
or margins. Values are compared as strings, so serialize metadata consistently.
Dimensions in this example must match across active captures too; scope the rule
to one viewport or omit them when intentional resizing preserves interpretation.
For DR-005, use an entity identity with properties such as `color`, `fill`, or
`stroke` and attributes for symbols; choose properties actually used by the mark.

An `attribute` rule can require a declared bar baseline:

```json
{
  "id": "amount-bar-baseline",
  "type": "attribute",
  "selector": "[data-chart-kind='amount-bar']",
  "attribute": "data-y-min",
  "allowed": ["0"],
  "designRules": ["DR-002"],
  "severity": "error",
  "reason": "Ordinary amount bars use a zero baseline."
}
```

For DR-004, scope `context` to actual estimated/forecast elements, require their
visible explanatory labels, and cite `"designRules": ["DR-004"]`. This checks
the presentation of declared states; data correctness remains unassessed.

## Enforcement and repair

`ui-review check` returns 0 when configured error checks pass, 1 for detected
failures, and 2 for configuration/setup errors. A required CI job can gate a
merge on that exit code. Warnings and unrequired unassessed rules stay visible.
Required coverage, missing required selectors, incomplete captures, and stale
source/configuration/policy evidence cannot satisfy the corresponding gate.

The opt-in Stop hook requires a current passing review and includes up to five
blocking findings with their design IDs and report path. It retains its bounded
continuation behavior; it is an iteration aid rather than an unbypassable gate.
Code, rules, and the design-rule document participate in freshness checks.

Findings include page, viewport, selector, measured and expected values, the
design-rule citation, and a suggested next action. A coding agent can use this
feedback to repair the application and rerun the same check. There is no
autonomous repair command or automatic source edit. Never fix a result by changing
metadata independently of the renderer, removing comparison identities, or
weakening requirements. Intentional policy adjustments belong in the feedback
and rule-review workflow.

The regression detector remains one representative CLI workflow. It exercises
the broken and repaired responsive comparison, cited findings, feedback
promotion, capture evidence, and stale-result blocking.
