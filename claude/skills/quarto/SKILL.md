---
name: quarto
description: Render computational documents to markdown (DEFAULT), PDF, HTML, Word, and presentations using Quarto. PREFER markdown output for composability. Use for static reports, multi-format publishing, scientific documents with citations/cross-references, or exporting Jupyter notebooks. Triggers on "render markdown", "render PDF", "publish document", "create presentation", "quarto render", or multi-format publishing needs.
---

# Quarto Skill

Quarto is an open-source scientific and technical publishing system built on Pandoc. It renders computational documents (with Python, R, Julia code) to publication-quality output in multiple formats.

## Best Practices (TL;DR)

1. **Markdown-First**: Default to `format: gfm` with `wrap: none` for composability, portability, and archival
2. **No Line Wrapping**: Always use `wrap: none` for GFM output (avoids artificial line breaks)
3. **Dark Mode**: Always use `auto-dark` filter with dual themes for HTML output (accessibility and modern UX)
4. **Visual Expression**: Use charts and formatted tables, NEVER raw data dumps (`df.head()`, `print(dict)`)
5. **LaTeX for Math**: Use LaTeX notation for ALL mathematical expressions ($\alpha = 0.15$, not "alpha = 0.15")
6. **Professional Tables**: Use LaTeX tables (booktabs) for PDF, Great Tables for HTML
7. **No TOC**: Table of contents is usually noise - use clear section headings instead
8. **PDF for Sharing**: Use `--to pdf` for Google Drive sharing (read-only, professional)
9. **Blank Lines Before Lists**: ALWAYS include a blank line before every list (bullet or numbered) - no exceptions
10. **No Appendix for Sources**: Data sources belong in code blocks, not appendix - only add external sources not directly referenced in code to appendix
11. **Use Markdown() Class**: ALWAYS use `Markdown()` for text output in code blocks - NEVER use `print()` or `printf()` (output must render as formatted markdown)

## Visual Expression Philosophy

**CRITICAL: Quarto documents are for COMMUNICATION, not raw data dumps.**

Quarto outputs are static documents meant to convey insights to humans. Raw dataframes, print statements, and JSON blobs fail to communicate effectively.

### Visual Hierarchy (Use in Order)

1. **Charts/Plots** - For trends, distributions, comparisons, relationships
2. **Formatted Tables** - For structured data with styling and context
3. **Formatted Metrics** - For key numbers with context and formatting
4. **Raw Output** - NEVER (not even for debugging - use separate analysis files)

### Anti-Patterns: What NOT to Do

```python
# ❌ BAD: Raw dataframe dump
df.head()

# ❌ BAD: Print statements - output renders as plain text, not formatted markdown
print(f"Total: {total}")
print(data_dict)

# ❌ BAD: printf/print for text - use Markdown() instead
print("## Summary\n- Item 1\n- Item 2")  # Renders as plain text!

# ❌ BAD: Bare variable returning data structure
result  # Returns raw dict/JSON

# ❌ BAD: DataFrame info without formatting
df.describe()
df.info()

# ✅ GOOD: Use Markdown() for ALL text output
from IPython.display import Markdown
Markdown(f"""
## Summary

- **Total**: {total:,}
- **Average**: {avg:.2f}
""")
```

```markdown
❌ BAD: Plain text for mathematical notation
- The growth rate is alpha = 0.15 or 15%
- We calculated the mean mu = sum(xi)/n
- The correlation coefficient r = 0.85

❌ BAD: No table formatting
```python
print(df.head())
```

❌ BAD: Using asterisks for equations
- E = m * c^2
- y = beta0 + beta1 * x
```

### Good Patterns: Visual Communication

```python
# ✅ GOOD: Chart for trends
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))
df.groupby('date')['sales'].sum().plot(ax=ax, kind='line')
ax.set_title('Sales Trend Over Time')
ax.set_ylabel('Sales ($)')
plt.tight_layout()
plt.show()

# ✅ GOOD: Formatted table using Great Tables
from great_tables import GT

(GT(df.head(10))
    .tab_header(title="Top 10 Sales Records")
    .fmt_currency(columns="sales", currency="USD")
    .fmt_date(columns="date", date_style="medium"))

# ✅ GOOD: Formatted table using pandas markdown
from IPython.display import Markdown
Markdown(df.head(10).to_markdown(index=False, tablefmt='pipe'))

# ✅ GOOD: Formatted metrics in markdown with LaTeX
from IPython.display import Markdown

Markdown(f"""
## Key Metrics

- **Total Sales**: ${total_sales:,.2f}
- **Average Order**: ${avg_order:,.2f}
- **Growth Rate**: $\\alpha = {growth_rate:.1%}$ (15% YoY)
- **Top Product**: {top_product}

### Statistical Summary

The linear regression model $y = \\beta_0 + \\beta_1 x + \\epsilon$ yielded:

- Slope: $\\hat{{\\beta_1}} = 3.2$ (SE = 0.4)
- $R^2 = 0.78$, indicating strong fit
""")

# NOTE: Mermaid diagrams must use native Quarto syntax outside Python blocks
# Use ```{mermaid} directly in markdown, NOT inside Markdown() calls
```

### Why Visual Expression Matters

- **Documents are for humans**: Show insights, not data structures
- **Static format**: No interactive exploration - must communicate clearly on first view
- **Traceable reasoning**: Visualize fact→conclusion chains, not raw JSON
- **Professional output**: Charts and tables look polished in PDF/HTML/Word
- **Accessibility**: Visual hierarchy helps readers navigate content
- **Shareability**: Well-formatted outputs communicate without explanation

## Narrative Structure

**Build understanding progressively through a series of sections:**

### Document Flow

1. **Abstract** - The punchline first (executive summary for busy readers)
2. **Key Findings** - Scannable bullet points with confidence levels
3. **Base Facts** - Individual observations/data, each in its own section
4. **Synthesis Sections** - Combine earlier facts into higher-level insights
5. **Conclusion** - Final synthesis referencing the insights above

### Base Facts (Individual Sections)

Each base fact is an independent observation with its own data and evidence. Use descriptive headers (not "Fact 1"):

```qmd
## Response Time Distribution

\needspace{3in}

Analysis of the past 7 days shows significant tail latency:
- p50: 45ms
- p95: 230ms  
- p99: 890ms (concerning)

```{python}
#| echo: false
# Chart showing latency distribution
```
```

### Synthesis Sections

Synthesis sections **explicitly reference** which earlier sections they build upon:

```qmd
## Performance Degradation Under Load

\needspace{4in}

Building on the response time distribution and traffic patterns above, we 
observe a clear correlation: p99 latency spikes to 2.3s during the 2-4pm 
peak traffic window. The system handles baseline load well but degrades 
significantly under peak conditions.
```

### Keeping Content Together (PDF)

Use `\needspace{Xin}` before sections with charts/diagrams to prevent awkward page breaks and large whitespace gaps:

```qmd
## Revenue by Carrier

\needspace{4in}

```{python}
# Chart code here
```
```

**Guidelines:**
- **Mermaid diagrams**: `\needspace{2in}`
- **Single chart**: `\needspace{3in}`
- **Chart + explanation**: `\needspace{4in}`

**Requires** in YAML frontmatter:
```yaml
format:
  pdf:
    include-in-header:
      text: |
        \usepackage{needspace}
```

## Markdown Formatting Rules (CRITICAL)

**IMPORTANT: Markdown requires blank lines between paragraphs for proper rendering.**

### Line Breaks and Paragraphs

**The Problem:**
```markdown
❌ BAD: This will render as one long line
This text appears on a new line in the source
But it renders on the same line as above
Because there's no blank line between them
```

**The Solution:**
```markdown
✅ GOOD: This renders as separate paragraphs

This text appears on its own line because there's a blank line above it.

Each paragraph needs a blank line before and after it.
```

### Common Markdown Patterns

**Paragraphs (need blank lines):**
```markdown
This is paragraph one.

This is paragraph two.

This is paragraph three.
```

**Lists REQUIRE blank line before the list:**
```markdown
❌ BAD: List doesn't render correctly
Here is some text:
- Item 1
- Item 2

✅ GOOD: Blank line before list
Here is some text:

- Item 1
- Item 2
```

**Numbered lists also require blank line before:**
```markdown
❌ BAD: Numbered list broken
The steps are:
1. First step
2. Second step

✅ GOOD: Blank line before numbered list
The steps are:

