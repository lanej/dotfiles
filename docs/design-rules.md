# Design rules for analytical UIs

Help the reader make accurate comparisons and understand the evidence behind a
decision. Use available space to reveal useful information while preserving
legibility and context.

These are our application of Edward Tufte's *The Visual Display of Quantitative
Information*, supplemented by his later writing. They are design requirements
for quantitative screens, not quotations or universal rules for every interface.

This file defines the intended behavior. [Detection and enforcement](ui-review-enforcement.md)
describes the implemented checks and their limits; listing a rule here does not
mean the tool checks every part of it. See [UI review](ui-review.md) for setup.

## How to apply the rules

- **Must** defines a requirement when the stated condition applies.
- **Should** defines a default that calls for judgment in the particular screen.
- A **comparison group** is a set of values or charts the reader is expected to
  compare for one task. Its membership and intended comparison must be explicit.
- Scope requirements to the task, page state, comparison group, and viewport.
  There is no universal density percentage, row count, or font size.
- Document an exception with its rule ID, scope, reason, and how it preserves the
  intended comparison. A disclosure cannot make a misleading encoding accurate.

## DR-001 — Comparable charts use comparable scales

**Requirement:** Charts comparing absolute magnitudes of the same measure must
use the same units, axis domains, scale transformations, and plotting dimensions.
Time comparisons must use matching windows or explicitly labeled corresponding
periods. Changes in layout must preserve the interpretation of the scale.

**Why:** Visual differences should reflect differences in data. Independently
rescaling each panel can make very different magnitudes appear equivalent.

**Exception:** Separate scales may support comparison of patterns within each
series. Label those scales clearly and identify the comparison as one of shape
or relative change. Logarithmic and indexed views must identify their transform
and reference value.

## DR-002 — Visual magnitude reflects numerical magnitude

**Requirement:** Ordinary bars representing amounts must start at zero. Filled
area charts representing amounts must preserve a zero baseline. Bubble area
must be proportional to its encoded value. Decorative 3D projections must not
distort a two-dimensional quantitative comparison.

**Why:** The size of the visual mark must represent the quantity faithfully.

**Exception:** Range bars and timelines represent intervals; their endpoints must
represent those intervals accurately. Unfilled line and scatter plots may use
nonzero domains to reveal variation. Actual three-dimensional data may justify
a three-dimensional view. Axis labels must make the chosen mapping clear.

## DR-003 — Quantities carry the context needed to interpret them

**Requirement:** A quantitative claim must identify its measure, units, applicable
period, and population or scope. Rates must identify their denominator;
performance comparisons must identify their baseline. Currency must be
unambiguous. Source information must be accessible, with freshness stated when
it affects the decision.

**Why:** A precise-looking number can still be uninterpretable or incomparable.

**Application:** Put essential context beside the value or in a clearly shared
heading. Do not hide essential units or periods exclusively in hover content.
Shared context can cover a whole table or chart group; repeating it in every
cell adds noise. Detailed source documentation may be expandable.

## DR-004 — Missing and estimated values remain distinguishable

**Requirement:** Missing, unavailable, and suppressed values must remain distinct
from observed zero. Forecasts, estimates, and measured values must be visibly
distinguishable. Disclose interpolation across missing observations and material
omissions or truncation. Show supplied uncertainty when it affects interpretation.

**Why:** A continuous line or an apparently complete table must not imply evidence
that does not exist.

**Application:** A gap or labeled missing value is valid. Connecting observations
across a gap requires an explicit indication that intervening values are missing.
Do not invent an uncertainty interval when the underlying data provides none.

## DR-005 — Visual meanings stay consistent

**Requirement:** Within a comparison workspace, the same entity or status must
retain its color, symbol, and line-style meaning across charts, filters, sorting,
and viewport changes. Different meanings must not silently reuse an established
encoding. Essential distinctions must remain understandable without color alone.

**Why:** Relearning a visual vocabulary consumes attention and invites incorrect
comparisons.

