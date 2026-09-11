# Authoring Conventions

How Quarto documents communicate: visual hierarchy, output formatting, document structure,
data provenance, and the prose/code boundary. Read when writing or reviewing document content.

## Contents

- [Visual Expression Philosophy](#visual-expression-philosophy) — charts over dumps, `Markdown()` over `print()`
- [Narrative Structure](#narrative-structure) — document flow, base facts, synthesis, PDF page-break control
- [LLM Self-Reasoning with Quarto](#llm-self-reasoning-with-quarto) — graduated-detail structure for `/think` documents
- [Data Provenance and Portability](#data-provenance-and-portability) — embedded extraction, caching, freeze, heavy dependencies
- [Document & Report Writing Principles](#document--report-writing-principles) — the prose/code boundary

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
import pandas as pd
from epq import bq

# Extract from BigQuery via client library — cached to avoid re-running on every render
chunks = list(bq.run_bq_query("""
    SELECT * FROM production.orders
    WHERE date >= '2024-01-01'
    AND status = 'completed'
"""))
df = pd.concat(chunks, ignore_index=True)
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
uv add jupyter-cache
```

**Per-cell caching:**
```python
#| cache: true
#| label: data-extraction

# This cell only re-executes if the code changes
from epq import bq
import pandas as pd
chunks = list(bq.run_bq_query("SELECT ..."))
df = pd.concat(chunks, ignore_index=True)
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

### Cache-Read-or-Query Pattern (BigQuery / Expensive APIs)

Use this pattern when `cache: true` is insufficient — specifically when:

- Querying BigQuery or other expensive external APIs
- Cache must survive Quarto kernel restarts (Jupyter cache does not)
- You want explicit control over cache invalidation (not tied to source changes)
- Cache files are machine-specific and should be gitignored

Set `execute: cache: false` in frontmatter when using this pattern (disable Jupyter cache to avoid double-caching).

**Helper functions** (add once per document, in a setup cell):

```python
import json
from pathlib import Path
from datetime import datetime, timezone

_CACHE_DIR = Path('data/cache')
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _cache_path(name):
    return _CACHE_DIR / f"{name}.json"

def _read_cache(name):
    p = _cache_path(name)
    if p.exists():
        return json.loads(p.read_text())
    return None

def _write_cache(name, records, scalars=None):
    p = _cache_path(name)
    p.write_text(json.dumps({
        '_queried_at': datetime.now(timezone.utc).isoformat(),
        'records': records,
        'scalars': scalars or {}
    }, default=str))
```

**Per-dataset usage template** (repeat for each dataset):

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

**Cache hit** → reads DataFrame and scalars from JSON; no BigQuery call.
**Cache miss** → queries BigQuery live, writes cache, continues render.
**Query failure on miss** → render fails loudly (intentional — no silent fallback).

**Never do:**

- `except Exception: my_scalar = 42` — silent fallback masks broken queries
- Assign a constant inside `try:` without a preceding query call — hidden constant, not a live value
- Omit `_write_cache()` in the else branch — next render re-queries unnecessarily

**Cache file format:**

```json
{
    "_queried_at": "2026-02-20T16:00:00Z",
    "records": [...],
    "scalars": {...}
}
```

Serialization notes:
- Numpy arrays → store as lists (`df['col'].tolist()`), reconstruct with `np.array(...)`
- Dates → use `default=str` in `json.dumps` to handle non-serializable types

**Cache invalidation:**

```
# .gitignore
data/cache/

# Justfile recipe
delete-cache:
    rm -rf data/cache/
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

## Document & Report Writing Principles

### Data Sources Stay in Code, Not Prose

When writing Quarto documents, strategy memos, or any analytical report:

- **Never name data sources in prose** — table names (`all_customers_revenue_final`), field names (`salesforce_account_id`, `recognized_revenue_c`), database names (`ep-core-data`), query tools (`BigQuery`, `Prophet`), or internal implementation details belong in code cells only
- **Describe the data, not where it came from** — write "actual revenue from those accounts" not "revenue from `all_customers_revenue_final` joined via `salesforce_account_id`"
- **Describe the method, not the tool** — write "trend model with yearly seasonality" not "Prophet with `changepoint_prior_scale`"
- **The code is the documentation** — readers who need provenance can read the code cells; prose is for interpretation and insight

### What Belongs in Prose vs. Code

| Prose | Code |
|---|---|
| "actual revenue from sales-linked accounts" | `JOIN all_customers_revenue_final ON salesforce_account_id` |
| "trend model incorporating deal count" | `Prophet.add_regressor('won_count_norm')` |
| "CRM-linked accounts" | `WHERE salesforce_account_id IS NOT NULL` |
| "80% of revenue is attributable" | `sf_corr_attributed_pct = ...` |
| "pipeline data available since April 2024" | cache TTL, query date bounds |