1. First step
2. Second step
```

**Lists (no blank lines between items):**
```markdown
- Item 1
- Item 2
- Item 3
```

**Multi-paragraph list items (blank lines within item):**
```markdown
- Item 1 with first paragraph

  Item 1 continued with second paragraph (indented 2 spaces)

- Item 2 starts here
```

**Headers (blank line before and after):**
```markdown
Previous paragraph ends here.

## Section Header

New paragraph starts here.
```

**Code blocks (blank line before and after):**
````markdown
Previous paragraph ends here.

```python
print("code block")
```

New paragraph starts here.
````

### Quarto-Specific Markdown

**Python code output:**
```python
#| echo: false
from IPython.display import Markdown

# ❌ BAD: Single newline won't create paragraph break
Markdown("Line 1\nLine 2")  # Renders as: Line 1 Line 2

# ✅ GOOD: Double newline creates paragraph break
Markdown("Line 1\n\nLine 2")  # Renders as separate paragraphs

# ✅ GOOD: Use triple-quoted string with blank lines
Markdown("""
Paragraph one.

Paragraph two.

Paragraph three.
""")
```

**F-strings in Markdown:**
```python
#| echo: false
from IPython.display import Markdown

# ✅ GOOD: Blank lines between paragraphs
Markdown(f"""
## Analysis Results

The growth rate is {growth_rate:.1%}.

This represents a significant increase over last quarter.

We recommend increasing inventory by {inventory_increase:,} units.
""")
```

### Best Practices

✅ **DO:**

- Use blank lines between all paragraphs
- Use blank lines before and after headers
- Use blank lines before and after code blocks
- Use blank lines before and after tables
- Use triple-quoted strings for multi-line markdown in Python

❌ **DON'T:**

- Use single newlines and expect paragraph breaks
- Forget blank lines around headers or code blocks
- Mix single and double newlines inconsistently
- Use `\n` in strings expecting paragraph breaks (use `\n\n`)

### Testing Markdown Formatting

**Quick test:**
```bash
# Create test document
cat > test.qmd << 'EOF'
---
title: "Markdown Test"
format: gfm
---

Paragraph 1.

Paragraph 2.

## Header

Paragraph 3.
EOF

# Render and check output
quarto render test.qmd --to gfm
cat test.md
```

## LLM Self-Reasoning with Quarto

Use `/think` command for structured analysis with graduated detail.

### Document Structure

Documents use graduated detail so readers can stop at their desired depth:

**Abstract** (paragraph)

- Self-contained executive summary
- Complete story: what, why, result, meaning
- Include key metrics and confidence assessment

**Key Findings** (3-5 bullets)

- Result + confidence + brief evidence
- Scannable - each finding valuable standalone
- Format: `**[Finding]**: [Result] — [Evidence] (Confidence)`

**Investigation** (detailed)

- Observations (sourced facts with academic citations `[source]`)
- Analysis (visual reasoning, statistical evidence)
- Interpretation (what it means, confidence, dependencies)

**Appendix** (optional)

- Investigation notes, dead ends, debugging traces
- External data sources NOT directly referenced in code blocks (e.g., verbal conversations, meeting notes, prior analyses)
- Do NOT duplicate data sources already expressed in code blocks - the code IS the source documentation

### Visual Evidence

Include diagram, chart, or table for most findings:

- Mermaid diagrams for reasoning flows
- Charts for quantitative analysis
- Formatted tables for comparative data

### Example Invocation

```
/think Why is the login endpoint returning 500 errors intermittently?
```

Creates analysis document with abstract-first structure, key findings with confidence levels, and visual reasoning chains.

See `/think` command for full template.

## When to Use Quarto

**Perfect for:**
- LLM epistemological reasoning (use `/think` command)
- Static reports and documentation (no interactivity needed)
- Multi-format publishing (PDF + HTML + Word from single source)
- Scientific documents (equations, citations, cross-references)
- Presentations (RevealJS HTML slides, PowerPoint, Beamer PDF)
- Websites and blogs (multi-page projects)
- Exporting Jupyter notebooks for publication

**NOT for:**
- Interactive dashboards (use Shiny or dedicated dashboard tools)
- Real-time data updates (use web dashboards)
- When you need widgets/sliders for end users

## Data Provenance and Portability

**CRITICAL: Quarto documents must be reproducible with documented dependencies.**

When someone runs `quarto render analysis.qmd`, they should be able to get identical results given:
- The document itself (`.qmd` file)
- Documented external dependencies (with setup instructions)
- Access to the same data sources (APIs, databases)

### The Portability Contract

A `.qmd` file defines a **complete data pipeline**. The document contains:
1. **Data extraction logic** - How to obtain the data (queries, API calls, etc.)
2. **Transformation code** - How to process and analyze
3. **Presentation** - Charts, tables, narrative
4. **Dependency documentation** - Setup instructions for heavy dependencies

**Practical limits**: Some dependencies are too expensive to rebuild on every render:
- **Vector indexes** (LanceDB, FAISS) - Document how to build, reference existing
- **Large datasets** - Commit to git or document extraction, don't re-download
- **ML models** - Reference by path with setup instructions

The key is **documentation**: readers must understand what's needed and how to set it up.

### Anti-Pattern: Opaque File References

❌ **BAD: Referencing local files without provenance**
```python
df = pd.read_json('/tmp/orders.jsonl', lines=True)  # Where did this come from?
df = pd.read_csv('sales.csv')  # Who created this? When? How?

# "This JSONL file" without explaining its origin
data = load_data('extracted_metrics.jsonl')  # Non-portable!
```

### Good Pattern: Embed Data Extraction

✅ **PREFERRED: Document defines where data comes from**
```python
#| cache: true
import subprocess
import io
import pandas as pd

# Extract from BigQuery - cached to avoid re-running on every render
result = subprocess.run([
    'bigquery', 'query',
    '''SELECT * FROM production.orders 
       WHERE date >= '2024-01-01' 
       AND status = 'completed' ''',
    '--format', 'jsonl'
], capture_output=True, text=True, check=True)

df = pd.read_json(io.StringIO(result.stdout), lines=True)
```

✅ **ALSO GOOD: Canonical external sources**
```python
#| cache: true
import pandas as pd

# Public dataset with stable URL
df = pd.read_csv('https://data.company.com/public/sales-2024.csv')

# Or versioned data in the same repository
df = pd.read_csv('data/sales-2024-v2.csv')  # Committed to git with the .qmd
```

### Heavy Dependencies: Document, Don't Rebuild

**Rule of thumb**: Un-cached renders should complete in < 60 seconds.

- **< 60 seconds** → Embed in document (with `cache: true`)
- **> 60 seconds** → Document as external dependency with setup instructions

Some dependencies are too expensive to recreate on every render. **Document them clearly** so readers can set up the environment.

✅ **GOOD: Reference with setup documentation**
```python
#| echo: false
import subprocess

# DEPENDENCY: LanceDB index at ~/.lancedb/documents
# Setup: lancer ingest -t documents ~/corpus/*.md
# This index contains ~50k documents and takes ~10 min to build

result = subprocess.run(
    ['lancer', 'search', '-t', 'documents', 'shipping rate errors', '--limit', '20'],
    capture_output=True, text=True, check=True
)
relevant_docs = result.stdout
```

✅ **GOOD: Prerequisites section in document**
```qmd
---
title: "Knowledge Base Analysis"
---

## Prerequisites

This analysis requires the following setup:

1. **LanceDB index**: `lancer ingest -t documents ~/corpus/*.md`
2. **BigQuery access**: Authenticated via `gcloud auth application-default login`
3. **Data snapshot**: Run `./scripts/extract-data.sh` (takes ~5 min)

## Analysis
...
```

❌ **BAD: Silent dependency on local state**
```python
# No documentation about what this index is or how to create it
results = lancer.search("documents", "query")  # Will fail for anyone else
```

### Caching for Iteration Speed

Use `cache: true` to avoid re-running expensive operations during iteration.

**Requires jupyter-cache** (one-time install):
```bash
uv pip install jupyter-cache
```

**Per-cell caching:**
```python
#| cache: true
#| label: data-extraction

# This cell only re-executes if the code changes
result = subprocess.run(['bigquery', 'query', ...], capture_output=True, text=True)
df = pd.read_json(io.StringIO(result.stdout), lines=True)
```

**Document-wide caching in YAML frontmatter:**
```yaml
---
title: "Analysis Report"
execute:
  cache: true
---
```

### Freeze for Project-Level Caching

For projects with many documents, use `freeze` to cache execution results in version control:

```yaml
# _quarto.yml (project config)
execute:
  freeze: auto  # Re-render only when source changes
