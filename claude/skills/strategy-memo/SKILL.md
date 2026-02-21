---
name: strategy-memo
description: Create Amazon 6-pager-style data-backed strategy memos as Quarto documents (QMD → PDF). Use when asked to write a strategy pre-read, leadership memo, director briefing, executive narrative report, or any data-driven document following Amazon 6-pager conventions. Provides: an interview-then-scaffold workflow, a complete template QMD with caching/visualization/LaTeX patterns already wired, and supporting build tooling (Justfile, figure preview, cache validation). Auto-load when user says "strategy memo", "pre-read", "6-pager", "director briefing", "leadership document", "data-backed narrative", or "strategy document".
---

# Strategy Memo Skill

Produces Amazon 6-pager-style strategy memos as Quarto documents that render to publication-quality PDF (+ HTML). The canonical reference is `pre-read.qmd` in the `intelligence-strategy-sessions` project — everything in this skill is distilled from that document.

## Workflow

### Step 1: Interview the user

Before generating anything, ask these questions (all at once, numbered):

1. **Company & domain** — What company/team is this for? What domain (product strategy, platform investment, org change, technical direction)?
2. **Audience** — Who reads this? (e.g., Engineering + Product Directors, Board, VP-level)
3. **Leadership framework** — How should intent be framed? (Intent-Based Leadership = "I intend to…"; OKR-driven; DACI; or neutral)
4. **Strategic thesis** — In one sentence: what is the central argument or direction you are asserting?
5. **Key questions** — What are the 3–5 strategic choices the document must help the audience decide or validate?
6. **Data sources** — BigQuery project + key table names? Or will data be provided manually / hardcoded?
7. **Target length** — 6 pages is the Amazon canon. More than 8 pages is too long regardless of figures.
8. **Tone** — Urgent inflection point? Confident direction-setting? Diagnostic + open questions?

### Step 2: Generate the scaffold

Once you have answers, generate a new `.qmd` file by adapting `assets/template.qmd`:

- Replace all `{{PLACEHOLDER}}` tokens with content derived from the interview
- For each **key question**, create a `## Part N: ...` section with prose and a figure cell stub
- For each **data source**, create a cache block in the key-numbers cell (cache-read-or-query pattern)
- Set `\fancyhead` values (company name, document title, author)
- Populate the intent declarations from the thesis and questions
- Leave figure cells as stubs with `# TODO: implement visualization` comments

### Step 3: Set up the project

Copy the supporting assets into the project root:

```bash
cp assets/Justfile ./Justfile
cp assets/scripts/preview-fig.py ./scripts/preview-fig.py
cp assets/scripts/validate-cache.py ./scripts/validate-cache.py
mkdir -p data/cache scripts
```

Add to `.gitignore`:
```
data/cache/
.drive-file-id
.jupyter_cache/
```

For Google Drive sync, create `.drive-file-id` containing the Drive file ID of the target PDF.

### Step 4: Build loop

```bash
just render          # Full render: PDF + HTML + check + sync to Drive
just preview         # HTML only, opens in browser (fast)
just preview-fig fig1  # Screenshot a single figure (~15s, no full render)
just check           # Scan PDF for unrendered Python literals
just delete-cache    # Wipe data/cache/ — forces live BigQuery re-query
just validate        # Compare cache to live BigQuery (fails if drift > 5%)
```

## Core Authoring Rules

See `references/6pager-spec.md` for document structure and writing style.
See `references/visualization-standards.md` for figure patterns, color palette, and anti-patterns.

### No hardcoded numbers in prose (strict)

Every factual number must flow from a Python variable:

```markdown
Analysis of `{python} f"{total_deals:,}"` lost opportunities...
```

Never: `Analysis of 847 lost opportunities...`

Numbers that CAN be hardcoded: stylistic/non-factual values ("25 minutes of silent reading").

### Cache-read-or-query pattern (mandatory for BigQuery)

```python
_c = _read_cache('my_dataset')
if _c:
    df = pd.DataFrame(_c['records'])
    my_scalar = float(_c['scalars']['my_scalar'])
else:
    df = run_bq_query(my_query)
    my_scalar = float(df['col'].values[0])
    _write_cache('my_dataset', df.to_dict(orient='records'), {
        'my_scalar': my_scalar,
    })
```

**Never:** `except Exception: my_scalar = 42` — silent fallback masks broken queries.

### Figure captions: insight, not description

```python
#| fig-cap: "Lost deal flow (2024+). The dominant flow: customers who evaluated and stayed put."
```

Not: `#| fig-cap: "Sankey diagram of deal flow by loss reason."`

### LaTeX in PDF output

```latex
\begin{quote}
\small\itshape
"Customer quote here."

\upshape---Attribution, Date
\end{quote}
```

Escape dollars: `\$110M`. Em-dashes: `---` (renders as —). Page breaks: `\newpage`.

### Figure captions cannot use `{python}` expressions

Quarto limitation. Add a sync comment adjacent to any hardcoded caption value:
```python
# CAPTION-SYNC: ratio={ratio:.0f} — update caption if ratio changes
#| fig-cap: "...approximately 4×..."
```

## Document Structure

The proven 4-part structure from `pre-read.qmd`:

1. **Introduction** — Intent declarations (3 statements of "I intend to…") + "How These Sessions Work"
2. **Part 1: The Situation** — Diagnosis, primary visualization, customer/evidence quote
3. **Part 2: Why This Intent** — Strategic rationale, data moat, revenue/product evidence
4. **Part 3: What This Requires** — Technical, organizational, and execution dependencies
5. **Part 4: Questions to Refine Intent** — Exactly 3–5 strategic choices, not action items

**Never add:** self-blame tone, tactical product details, "Risks and Mitigations" framing, top-down action items, more than 5 strategic choices, appendices, bullet points in narrative prose.

## Pre-flight Audit Checklist

Before `just publish`, scan for:

- [ ] `int(N)` literals inside `{python}` inline expressions (literal masquerading as variable)
- [ ] Numbers assigned in `if _c:` blocks without a preceding `run_bq_query()` call
- [ ] Dollar amounts in LaTeX attribution blocks with no Python variable reference
- [ ] Percentages written as words ("Seventy-three percent") with no `{python}` backing
- [ ] Figure captions containing bare `%` characters (LaTeX compile failure)
- [ ] `text labels beyond xlim` in matplotlib (causes comically small PDF figures)
- [ ] Missing `plt.close('all')` after each figure cell
