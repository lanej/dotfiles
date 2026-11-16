# Visual and interaction evidence

Evaluate the actual interface against the decision it supports and the project's design system. Viewrule findings can expose geometric problems, but they do not replace visual judgment. Review hierarchy, comparison quality, legibility, chart truthfulness, and interaction states separately; report concrete elements and observations rather than an arbitrary score.

## Color and grouping

Use color to communicate category, recorded state, or an actionable exception. Quantity alone does not imply warning or failure. Category colors for unrelated identities carry no success/failure meaning. Continuous magnitude uses an appropriate sequential scale; a diverging scale needs a meaningful midpoint. Preserve distinctions among unknown, unavailable, and confirmed healthy state. Read the project's actual palette and category definitions rather than importing a different organization's example colors.

## Density and inspection

Scope selectors and thresholds to the applicable page and viewport. Calibrate measurable rules against accepted and rejected examples; preserve subjective feedback as guidance instead of manufacturing numeric proxies. An approval applies to the reviewed reference, not a universal font size or density target.

For density checks, select a meaningful region and its content. Text measurements can expose text diluted inside large containers; box measurements can suit plots or visual content. These are geometric proxies, not semantic information density or Tufte's data-ink ratio. Combine them with relevant visible content and readable typography. Do not improve a metric by shrinking text or padding a screen with irrelevant content. Check actual CSS viewport dimensions rather than physical monitor pixels.

Inspect full-page hierarchy and detailed regions at original or otherwise readable scale. Cover affected right and bottom edges as well as the initial viewport. Report incomplete capture coverage instead of implying it was reviewed.

## Interaction coverage and retained behavior

Static route captures do not establish collapse/expand, hover, focus, open/closed, loading, error, or recovery behavior. Exercise states relevant to the change. Where retained consequential behavior warrants protection, add a focused persistent browser test through the real interaction instead of repeating ad hoc pixel measurements on every future edit. Keep the test proportional; do not require a full application harness for an unrelated wrapper or discarded experiment.

If the project uses Viewrule, use its configured reports and approved references alongside the project's browser tests. A successful verify command checks existing evidence at that boundary; it does not establish coverage of every interaction state or a successful live deployment. Diagnose a capture or runtime failure before treating it as a design finding.