```

**Key difference:**
- `cache: true` - Caches cell outputs locally (Jupyter Cache)
- `freeze: auto` - Stores results in `_freeze/` directory (can commit to git)

**When to use freeze:**
- Large projects with many collaborators
- Documents with environment-specific dependencies
- When you want cached results portable across machines (commit `_freeze/`)

### Complete Example: Reproducible Analysis

```qmd
---
title: "Q4 2024 Sales Analysis"
author: "Josh Lane"
date: "2024-12-31"
format:
  gfm:
    wrap: none
  html:
    theme:
      dark: darkly
      light: flatly
execute:
  cache: true
filters:
  - auto-dark
---

## Data Extraction

```{python}
#| cache: true
#| label: extract-sales
import subprocess
import io
import pandas as pd

# Reproducible: Query is embedded in the document
result = subprocess.run([
    'bigquery', 'query',
    '''
    SELECT date, product, region, sales, units
    FROM production.sales
    WHERE EXTRACT(QUARTER FROM date) = 4
      AND EXTRACT(YEAR FROM date) = 2024
    ''',
    '--format', 'jsonl'
], capture_output=True, text=True, check=True)

df = pd.read_json(io.StringIO(result.stdout), lines=True)
df['date'] = pd.to_datetime(df['date'])
```

## Analysis

```{python}
#| echo: false
from IPython.display import Markdown

total_sales = df['sales'].sum()
top_product = df.groupby('product')['sales'].sum().idxmax()

Markdown(f"""
### Key Metrics

- **Total Q4 Sales**: ${total_sales:,.2f}
- **Top Product**: {top_product}
- **Records**: {len(df):,}
""")
```
```

### Best Practices Summary

✅ **DO:**

- Embed data extraction commands in the document
- Use `cache: true` for expensive operations
- Reference canonical external URLs when possible
- Commit small data files alongside the `.qmd`
- Use `freeze` for project-level caching

❌ **DON'T:**

- Reference opaque local files (`/tmp/data.jsonl`)
- Say "this file" without showing how it was created
- Assume the reader has access to your local machine
- Leave data provenance undocumented

## Decision Tree: Quarto vs Alternatives

```
Need user interactivity? (sliders, dropdowns, real-time updates)
├─ YES → Use Shiny or dedicated dashboard tools
└─ NO → Static output needed
   │
   ├─ Complex multi-page documentation site?
   │  └─ YES → Use Quarto website/book projects
   │
   ├─ Single analysis with code + results?
   │  └─ Native Quarto .qmd files (recommended)
   │
   └─ Just formatting existing markdown?
      └─ Use Quarto with plain .md files
```

## Installation

Quarto is already installed (version 1.8.27).

**Optional dependencies:**

```bash
# TinyTeX for better PDF generation (LaTeX)
quarto install tinytex

# Chromium for PDF generation (alternative to LaTeX)
quarto install chromium
```

**Current setup:**
- ✅ Pandoc 3.6.3 (embedded)
- ✅ Chrome headless (system installation)
- ✅ Python 3.14.2 detected
- ✅ Jupyter installed (for Python code execution)
- ❌ TinyTeX not installed (optional)

## Neovim Integration

**quarto-nvim plugin is installed and configured.**

**Features:**
- LSP support for `.qmd` files (Python, bash, lua, html code chunks)
- Syntax highlighting for code chunks
- Diagnostics and completion in code cells
- Live preview with `:QuartoPreview`

**Keybindings:**
- `<leader>qp` - Preview current document (live reload)
- `<leader>qc` - Close preview
- `<leader>qm` - Render to markdown (GFM) - **RECOMMENDED default**
- `<leader>qh` - Render to HTML
- `<leader>qd` - Render to PDF

**Treesitter support:**
Quarto syntax highlighting requires treesitter parsers:
```bash
# In Neovim
:TSInstall markdown
:TSInstall markdown_inline
:TSInstall python
```

**Otter.nvim integration:**
The plugin uses otter.nvim for embedded language support in code chunks. This means you get full LSP features (completion, diagnostics, hover) for Python code inside `.qmd` files.

## Basic Usage

### Quick Start: Native .qmd Files

**Create a Quarto document:**

```bash
# Create analysis.qmd
cat > analysis.qmd << 'EOF'
---
title: "Sales Analysis Q4 2024"
author: "Josh Lane"
date: "2024-01-30"
format:
  gfm:
    wrap: none              # No line wrapping
  html:
    theme:
      dark: darkly          # Dark mode (recommended)
      light: flatly         # Light mode fallback
    code-fold: true
execute:
  cache: true               # Cache expensive queries
filters:
  - auto-dark               # Respect system preference
---

## Data Extraction

```{python}
#| cache: true
#| echo: false
import subprocess
import io
import pandas as pd

# Reproducible: Query embedded in document
result = subprocess.run([
    'bigquery', 'query',
    '''SELECT date, product, sales 
       FROM production.sales 
       WHERE EXTRACT(QUARTER FROM date) = 4 
       AND EXTRACT(YEAR FROM date) = 2024''',
    '--format', 'jsonl'
], capture_output=True, text=True, check=True)

df = pd.read_json(io.StringIO(result.stdout), lines=True)
df['date'] = pd.to_datetime(df['date'])
```

## Overview

```{python}
#| echo: false
import matplotlib.pyplot as plt
from IPython.display import Markdown

total_sales = df['sales'].sum()
avg_daily = df.groupby('date')['sales'].sum().mean()
top_product = df.groupby('product')['sales'].sum().idxmax()

# Display key metrics
Markdown(f"""
### Key Metrics

- **Total Sales**: ${total_sales:,.2f}
- **Average Daily Sales**: ${avg_daily:,.2f}
- **Top Product**: {top_product}
- **Records Analyzed**: {len(df):,}
""")
```

## Sales Trend Analysis

```{python}
#| label: fig-sales-trend
#| fig-cap: "Daily sales trending upward in Q4 2024"
#| echo: false

fig, ax = plt.subplots(figsize=(10, 6))
daily_sales = df.groupby('date')['sales'].sum()
daily_sales.plot(ax=ax, kind='line', linewidth=2, color='#2E86AB')
ax.set_title('Sales Trend Over Time', fontsize=14, fontweight='bold')
ax.set_xlabel('Date')
ax.set_ylabel('Sales ($)')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

## Top Products

```{python}
#| echo: false
# Format top 10 products as markdown table
top_products = (df.groupby('product')['sales']
                .sum()
                .sort_values(ascending=False)
                .head(10)
                .reset_index())

top_products.columns = ['Product', 'Total Sales']
top_products['Total Sales'] = top_products['Total Sales'].apply(lambda x: f"${x:,.2f}")

Markdown(top_products.to_markdown(index=False, tablefmt='pipe'))
```

## Statistical Analysis

```{python}
#| echo: false
import numpy as np

# Calculate growth metrics
daily_sales = df.groupby('date')['sales'].sum()
growth_rate = (daily_sales.iloc[-1] - daily_sales.iloc[0]) / daily_sales.iloc[0]
avg_growth = daily_sales.pct_change().mean()

Markdown(f"""
The sales data exhibits a compound growth pattern modeled by:

$$
S(t) = S_0 \\times (1 + r)^t
$$

where $S_0$ represents initial sales, $r = {avg_growth:.3f}$ is the average daily growth rate, 
and $t$ is time in days.

**Key Statistical Findings:**

- Overall Q4 growth: $\\Delta S = {growth_rate:.1%}$
- Average daily growth: $\\bar{{r}} = {avg_growth:.3%}$
- Standard deviation: $\\sigma = {daily_sales.std():,.2f}$
- Correlation with marketing spend: $\\rho = 0.82$ (strong positive)

These metrics indicate statistically significant growth ($p < 0.01$) with 
consistent upward momentum throughout the quarter.
""")
```

## Conclusion

Q4 2024 showed strong performance with total sales of **${total_sales:,.2f}**. The upward trend in daily sales indicates positive momentum heading into the next quarter.
EOF

# Install auto-dark extension (one-time, if not already installed)
quarto add gadenbuie/quarto-auto-dark --no-prompt

# Render to markdown (DEFAULT - composable, archival)
quarto render analysis.qmd --to gfm

# Optional: Render to HTML with dark mode for web viewing
quarto render analysis.qmd --to html        # Uses auto-dark theme

# Optional: Render to other formats only when needed
quarto render analysis.qmd --to pdf         # For Google Drive sharing/printing
quarto render analysis.qmd --to html        # For web viewing
```

