# Color as information architecture

Use color to help readers identify the kind of work, its recorded state, or
an actionable exception. Start with the decision the chart supports. A status
or health breakdown needs category meaning; painting every bar blue only
communicates quantity.

For EasyPost Looker dashboards, read the project's `docs/dashboard_style_guide.md`
and `schemas/easypost_palette.json` before editing. Use its actual EasyPost
collection values; do not copy an example's arbitrary red/blue/gray hex codes.

| Meaning | EasyPost color |
|---|---|
| Ordinary activity or quantity | Blue `#164DFF` |
| Reported complete/on track, resolved linkage | Green `#007357` |
| Reported blocked/off track, confirmed failure | Red `#FB5C59` |
| Risk, hold, or review needed | Amber `#AF640C` |
| Testing | Purple `#9F39EE` |
| Planning/coordination or waiting to start | Navy `#061340` |
| Go-live/support activity | Teal `#00E5AE` |
| Unknown, unavailable, unmapped | Slate `#47547F` |

Keep role mappings consistent within the dashboard. Category colors for teams
or unrelated identities carry no success/failure implication. Continuous magnitude
uses the sequential palette; a diverging scale needs a meaningful midpoint.
High counts or hours do not establish a problem. Numeric thresholds need units,
direction, boundaries, and a real target source.

Rankings should contain the entities or recorded categories named in their title.
Exclude missing identities, NULL/blank categories and non-entity placeholders:
`Customer not recorded` is not a customer, and NULL is not a Salesforce stage.
Filter the chart or table using a resolved entity key when available, and state
that it covers the recorded subset. Retain missing-entity rows in overall totals
and detail views. Show missingness in a coverage/completeness view when useful;
neutral color alone does not make a placeholder a valid member of an entity ranking.

Preserve readable category labels and values, with concise hover notes when color
meaning needs explanation. Do not use color as the only identifier. Source-reported
success is not independently verified completion; label that distinction.

In Looker, pin `series_labels` to the displayed series name, keep unknown categories
neutral through `series_colors`, and use `advanced_vis_config` point formatters
such as `name = Completed`. Store advanced configuration as a string of strict JSON,
never evaluate it. The project lint checks nested literal colors; it does not
prove selector behavior or rendering. Keep horizontal bars for long names.

For binary coverage (Yes/No, present/missing), prefer a single horizontal 100%
stacked bar with a fixed 0–100% scale and stable state order. Use one cohort row,
pivot the states, show both percentages, and retain counts in tooltip/Explore.
Filters define the denominator; unknown is separate from No, and an empty cohort
is no data. A two-slice pie is acceptable for an isolated part-to-whole view,
but the shared linear scale supports comparisons across cohorts or time.
Use green for confirmed presence and amber for absence needing review; red
requires a verified violation. Missing linkage does not prove missing work.

For many near-duplicate task names, group by a documented activity taxonomy before
coloring. Check both the default window and full history. Make first-match priorities
explicit: building a Test environment is delivery, not test execution. Keep mixed
tasks in one stated group; do not invent an allocation of their hours. Retain raw names
and signed entries in drill-down/detail, and reconcile grouped totals to ungrouped
totals. Keep unmapped work and missing tasks separate; negative net totals remain
neutral unless their business meaning is verified.

Exclude a generic `Other` category only when requested or justified by the chart's
decision. State that the chart shows the remaining subset and preserve whole-population
coverage elsewhere. Never silently remove unknown work from effort totals.

Looker's web UI requires the user's interactive SSO session. Use API checks for
configuration and query evidence; don't attempt automated navigation to
`analytics.easypost.com`. Ask for a rendered spot-check when needed. User approval of
an observed result can be recorded as feedback, but do not invent screenshots or a
Viewrule report to attach it to.