**Exception:** Theme or accessibility changes may alter the palette while
preserving the mapping and an identifiable label or other distinguishing mark.
An explicitly different encoding, such as coloring carriers by risk instead of
identity, must be explained where that encoding is used.

## DR-006 — Related evidence stays visible together

**Requirement:** For each task, identify the critical comparison set. At its
supported analytical desktop sizes, the screen must show that set together in
the declared comparison view. Align related values and use consistent numeric
formatting so the reader can scan them. Keep labels close to their evidence.

**Why:** Comparing alternatives should not depend on remembering a value from
another tab or a previous scroll position.

**Application:** A carrier-selection view might require cost, delivery window,
and reliability for the selected alternatives together. Secondary detail may be
expandable. Small screens may use an explicit selection or comparison mode;
the reduced view must keep the identity and context of each alternative clear.

## DR-007 — Larger screens expose useful detail and preserve legibility

**Requirement:** For the same task and data state, moving to a larger supported
viewport must preserve the critical comparison set. Where additional evidence
helps the task, define which extra rows, columns, time history, or comparison
panels become visible at larger sizes. Preserve readable type and interaction
targets as density changes.

**Why:** Additional screen area is an opportunity to improve comparison and
inspection. Stretching containers alone does not demonstrate that improvement.

**Application:** Judge density by useful, distinct observations and relationships.
Repeated values, larger cards, and decorative marks do not count as additional
evidence. A larger carrier table might expose volume and service breakdowns while
keeping cost and reliability visible. Do not increase density by shrinking text
below the project's readable type scale.

**Exception:** A finite comparison or focused task may already show all useful
evidence. Retain useful whitespace and bounded reading widths in that case;
do not manufacture content to meet an occupancy target.

**Review:** Assess both the whole layout and detail at its intended reading size
for every target viewport. A reduced overview alone cannot establish legibility
on a large screen. Viewport dimensions refer to CSS pixels; account for browser
zoom and display scaling when choosing representative screen sizes.

## DR-008 — Decoration earns its space and visual weight

**Default:** Remove redundant frames, nested cards, repeated labels, ornamental
icons, and effects that compete with the evidence. Gridlines and separators
should support reading without dominating the data. Headers and controls should
leave room for the task's primary comparisons.

**Why:** Prominent visual elements should communicate relevant information.

**Exception:** Grouping, selection, warnings, and interaction affordances may
need visible boundaries or emphasis. Preserve these functions. Minimal decoration
is not a reason to erase useful labels, context, or controls.

**Review:** Treat excessive decoration as a design concern requiring judgment.
An empty screen is not automatically a successful reduction of non-data ink.

## Refining the rules

Use feedback on concrete screens to refine a rule or add a scoped example.
Record what decision became easier or harder and at which viewport. Preserve the
rule IDs so future detection and enforcement can refer to the same requirements.
Appearance approval alone does not establish numerical or graphical accuracy.

## Sources

- Edward Tufte, [The Visual Display of Quantitative Information](https://www.edwardtufte.com/book/the-visual-display-of-quantitative-information/): graphical integrity, data-ink, high-resolution displays, and small multiples.
- Edward Tufte, [Baseline for amount scale](https://www.edwardtufte.com/notebook/baseline-for-amount-scale/): why time-series axes need not always include zero.
- Edward Tufte, [Sparkline theory and practice](https://www.edwardtufte.com/notebook/sparkline-theory-and-practice-edward-tufte/): later discussion of context, simultaneous comparison, resolution, and unnecessary frames.
- Edward Tufte, [Making better inferences from statistical graphics](https://www.edwardtufte.com/notebook/making-better-inferences-from-statistical-graphics-edward-tufte/): later guidance on documenting sources and analytical choices.
- Carl Bergstrom and Jevin West, [The principle of proportional ink](https://www.callingbull.org/tools/tools_proportional_ink.html): an operational interpretation of proportional graphical representation.