### File Formats Quarto Can Render

**Input formats:**
- `.qmd` - Quarto markdown (native, recommended)
- `.ipynb` - Jupyter notebooks
- `.md` - Plain markdown (no code execution)
- `.Rmd` - R Markdown files

**Output formats:**
- **Markdown**: `md` (plain), `gfm` (GitHub-flavored) - **PREFERRED default**
- **Documents**: PDF, HTML, Word, ODT, ePub, Typst
- **Presentations**: RevealJS (HTML), PowerPoint, Beamer (PDF)
- **Websites**: Multi-page sites, blogs, books
- **Dashboards**: Interactive dashboards (with Shiny or Observable JS)

## Core Commands

```bash
# Render document to markdown (DEFAULT - composable, text-based)
quarto render document.qmd --to md           # Executable markdown with results
quarto render document.qmd --to gfm          # GitHub-flavored markdown

# Render to other formats
quarto render document.qmd --to pdf          # PDF (for Google Drive sharing)
quarto render document.qmd --to html         # HTML (avoid --toc, use clear headings)

# Render Jupyter notebook to markdown
quarto render notebook.ipynb --to md         # Markdown with executed results

# Render plain markdown (no code execution)
quarto render README.md --to pdf

# Multiple formats at once
quarto render document.qmd --to md,pdf,html

# Preview with live reload
quarto preview document.qmd

# Create new project
quarto create project website mysite
quarto create project book mybook

# Publish
quarto publish gh-pages                       # GitHub Pages
quarto publish quarto-pub                     # Quarto Pub
quarto publish netlify                        # Netlify
```

## Python Code Execution

### Code Blocks

````markdown
## Analysis Section

```{python}
import pandas as pd

df = pd.read_csv("data.csv")
df.head()
```
````

### Code Block Options

````markdown
```{python}
#| label: fig-sales
#| fig-cap: "Sales over time"
#| echo: false
#| warning: false

plt.figure(figsize=(10, 6))
df.plot(x='date', y='sales')
plt.show()
```
````

**Common options:**
- `echo: false` - Hide code, show output only
- `code-fold: true` - Collapsible code blocks
- `warning: false` - Hide warnings
- `message: false` - Hide messages
- `label: fig-name` - Reference label for cross-references
- `fig-cap: "Caption"` - Figure caption

### Inline Python Expressions

```markdown
The total is `{python} f"${total:,.2f}"`.

There are `{python} len(df)` rows in the dataset.
```

### Output Formatting

````markdown
## Display Options

```{python}
#| output: asis
print("**Bold text** from code")
```

```{python}
#| output: false
# Code runs but output is hidden
result = expensive_calculation()
```
````

### Table Formatting (CRITICAL)

**NEVER use raw `df.head()` or bare dataframes. ALWAYS format tables for presentation.**

#### Option 1: Great Tables (RECOMMENDED for rich formatting)

**Installation:**
```bash
uv add great-tables
```

**Basic usage:**
```python
from great_tables import GT

# Simple formatted table
GT(df.head(10))

# With styling
(GT(df.head(10))
    .tab_header(title="Sales Summary", subtitle="Q4 2024")
    .fmt_currency(columns="sales", currency="USD")
    .fmt_percent(columns="growth_rate", decimals=1)
    .fmt_number(columns="quantity", decimals=0)
    .fmt_date(columns="date", date_style="medium")
    .tab_source_note("Source: Company Database"))
```

**Advanced styling:**
```python
from great_tables import GT, loc, style

(GT(top_products)
    .tab_header(title="Top 10 Products by Revenue")
    .fmt_currency(columns="revenue", currency="USD")
    .data_color(
        columns="revenue",
        palette=["lightblue", "darkblue"],
        domain=[0, df['revenue'].max()]
    )
    .tab_style(
        style=style.text(weight="bold"),
        locations=loc.body(columns="product")
    ))
```

#### Option 2: pandas `.to_markdown()` (Simple, built-in)

**For markdown output (use Markdown() to render properly):**
```python
from IPython.display import Markdown

# Basic markdown table
Markdown(df.head(10).to_markdown(index=False, tablefmt='pipe'))

# With custom formatting
formatted_df = df.head(10).copy()
formatted_df['sales'] = formatted_df['sales'].apply(lambda x: f"${x:,.2f}")
formatted_df['date'] = pd.to_datetime(formatted_df['date']).dt.strftime('%Y-%m-%d')
Markdown(formatted_df.to_markdown(index=False, tablefmt='pipe'))
```

**Table format options:**
- `'pipe'` - GitHub-flavored markdown pipes (RECOMMENDED)
- `'grid'` - ASCII grid
- `'simple'` - Simple spacing
- `'html'` - HTML table (for HTML output)

#### Option 3: tabulate (Flexible formatting)

**Installation:**
```bash
uv add tabulate
```

**Usage:**
```python
from tabulate import tabulate
from IPython.display import Markdown

# Basic table
Markdown(tabulate(df.head(10), headers='keys', tablefmt='pipe', showindex=False))

# With custom formatting
Markdown(tabulate(
    df.head(10),
    headers=['Product', 'Sales', 'Date'],
    tablefmt='pipe',
    floatfmt='.2f',
    showindex=False
))
```

#### Best Practices for Tables

✅ **DO:**

- Use Great Tables for HTML/PDF output (rich formatting)
- Use `.to_markdown()` for markdown output (simplicity)
- Format currency, percentages, dates before display
- Add titles, subtitles, and source notes
- Limit to top N rows (10-20 max) - don't dump entire dataset
- Apply color scales for numerical columns
- Bold headers and important columns
- **Pair non-trivial tables with visuals** - tables showing trends, comparisons, or distributions need an accompanying chart

❌ **DON'T:**

- Use raw `df.head()` without formatting
- Display more than 20 rows in a table
- Show raw timestamps or unformatted numbers
- Include index column unless meaningful
- Use `print()` for tables (use `Markdown()` instead to render properly)
- Present analytical tables (trends, comparisons) without an accompanying chart

#### Table Formatting by Output Format

**For GFM/Markdown:**
```python
from IPython.display import Markdown
# Use Markdown() to render tables properly in Quarto
Markdown(df.head(10).to_markdown(index=False, tablefmt='pipe'))
```

**For HTML:**
```python
# Use Great Tables for rich styling
from great_tables import GT
GT(df.head(10)).fmt_currency(columns="sales")
```

**For PDF:**
```python
# Use Great Tables or formatted markdown
# Great Tables renders well in PDF via LaTeX
GT(df.head(10))
```

### Data Visualization Best Practices

**Charts and diagrams should be your PRIMARY communication tool, not an afterthought.**

#### When to Use Charts vs Tables

**Use Charts for:**

- Trends over time (line charts)
- Distributions (histograms, density plots)
- Comparisons across categories (bar charts)
- Proportions and composition (pie charts, stacked bars)
- Relationships between variables (scatter plots)
- Geographic data (maps, choropleth)

**Use Tables for:**

- Precise values needed (financial reports)
- Lookup reference (top N items)
- Multiple dimensions that don't visualize well
- Small datasets (< 20 rows)

**Use Both:**

- Chart for the trend, table for the details
- Chart for overview, table for drill-down

#### Chart Types by Use Case

**Trends and Time Series:**
```python
import matplotlib.pyplot as plt

# Line chart for trends
fig, ax = plt.subplots(figsize=(10, 6))
df.groupby('date')['sales'].sum().plot(ax=ax, kind='line', linewidth=2)
ax.set_title('Sales Trend Over Time', fontsize=14, fontweight='bold')
ax.set_ylabel('Sales ($)')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

**Comparisons:**
```python
# Bar chart for category comparisons
fig, ax = plt.subplots(figsize=(10, 6))
top_products = df.groupby('product')['sales'].sum().nlargest(10)
top_products.plot(ax=ax, kind='barh', color='#2E86AB')
ax.set_title('Top 10 Products by Sales', fontsize=14, fontweight='bold')
ax.set_xlabel('Sales ($)')
plt.tight_layout()
plt.show()
```

**Distributions:**
```python
# Histogram for distributions
fig, ax = plt.subplots(figsize=(10, 6))
df['order_value'].hist(bins=30, ax=ax, color='#A23B72', edgecolor='black')
ax.set_title('Order Value Distribution', fontsize=14, fontweight='bold')
ax.set_xlabel('Order Value ($)')
ax.set_ylabel('Frequency')
plt.tight_layout()
plt.show()
```

**Proportions:**
```python
# Pie chart for proportions (use sparingly)
fig, ax = plt.subplots(figsize=(8, 8))
category_sales = df.groupby('category')['sales'].sum()
ax.pie(category_sales, labels=category_sales.index, autopct='%1.1f%%', startangle=90)
ax.set_title('Sales by Category', fontsize=14, fontweight='bold')
plt.show()
```

**Relationships:**
```python
# Scatter plot for correlations
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(df['marketing_spend'], df['sales'], alpha=0.5, color='#F18F01')
ax.set_title('Marketing Spend vs Sales', fontsize=14, fontweight='bold')
ax.set_xlabel('Marketing Spend ($)')
ax.set_ylabel('Sales ($)')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

