---
name: qmd-math
description: Math notation conventions for Quarto/EPQ documents rendered via lualatex. Use when: writing or adding a formula, equation, or mathematical expression to a .qmd file; asked about display math, inline math, or LaTeX notation in a QMD/Quarto context; defining a where-clause or variable definitions for an equation; converting prose variable descriptions into structured math notation; fixing math that renders badly in a PDF; using \lvert, \begin{aligned}, \tfrac, \text{where}, or any LaTeX math command in a Quarto document. Triggers on: "write a formula", "add an equation", "math notation", "where clause", "display math", "LaTeX equation", "define variables", "simplify the formula", "typeset this".
---

# qmd-math — Math Notation in Quarto/lualatex

## Core Rule: Display Math for Non-Trivial Equations

Use `$$...$$` display blocks for any equation with more than one operation. Inline `$...$` is for single-symbol references in prose only.

```markdown
<!-- WRONG — hard to scan, subscript stacking mangles copy-paste from PDF -->
The formula is $\text{NRE}_f = \frac{r_i}{8} \cdot \frac{5}{7} \sum_{\text{seg}} \frac{\Delta t_{\text{seg}}}{\lvert\mathcal{F}_{\text{seg},i}\rvert}$ where ...

<!-- CORRECT — opening and closing $$ each on their own line -->
$$
\text{NRE}_f = \frac{r_i}{8} \cdot \frac{5}{7} \sum_{\text{seg}} \frac{\Delta t_{\text{seg}}}{\lvert\mathcal{F}_{\text{seg},i}\rvert}
$$
```

## Where-Clause Pattern

**Preferred: inline `\text{where}` with `\begin{aligned}`** — keeps definitions inside the math block, aligned at `=`, no list markup needed. Use when definitions are short phrases.

```latex
$$
\text{NRE}_f = \frac{r_i}{8} \cdot \frac{5}{7} \sum_{\text{seg}} \frac{\Delta t_{\text{seg}}}{\lvert\mathcal{F}_{\text{seg},i}\rvert}
\quad \text{where} \quad
\begin{aligned}
  r_i/8 &= \text{assignee hourly rate (daily rate} \div 8\text{)} \\
  \Delta t_{\text{seg}} &= \text{wall-clock hours in segment} \\
  \lvert\mathcal{F}_{\text{seg},i}\rvert &= \text{distinct carrier families active in that segment} \\
  5/7 &= \text{wall-clock to business-day conversion}
\end{aligned}
$$
```

This renders as: equation left · "where" center · aligned definitions right. No overflow on a 6.5in text block if definitions stay under ~40 chars. Verified in lualatex/scrartcl letter.

**Fallback: bulleted list** — use when definitions are long phrases that would overflow inline.

```markdown
$$
\text{NRE}_f = \frac{r_i}{8} \cdot \frac{5}{7} \sum_{\text{seg}} \frac{\Delta t_{\text{seg}}}{\lvert\mathcal{F}_{\text{seg},i}\rvert}
$$

where:

- $r_i / 8$ — assignee hourly rate (daily rate ÷ 8 hours)
- $\Delta t_{\text{seg}}$ — wall-clock hours in sweep segment
- $\lvert\mathcal{F}_{\text{seg},i}\rvert$ — distinct carrier families with open pre-first-label tickets in that segment
- $5/7$ — wall-clock to business-day conversion
```

Each bullet: symbol (inline math) — plain-English definition. One line per term. No nesting.

**Never**: run-on prose embedding symbols — `where $\Delta t$ is the wall-clock hours... $\lvert\mathcal{F}\rvert$ is the count...`

## Repeated Formulas

When a second formula shares terms with a previous one, use a two-row `\begin{aligned}` where-block: one row for the new term, one back-reference row for the shared terms.

```latex
$$
C_{\text{maint},f} = \frac{r_i}{8} \cdot \frac{5}{7} \sum_{\text{seg} \geq t_{0,f}} \frac{\Delta t_{\text{seg}}}{\lvert\mathcal{F}_{\text{seg},i}\rvert}
\quad \text{where} \quad
\begin{aligned}
  t_{0,f} &= \text{first label date for carrier family } f \\
  r_i/8,\, \Delta t_{\text{seg}},\, \lvert\mathcal{F}_{\text{seg},i}\rvert &= \text{as defined above}
\end{aligned}
$$
```

