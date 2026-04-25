# EPQ Whitespace Control (`\needspace`)

**Core principle: section + intro prose + figure = atomic unit.**

If the unit cannot fit on the current page, it must start clean at the top of the next
page. Never let heading, prose, and figure split across pages. A clean page break is
always better than any partial fit.

## Placement

`\needspace` must appear **BEFORE the section heading** — not after it, and not between
prose and figure.

```markdown
\needspace{8.0in}

## Section Heading

One or two sentences of intro prose that set up the figure.

```{python}
#| label: fig-name
#| fig-height: 4.0
#| fig-pos: "H"
...
```
```

## Sizing Formula

`\needspace{(FIG_HEIGHT + prose_lines + heading)in}`

- Heading alone: ~0.5in
- Each prose paragraph: ~0.75–1.0in
- Figure: `FIG_HEIGHT`in
- Caption + buffer: ~0.5in

**When in doubt, go larger.** A slightly early page break leaves a small white gap.
Prose and figures on separate pages is always worse.

## Practical Reference

| Section contents | needspace value |
|---|---|
| Heading + 1 prose para + 3.0in fig | `\needspace{5.5in}` |
| Heading + 1 prose para + 4.0in fig | `\needspace{6.5in}` |
| Heading + 2 prose paras + 4.0in fig | `\needspace{8.0in}` |
| Heading + 3+ prose paras + 4.0in fig | `\needspace{9.0in}` |
| Heading + 1 prose para + 5.0in fig | `\needspace{7.5in}` |

## Rules (all three required)

1. BEFORE the section heading — not after it
2. BEFORE the intro prose — not between prose and figure
3. Value large enough to cover heading + all prose + figure + caption

**Never `\newpage` before a figure** — use `\needspace` (soft break, not forced).
**Never `\clearpage`** — always forces a break and flushes all floats.

`latex-header.tex` sets `\floatplacement{figure}{H}` globally — figures default to
hard placement. Individual cells can opt out with `#| fig-pos: "htbp"`.