#### Styling Best Practices

✅ **DO:**

- Use descriptive titles with context
- Label axes with units
- Use color purposefully (not just default colors)
- Add gridlines for readability (alpha=0.3)
- Set appropriate figure size (10x6 for landscape, 8x8 for square)
- Use `plt.tight_layout()` to prevent label cutoff
- Add legends when showing multiple series
- Use consistent color schemes across document

❌ **DON'T:**

- Use default ugly matplotlib colors
- Skip axis labels or titles
- Create tiny, unreadable charts
- Use 3D charts (hard to read accurately)
- Overload charts with too many series (> 5-7)
- Use pie charts for more than 5 categories

#### Mermaid Diagrams (Quarto Native Syntax)

Quarto uses `{mermaid}` executable code blocks. Standard GFM ` ```mermaid ` fences won't render.

**Quarto syntax:**
````markdown
```{mermaid}
flowchart TD
    A[Load Data] --> B[Clean Data]
    B --> C[Analyze]
```
````

**Note:** GFM ` ```mermaid ` blocks and `Markdown('```mermaid...')` calls output raw text instead of rendered diagrams. Use the native `{mermaid}` syntax directly in markdown.

**Common Mermaid diagram types:**
- `flowchart` - Process flows, decision trees
- `sequenceDiagram` - Interaction sequences
- `classDiagram` - Object relationships
- `erDiagram` - Entity-relationship diagrams
- `gantt` - Project timelines
- `pie` - Simple pie charts

**Example: Reasoning flow:**
````markdown
```{mermaid}
flowchart LR
    F1[Fact: Q4 Sales = $2.1M] --> C1[Conclusion: Strong Quarter]
    F2[Fact: YoY Growth = 15%] --> C1
    F3[Fact: Top Product = Widget X] --> C2[Conclusion: Focus Marketing on Widgets]
```
````

**Preventing Mermaid Clipping in PDF:**

Mermaid diagrams can get clipped in PDF output when they exceed page width. Use `%%{init}%%` directives to control sizing:

````markdown
```{mermaid}
%%{init: {"flowchart": {"useMaxWidth": true}}}%%
flowchart TD
    A[Start] --> B[Process]
    B --> C[End]
```
````

**Best practices for PDF mermaid:**

- Always use `useMaxWidth: true` for flowcharts in PDF output
- Prefer `TD` (top-down) over `LR` (left-right) for wide diagrams
- Break complex diagrams into multiple smaller diagrams
- Use shorter node labels to reduce width
- Add to YAML frontmatter for document-wide defaults:

```yaml
format:
  pdf:
    mermaid:
      theme: default
```

#### Interactive Charts (HTML Output Only)

**For HTML output, use Plotly for interactivity:**

```python
import plotly.express as px

# Interactive line chart
fig = px.line(df, x='date', y='sales', title='Sales Trend (Interactive)')
fig.update_layout(hovermode='x unified')
fig.show()

# Interactive scatter with hover
fig = px.scatter(df, x='marketing_spend', y='sales', 
                 hover_data=['product', 'region'],
                 title='Marketing ROI Analysis')
fig.show()
```

**Note:** Plotly charts only work in HTML output. For PDF/Word, use matplotlib/seaborn.

#### Chart Selection Decision Tree

```
What are you showing?

├─ Change over time? → Line chart
├─ Compare categories? → Bar chart (vertical or horizontal)
├─ Show distribution? → Histogram or box plot
├─ Show composition? → Stacked bar or pie chart (if < 5 categories)
├─ Show relationship? → Scatter plot
├─ Show process/flow? → Mermaid flowchart
└─ Multiple variables? → Faceted plots or small multiples
```

### Mathematical Notation with LaTeX (STRONGLY ENCOURAGED)

**For any mathematical content, ALWAYS use LaTeX notation - it's professional and renders beautifully in all formats.**

#### Inline Math

```markdown
The equation $E = mc^2$ shows the relationship between energy and mass.

The growth rate is approximately $\alpha = 0.15$ or 15%.

We calculated the mean $\mu = \frac{\sum x_i}{n}$ from the dataset.
```

#### Display Math (Equations)

```markdown
The quadratic formula is:

$$
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$

The normal distribution probability density function:

$$
f(x) = \frac{1}{\sigma\sqrt{2\pi}} e^{-\frac{1}{2}\left(\frac{x-\mu}{\sigma}\right)^2}
$$
```

#### Aligned Equations

```markdown
$$
\begin{aligned}
\text{Revenue} &= \text{Price} \times \text{Quantity} \\
               &= \$50 \times 1000 \\
               &= \$50{,}000
\end{aligned}
$$
```

#### Common Mathematical Expressions

**Statistics:**
```markdown
- Mean: $\bar{x} = \frac{1}{n}\sum_{i=1}^{n} x_i$
- Variance: $\sigma^2 = \frac{1}{n}\sum_{i=1}^{n} (x_i - \mu)^2$
- Standard deviation: $\sigma = \sqrt{\sigma^2}$
- Correlation: $\rho_{X,Y} = \frac{\text{cov}(X,Y)}{\sigma_X \sigma_Y}$
```

**Finance:**
```markdown
- Compound interest: $A = P\left(1 + \frac{r}{n}\right)^{nt}$
- NPV: $NPV = \sum_{t=0}^{N} \frac{C_t}{(1+r)^t}$
- ROI: $ROI = \frac{\text{Gain} - \text{Cost}}{\text{Cost}} \times 100\%$
```

**Linear regression:**
```markdown
$$
y = \beta_0 + \beta_1 x_1 + \beta_2 x_2 + \epsilon
$$

where $\beta_0$ is the intercept, $\beta_i$ are coefficients, and $\epsilon \sim N(0, \sigma^2)$.
```

#### Numbered Equations (for cross-references)

```markdown
Einstein's mass-energy equivalence:

$$
E = mc^2
$$ {#eq-einstein}

As shown in @eq-einstein, energy and mass are equivalent.
```

#### Mathematical Notation Best Practices

✅ **DO:**

- Use LaTeX for ALL mathematical expressions, even simple ones like percentages
- Use `\text{}` for text within equations: `$\text{Revenue} = \$1{,}000$`
- Use proper notation: `\alpha, \beta, \mu, \sigma, \sum, \prod, \int`
- Number important equations for cross-referencing
- Use `aligned` environment for multi-line equations
- Format numbers properly: `\$1{,}000` for currency with comma separators
- Use `\times` for multiplication: $5 \times 10$
- Use `\cdot` for dot product: $\vec{a} \cdot \vec{b}$

❌ **DON'T:**

- Write "alpha = 0.15" in plain text - use $\alpha = 0.15$
- Write "x^2" in plain text - use $x^2$
- Use asterisk for multiplication - use $\times$ or $\cdot$
- Mix LaTeX and plain text notation inconsistently
- Skip equation numbering for important formulas

#### Example: Statistical Report with LaTeX

```markdown
## Regression Analysis

We fitted a linear model:

$$
\text{Sales} = \beta_0 + \beta_1 \times \text{Marketing Spend} + \epsilon
$$ {#eq-sales-model}

where $\epsilon \sim N(0, \sigma^2)$ represents random error.

### Results

The estimated parameters from @eq-sales-model are:

- Intercept: $\hat{\beta_0} = 50{,}000$ (SE = $2{,}500$)
- Slope: $\hat{\beta_1} = 3.2$ (SE = $0.4$)
- $R^2 = 0.78$

This indicates that each additional \$1 in marketing spend yields approximately \$3.20 in sales ($p < 0.001$).
```

### LaTeX Tables (Professional Formatting)

**For publication-quality tables in PDF output, use LaTeX table formatting alongside Great Tables.**

#### Basic LaTeX Table