## Sub-Formulas in the Where-Block

When a where-term is itself derived from other quantities, define it with a formula row — don't flatten it to prose. Use `\tfrac` (text-fraction) instead of `\frac` for compact inline fractions within an aligned block, and add the secondary definition on the same row after a `\quad`:

```latex
$$
\text{NRE}_f = w_i \sum_{\text{seg}} \frac{\Delta t_{\text{seg}}}{\lvert\mathcal{F}_{\text{seg},i}\rvert}
\quad \text{where} \quad
\begin{aligned}
  w_i &= \tfrac{5 r_i}{56}, \quad r_i = \text{assignee daily rate} \\
  \Delta t_{\text{seg}} &= \text{wall-clock hours in segment} \\
  \lvert\mathcal{F}_{\text{seg},i}\rvert &= \text{distinct carrier families active in that segment}
\end{aligned}
$$
```

When a second formula reuses a named term (`w_i`), the where-block only needs to define what's new — everything else is already established:

```latex
$$
C_{\text{maint},f} = w_i \sum_{\text{seg} \geq t_{0,f}} \frac{\Delta t_{\text{seg}}}{\lvert\mathcal{F}_{\text{seg},i}\rvert}
\quad \text{where} \quad
t_{0,f} = \text{first label date for carrier family } f
$$
```

Single-term where-clauses don't need `\begin{aligned}` — inline `\quad \text{where} \quad term = definition` is sufficient.

## epq Audit Gotcha: `\texttt` Inside Math Blocks

The epq audit flags `\texttt{...}` anywhere in QMD source, including inside `$$` blocks. Use `\mathtt{...}` for monospace in math mode, or just `\text{...}` (non-monospace). Better: avoid font commands in math entirely and reference the variable symbol instead.

## Delimiters: `\lvert\rvert` Over `|...|`

For absolute value and set cardinality, always use `\lvert...\rvert`. The bare `|` is a fixed-height fence — it mismatches tall fractions.

```latex
<!-- WRONG — bars don't scale with the fraction -->
|\mathcal{F}_{\text{seg},i}|

<!-- CORRECT — scales to match the numerator/denominator height -->
\lvert\mathcal{F}_{\text{seg},i}\rvert
```

## Subscript Formatting

- **Label subscripts** (words, abbreviations): wrap in `\text{}` — `_{\text{seg}}`, `_{\text{maint}}`. Unwrapped subscripts render as italicized variable sequences (`seg` → `s·e·g`).
- **Index subscripts** (single-letter variables): no wrapping — `_i`, `_f`.
- **Set names**: use `\mathcal{}` — `\mathcal{F}` for a set of families.

## Inline Math in lualatex Prose — What Works and What Breaks

**Safe in prose** (renders correctly):
- Variable references: `$\Delta t_{\text{seg}}$`, `$r_i$`, `$5/7$`
- Inline fractions: `$r_i / 8$`
- `$\div$`, `$\times$` operators
- Comparison: `$4\times$` (e.g., "capped at $4\times$")

**Breaks in lualatex prose** (renders as literal dollar signs or garbles):
- `$\geq$`, `$\leq$` — use Unicode `≥`, `≤` or plain English ("at least", "no more than")
- `$\to$`, `$\rightarrow$` — use `→` (Unicode) or plain arrow prose

**Safe Unicode in lualatex prose** (Latin Modern font supports these):
`≥ ≤ ≠ ≈ → ÷`

**Unsafe Unicode** (not in Latin Modern, will fail):
`× ` (multiplication sign U+00D7) — write "times" or use `$\times$` in math mode only.

## Checklist Before Committing Math

- [ ] Non-trivial equation in `$$...$$` display block (opening and closing `$$` on their own lines)
- [ ] Multi-variable equation has a where-clause (`\begin{aligned}` preferred; bulleted list as fallback for long definitions)
- [ ] Cardinality/absolute value uses `\lvert...\rvert` not `|...|`
- [ ] Label subscripts wrapped in `\text{}`
- [ ] No `$\geq$` / `$\leq$` in prose — Unicode or plain English instead
- [ ] Rendered PDF inspected — subscripts readable, fractions not cramped