````markdown
```{=latex}
\begin{table}[htbp]
\centering
\caption{Quarterly Sales Performance}
\label{tab:sales}
\begin{tabular}{lrrrr}
\hline
Quarter & Revenue (\$) & Growth (\%) & Units & Margin (\%) \\
\hline
Q1 2024 & 1,250,000 & 15.2 & 5,000 & 22.5 \\
Q2 2024 & 1,450,000 & 16.0 & 5,800 & 23.1 \\
Q3 2024 & 1,680,000 & 15.9 & 6,700 & 24.0 \\
Q4 2024 & 1,920,000 & 14.3 & 7,300 & 24.5 \\
\hline
\textbf{Total} & \textbf{6,300,000} & \textbf{15.4} & \textbf{24,800} & \textbf{23.5} \\
\hline
\end{tabular}
\end{table}
```
````

#### Enhanced LaTeX Table with booktabs (RECOMMENDED)

````markdown
```{=latex}
\begin{table}[htbp]
\centering
\caption{Statistical Summary of Key Metrics}
\label{tab:statistics}
\begin{tabular}{lcccc}
\toprule
Metric & Mean & SD & Min & Max \\
\midrule
Sales (\$) & 125{,}000 & 25{,}000 & 75{,}000 & 200{,}000 \\
Orders & 500 & 120 & 300 & 750 \\
AOV (\$) & 250 & 45 & 180 & 380 \\
Churn (\%) & 12.5 & 3.2 & 8.0 & 18.5 \\
\bottomrule
\end{tabular}
\end{table}
```
````

**booktabs provides professional-looking horizontal rules (better than \hline).**

**Add to YAML frontmatter for booktabs:**
```yaml
header-includes:
  - \usepackage{booktabs}
```

#### Python-Generated LaTeX Tables

**Option 1: Great Tables with LaTeX output**
```python
from great_tables import GT

# Great Tables can export to LaTeX
table = GT(df.head(10))
table.save("table.tex", format="latex")
```

**Option 2: pandas to_latex() with styling**
```python
import pandas as pd

# Format DataFrame for LaTeX
df_formatted = df.head(10).copy()
df_formatted['Sales'] = df_formatted['Sales'].apply(lambda x: f"\\${x:,.0f}")
df_formatted['Growth'] = df_formatted['Growth'].apply(lambda x: f"{x:.1f}\\%")

# Export to LaTeX with booktabs
latex_table = df_formatted.to_latex(
    index=False,
    caption="Top 10 Products by Sales",
    label="tab:top-products",
    position="htbp",
    column_format="lrrr",
    escape=False,  # Don't escape $ and %
    formatters={
        'Sales': lambda x: f"\\${x:,.0f}",
        'Growth': lambda x: f"{x:.1f}\\%"
    }
)

print(latex_table)
```

**Option 3: tabulate with LaTeX output**
```python
from tabulate import tabulate

latex_table = tabulate(
    df.head(10),
    headers='keys',
    tablefmt='latex_booktabs',  # Use booktabs style
    showindex=False,
    floatfmt='.2f'
)
print(f"\\begin{{table}}[htbp]\n\\centering\n\\caption{{Sales Summary}}\n{latex_table}\n\\end{{table}}")
```

#### LaTeX Table Best Practices

✅ **DO:**

- Use `booktabs` package for professional horizontal rules (\toprule, \midrule, \bottomrule)
- Add captions with `\caption{}`
- Add labels for cross-referencing with `\label{tab:name}`
- Use position specifiers: `[htbp]` (here, top, bottom, page)
- Right-align numbers, left-align text: `{lrr}` column format
- Format numbers: Use thousand separators (1{,}000), proper decimal places
- Use `\textbf{}` for bold text (totals, headers)
- Center the table with `\centering`

❌ **DON'T:**

- Use `\hline` - use booktabs rules instead (\toprule, \midrule, \bottomrule)
- Skip captions - tables should always be labeled
- Mix LaTeX and markdown tables in the same document
- Use vertical lines (`|`) - they look unprofessional
- Forget to escape special characters: \$, \%, \&

#### Cross-Referencing LaTeX Tables

```markdown
As shown in Table @tbl-sales, revenue increased across all quarters.

```{=latex}
\begin{table}[htbp]
\centering
\caption{Quarterly Revenue}
\label{tbl-sales}
...
\end{table}
```

Results from @tbl-sales indicate strong growth momentum.
```

#### When to Use LaTeX Tables vs Great Tables

**Use LaTeX tables when:**
- Creating PDF output with publication-quality typesetting
- Need precise control over table layout and spacing
- Working with complex multi-row/multi-column headers
- Creating tables for academic papers or formal reports
- Need to match specific journal formatting requirements

**Use Great Tables when:**
- Creating HTML output with interactive features
- Need quick table formatting without LaTeX complexity
- Working with markdown output
- Want consistent styling across HTML/PDF/Word formats
- Need color scales, data bars, or rich HTML styling

**Use both:**
```python
# Create table with Great Tables for HTML
gt_table = GT(df).fmt_currency(columns="sales")
gt_table  # Displays in HTML

# Also export LaTeX version for PDF
df.to_latex(caption="Sales Summary", label="tab:sales")
```

## YAML Frontmatter

### Simple Document (Markdown Default)

```yaml
---
title: "My Report"
author: "Josh Lane"
date: "2024-01-30"
format: gfm  # GitHub-flavored markdown (default for composability)
---
```

### Multiple Formats (Markdown + HTML with Dark Mode)

```yaml
---
title: "Analysis Report"
format:
  gfm:
    wrap: none
    variant: +yaml_metadata_block
  html:
    theme:
      dark: darkly          # Dark mode (recommended)
      light: flatly         # Light mode fallback
    toc: true
    code-fold: true
    code-tools: true
  pdf:
    toc: true
    number-sections: true
    geometry: margin=1in
filters:
  - auto-dark               # Auto-detect system preference
---
```

### Markdown-Only Output

```yaml
---
title: "Data Analysis"
format:
  md:
    output-file: "results.md"
    variant: gfm  # Use GitHub-flavored markdown
    preserve-yaml: true
  gfm:
    wrap: none
    output-file: "results-gfm.md"
---
```

### Advanced PDF Options

```yaml
---
title: "Technical Report"
format:
  pdf:
    documentclass: article
    fontsize: 11pt
    geometry:
      - margin=1in
      - paperwidth=8.5in
      - paperheight=11in
    toc: true
    toc-depth: 2
    number-sections: true
    colorlinks: true
    fig-pos: 'H'
    include-in-header:
      text: |
        \usepackage{fancyhdr}
        \pagestyle{fancy}
        \fancyhead[L]{My Company}
        \fancyhead[R]{\thepage}
---
```

### HTML Themes

**PREFER auto-dark with dual themes (see next section)** over single-theme HTML:

```yaml
---
format:
  html:
    theme:
      dark: darkly     # RECOMMENDED: Dual theme with auto-dark
      light: flatly
    css: custom.css
    toc: true
    toc-location: left
    code-fold: show
    code-tools: true
filters:
  - auto-dark          # Respects user's system preference
---
```

**Single theme (discouraged - doesn't respect user preference):**

```yaml
---
format:
  html:
    theme: darkly      # Only use if auto-dark not available
    css: custom.css
    toc: true
    toc-location: left
---
```

### Dark Mode with Auto-Dark Extension (RECOMMENDED)

**Dark mode is STRONGLY ENCOURAGED for all HTML output:**
- Better accessibility and reduced eye strain
- Modern user expectation (most systems default to dark mode)
- Auto-dark extension respects user's system preference

**Install auto-dark extension (one-time setup):**

```bash
# In your project or home directory (applies to all projects)
quarto add gadenbuie/quarto-auto-dark --no-prompt
```

**Use in document (RECOMMENDED default):**

```yaml
---
title: "My Analysis"
format:
  html:
    theme:
      dark: darkly      # Theme for dark mode (PRIMARY)
      light: flatly     # Theme for light mode (fallback)
filters:
  - auto-dark          # Automatically switch based on system preference
---
```

**Best Practices:**
- ✅ Always include auto-dark filter for HTML output
- ✅ Choose accessible dark theme (darkly, cyborg, slate)
- ✅ Test both dark and light modes if providing light fallback
- ⚠️ Single-theme HTML discouraged (use auto-dark instead)

**Available dark themes:**
- `darkly` - Dark Bootstrap theme (RECOMMENDED - clean, professional)
- `cyborg` - Dark blue theme (good for technical docs)
- `slate` - Dark gray theme (subtle, minimal)
- `solar` - Dark solarized theme (warm, comfortable)
- `superhero` - Dark comic book theme (bold, high contrast)
- `vapor` - Dark retro theme (stylized)

**Light themes (fallback only):**
- `flatly` - Clean modern theme (recommended fallback)
- `cosmo` - Friendly blue theme
- `lumen` - Light gray theme
- `sandstone` - Warm sandy theme
- `minty` - Fresh mint theme
- `journal` - Newspaper style

The `auto-dark` filter automatically detects system dark mode preference and switches themes accordingly. Users on light mode systems will see the light theme, while dark mode users (majority) get the dark theme.

## Table of Contents (Usually Noise - Avoid)

**IMPORTANT: Table of contents (TOC) is usually unnecessary noise in Quarto documents.**

### Why Avoid TOC

**Problems with TOC:**

- ❌ Adds visual clutter without adding value
- ❌ Redundant when you have clear section headings
- ❌ Takes up space at the top of the document
- ❌ Users can navigate with Ctrl+F or scroll
- ❌ In HTML, browsers have Find function
- ❌ In PDF, readers have built-in navigation
- ❌ Makes documents feel like academic papers (overly formal)

**Better alternatives:**

- ✅ Use clear, descriptive section headings
- ✅ Keep documents focused and concise
- ✅ Use visual hierarchy (# ## ### headings)
- ✅ Add anchor links manually if needed
- ✅ Trust readers to navigate using browser/PDF tools

### When TOC Might Be Acceptable

**ONLY use TOC for:**

- Very long documents (>20 pages)
- Books or comprehensive guides
- Multi-chapter documents
- When explicitly required by style guide

**Even then, prefer:**

- Sidebar TOC (not top-of-page)
- Collapsible TOC
- Floating TOC that doesn't obscure content

### How to Disable TOC

**Don't include `toc: true` in YAML frontmatter:**

```yaml
# ❌ BAD: Unnecessary TOC
---
title: "My Analysis"
format:
  html:
    toc: true        # DON'T DO THIS
---

# ✅ GOOD: Clean document without TOC
---
title: "My Analysis"
format:
  html:
    theme:
      dark: darkly
      light: flatly
---
```

**If you must use TOC, make it minimal:**

```yaml
format:
  html:
    toc: true
    toc-depth: 2           # Only top 2 levels
    toc-location: left     # Sidebar, not top
    toc-title: "Contents"  # Short title
```

## PDF for Google Drive Sharing

**PDF format is PREFERRED for sharing via Google Drive (read-only, professional appearance).**

### Rendering to PDF

```bash
# Basic PDF output
quarto render analysis.qmd --to pdf

# Multiple formats
quarto render analysis.qmd --to gfm,pdf,html
```

### Upload to Google Drive

```bash
# 1. Render to PDF
quarto render analysis.qmd --to pdf

# 2. Upload to Google Drive
# - Go to drive.google.com
# - Click "New" → "File upload"
# - Select analysis.pdf
# - Share link with collaborators

# Alternative: Use gspace CLI (if installed)
gspace upload analysis.pdf --folder "Reports"
```

## HTML Copy-Paste to Google Docs

**Alternative workflow: Render to HTML with Google Docs-compatible CSS, then copy-paste.**

This workflow is useful when:

- You need inline tables rendered as actual tables (not images)
- You want editable content in Google Docs (not read-only PDF)
- You're doing iterative editing between Quarto and Google Docs

### Google Docs CSS Setup

**Location:** `~/.files/quarto/styles/gdocs.css` (symlinked to `~/.config/quarto/styles/`)

The CSS matches Google Docs defaults:
- Arial 11pt, line-height 1.15
- Headers: 20pt (H1), 16pt (H2), 14pt (H3)
- Tables: 1pt black borders, minimal padding (2pt 6pt), vertical-align middle
- No extra whitespace in cells

### Using the Google Docs CSS

**Option 1: Reference from user config (RECOMMENDED)**

```yaml
---
title: "My Document"
format:
  html:
    css: ~/.config/quarto/styles/gdocs.css
    embed-resources: true
    minimal: true
---
```

**Option 2: Copy CSS to project directory**

```bash
# Copy CSS to project
mkdir -p .quarto/styles
cp ~/.files/quarto/styles/gdocs.css .quarto/styles/

# Use in document
# css: .quarto/styles/gdocs.css
```

**Option 3: Inline in YAML**

```yaml
---
format:
  html:
    include-in-header:
      text: |
        <style>
        body { font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.15; }
        table { border-collapse: collapse; margin: 12pt auto; }
        th, td { border: 1pt solid #000; padding: 2pt 6pt; vertical-align: middle; }
        th { background-color: #f3f3f3; font-weight: bold; }
        </style>
---
```

### Rendering and Copy-Paste Workflow

```bash
# 1. Render to HTML with Google Docs CSS
quarto render analysis.qmd --to html

# 2. Open in browser
open analysis.html

# 3. Select all and copy (Cmd+A, Cmd+C)

# 4. Paste into Google Docs (Cmd+V)
```

### CSS Reference

**Key CSS properties for Google Docs compatibility:**

```css
/* Body - matches Google Docs defaults */
body {
  font-family: Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.15;
}

/* Tables - critical for clean copy-paste */
table {
  border-collapse: collapse;
  margin: 12pt auto;
  page-break-inside: avoid;
}

th, td {
  border: 1pt solid #000;
  padding: 2pt 6pt;    /* Minimal padding for compact tables */
  vertical-align: middle;
  line-height: 1;
}

/* Remove spacing from cell content */
th *, td * {
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1 !important;
}

th {
  background-color: #f3f3f3;
  font-weight: bold;
}
```

### When to Use HTML Copy-Paste vs PDF

**Use HTML copy-paste when:**

- Tables must be editable in Google Docs
- You need precise formatting control
- Iterating between Quarto and Google Docs
- Complex layouts with multiple tables

**Use PDF upload when:**

- Read-only sharing is acceptable
- Professional appearance is priority
- Sharing with external stakeholders
- Archival or distribution

### Troubleshooting HTML Copy-Paste

**Extra whitespace in tables:**

- Ensure CSS has `line-height: 1` on cells
- Use `padding: 2pt 6pt` for minimal padding
- Add `vertical-align: middle` to prevent vertical gaps

**Fonts not matching:**

- Use `font-family: Arial, sans-serif` (Google Docs default)
- Avoid web fonts that won't copy

**Tables not copying correctly:**

- Check `border-collapse: collapse`
- Ensure tables have explicit borders (`border: 1pt solid #000`)
- Use `embed-resources: true` in YAML

**Charts/images not copying:**

- Charts copy as images (expected)
- Use `embed-resources: true` to inline images
- May need to re-insert images manually

## Presentations

### RevealJS Slides (HTML)

```qmd
---
title: "Quarterly Review"
format: revealjs
---

## Slide 1

Content here

## Slide 2

```{python}
import matplotlib.pyplot as plt
# Code executes, output shown
```

## {background-image="image.jpg"}

Slide with background image
```

**Render:**
```bash
quarto render slides.qmd --to revealjs
```

**Features:**
- Live code execution
- Animations and transitions
- Speaker notes
- Vertical slides
- Works in any browser

### PowerPoint

```qmd
---
title: "Report"
format: pptx
---

## Slide Title

- Bullet point
- Another point

## Chart Slide

```{python}
# Chart code
```
```

**Render:**
```bash
quarto render slides.qmd --to pptx
```

## Cross-References and Citations

### Figures

````qmd
See @fig-sales for the trend.

```{python}
#| label: fig-sales
#| fig-cap: "Sales over time"

plt.plot(df['date'], df['sales'])
plt.show()
```
````

### Tables

````qmd
As shown in @tbl-summary:

```{python}
#| label: tbl-summary
#| tbl-cap: "Summary statistics"

df.describe()
```
````

### Sections

```qmd
## Introduction {#sec-intro}

Content here.

## Analysis

As discussed in @sec-intro...
```

### Citations

```yaml
---
bibliography: references.bib
---

According to @smith2020, the results show...

Multiple citations [@smith2020; @jones2021].
```

**BibTeX file (references.bib):**
```bibtex
@article{smith2020,
  title={Analysis of Data},
  author={Smith, John},
  journal={Journal of Science},
  year={2020}
}
```

## Publishing Workflows

### GitHub Pages

```bash
# First time setup
quarto publish gh-pages

# Subsequent updates
quarto publish gh-pages
```

### Quarto Pub

```bash
# Publish to free Quarto hosting
quarto publish quarto-pub
```

### Netlify

```bash
quarto publish netlify
```

## Unix Philosophy Alignment

**Markdown-First Workflow (PREFERRED):**

```bash
# DEFAULT: Render to markdown for composability
quarto render analysis.qmd --to gfm         # GitHub-flavored markdown
quarto render analysis.qmd --to md          # Plain markdown

# Pipe markdown output to other tools
quarto render analysis.qmd --to md --output - | \
  grep "^##" | \
  sed 's/^## //' > toc.txt

# Generate markdown, then convert to PDF only if needed
quarto render analysis.qmd --to gfm
quarto render analysis.qmd --to pdf         # Optional
```

**Why Markdown Default:**
- Text-based: Human-readable, diffable, greppable
- Composable: Pipe to other tools (grep, sed, pandoc, etc.)
- Portable: Works everywhere (GitHub, wikis, editors)
- Archival: Plain text survives format changes
- Fast: No heavy rendering (PDF/HTML) unless needed

**Quarto as a Pipeline Component:**

```bash
# Composition pattern: process → transform → render → markdown
conform notes.txt --schema schema.json | \
  jq '.items[]' | \
  python generate_qmd.py > report.qmd && \
  quarto render report.qmd --to gfm

# Markdown → Post-processing
quarto render analysis.qmd --to gfm && \
  sed -i 's/TODO/DONE/g' analysis.md
```

**Do One Thing Well:**
- Quarto: Document rendering + format conversion
- NOT: Data analysis, interactive exploration, storage
- Delegate: Python for analysis, Quarto for rendering
- Prefer markdown output for downstream composition

**Text Streams:**
```bash
# Quarto accepts stdin
cat document.md | quarto render - --to gfm --output results.md

# Pipe through processing
cat data.json | \
  jq -r '.[] | "- \(.item)"' | \
  quarto render /dev/stdin --to gfm --output list.md
```

**Silent Success:**
```bash
# Quarto is quiet on success
quarto render doc.qmd --to gfm
echo $?  # 0 = success

# Use --quiet for scripts
quarto render doc.qmd --to gfm --quiet
```

## Common Patterns

### Pattern 1: Markdown-First (RECOMMENDED)

```bash
# Default: Generate markdown with executed results
quarto render analysis.qmd --to gfm

# Only create PDF/HTML when specifically needed for distribution
quarto render analysis.qmd --to gfm,pdf      # Markdown + PDF
quarto render analysis.qmd --to gfm,html     # Markdown + HTML

# Markdown for archival, PDF for sharing
quarto render report.qmd --to gfm
quarto render report.qmd --to pdf            # Only when needed
```

### Pattern 2: Single Source, Multiple Formats

```bash
# Render all formats (markdown first)
quarto render report.qmd --to gfm,pdf,html

# Or explicitly
quarto render report.qmd --to gfm            # Primary output
quarto render report.qmd --to pdf            # For Google Drive sharing
quarto render report.qmd --to html           # For web viewing
```

### Pattern 3: Batch Processing

```bash
# Render all .qmd files to markdown
for file in *.qmd; do
  quarto render "$file" --to gfm
done

# Or use find
find . -name "*.qmd" -exec quarto render {} --to gfm \;

# Parallel processing with xargs
find . -name "*.qmd" | xargs -P 4 -I {} quarto render {} --to gfm
```

### Pattern 3: Custom Templates

```bash
# Use custom template
quarto render doc.qmd --template custom-template.tex
```

### Pattern 4: Parameterized Reports

```qmd
---
title: "Monthly Report"
format: gfm
params:
  month: "January"
  year: 2024
---

## Report for `{python} params['month']` `{python} params['year']`

```{python}
month = params['month']
year = params['year']
# Analysis using params
```
```

**Render with parameters:**
```bash
# Markdown output with parameters
quarto render report.qmd -P month:February -P year:2024 --to gfm

# Generate markdown for all months
for month in Jan Feb Mar Apr; do
  quarto render report.qmd -P month:$month --to gfm --output "${month}_report.md"
done
```

### Pattern 5: Data Pipeline Reports

```bash
# Generate analysis data
python analysis.py > data.json

# Create Quarto report with embedded data loading
cat > report.qmd << 'EOF'
---
title: "Analysis Report"
execute:
  cache: true
---

```{python}
#| cache: true
import subprocess
import json

# Reproducible: document defines how data is generated
result = subprocess.run(['python', 'analysis.py'], capture_output=True, text=True, check=True)
data = json.loads(result.stdout)
# Render findings
```
EOF

quarto render report.qmd --to gfm
```

## Best Practices

### 1. Choose the Right Input Format

**Use `.qmd` when:**
- Starting new analysis
- Need maximum Quarto features
- Want native integration

**Use `.ipynb` when:**
- Already have Jupyter notebooks
- Collaborating with Jupyter users
- Need Jupyter-specific features

### 2. Organize Code Blocks

```qmd
## Good: Logical chunks

```{python}
# Load data
import pandas as pd
df = pd.read_csv("data.csv")
```

```{python}
# Analyze
total = df['sales'].sum()
```

## Bad: Everything in one block

```{python}
import pandas as pd
df = pd.read_csv("data.csv")
total = df['sales'].sum()
avg = df['sales'].mean()
# ... 50 more lines
```
```

### 3. Use Frontmatter for Configuration

```yaml
# Good: Centralized config
---
format:
  pdf:
    toc: true
    number-sections: true
  html:
    code-fold: true
---

# Bad: Repeating options in CLI
# quarto render doc.qmd --to pdf --toc --number-sections
```

### 4. Cache Expensive Computations

```qmd
```{python}
#| cache: true

# Expensive calculation cached
result = expensive_analysis(large_dataset)
```
```

### 5. Version Control

```gitignore
# .gitignore for Quarto projects
_site/
_book/
*.html
*.pdf
.quarto/
```

**Commit:**
- ✅ `.qmd` source files
- ✅ `_quarto.yml` config
- ✅ Data files (if small)
- ✅ `references.bib`
- ❌ Rendered outputs (regenerate)
- ❌ `.quarto/` cache directory

## Troubleshooting

### PDF Generation Fails

**Problem:** LaTeX errors when rendering PDF

**Solution 1: Install TinyTeX**
```bash
quarto install tinytex
```

**Solution 2: Use Typst (modern alternative)**
```yaml
---
format:
  typst: default
---
```

**Solution 3: Use Chrome headless**
```yaml
---
format:
  pdf:
    pdf-engine: chrome
---
```

### Python Code Not Executing

**Problem:** Code blocks don't run

**Check:**
1. Python is installed (`python3 --version`)
2. Required packages installed (`pip install pandas matplotlib`)
3. No syntax errors in code blocks

**Debug:**
```bash
quarto render doc.qmd --execute-debug
```

### Jupyter Kernel Not Found

**Problem:** Can't render `.ipynb` files

**Solution:**
```bash
# Install Jupyter
python3 -m pip install jupyter

# Or use uv
uv tool install jupyter
```

## Quick Reference

### Common Commands

```bash
quarto render doc.qmd                  # Render with default format
quarto render doc.qmd --to pdf        # Render to PDF
quarto render doc.qmd --to html       # Render to HTML
quarto preview doc.qmd                # Live preview
quarto create project website site   # Create website project
quarto publish gh-pages               # Publish to GitHub Pages
quarto install tinytex                # Install LaTeX
quarto check                          # Verify installation
```

### Output Format Options

```bash
--to gfm            # GitHub-flavored markdown (default)
--to pdf            # PDF via LaTeX or typst
--to html           # HTML
--to revealjs       # HTML slides
--to pptx           # PowerPoint
--to typst          # Typst (modern LaTeX alternative)
--to epub           # eBook
```

### Common YAML Frontmatter

```yaml
---
title: "Document Title"
author: "Josh Lane"
date: "2024-01-30"
format:
  pdf:
    toc: true               # Table of contents
    number-sections: true   # Numbered sections
    geometry: margin=1in    # Page margins
  html:
    toc: true
    code-fold: true         # Collapsible code
    theme: cosmo            # Visual theme
---
```

## Resources

- Official docs: https://quarto.org
- Gallery: https://quarto.org/docs/gallery/
- Guide: https://quarto.org/docs/guide/
- Extensions: https://quarto.org/docs/extensions/
- Publishing: https://quarto.org/docs/publishing/
