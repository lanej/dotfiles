---
description: Create computational narratives with MyST Markdown notebooks (myst-nb). Use for reproducible analysis, data exploration, research documentation, and EPIST provenance tracking. Triggers on "notebook", "computational narrative", "reproducible analysis", "MyST notebook", "executable markdown", or data analysis documentation.
---

# MyST Notebook Skill

MyST-NB (Markedly Structured Text - Notebook) allows you to create executable computational notebooks entirely in Markdown. Perfect for reproducible data analysis, research documentation, and integrating with EPIST for provenance tracking.

## When to Use MyST Notebooks

**Perfect for:**
- Reproducible data analysis with inline code execution
- Research documentation with computational narratives
- EPIST workflows (track analysis + code + outputs together)
- Version control friendly notebooks (text-based, not JSON)
- Creating technical reports with live computations
- Building documentation with executable examples
- Mixing analysis code with narrative explanations

**NOT for:**
- Simple static documentation (use plain Markdown)
- Interactive development (use Jupyter Lab for that)
- Non-technical documents (use Markdown or Word)

## Core Concepts

### Text-Based Notebooks
MyST notebooks are `.md` files that can be executed like Jupyter notebooks:
- Store in version control easily (readable diffs)
- Edit in any text editor
- Convert to/from `.ipynb` with jupytext
- Execute with Sphinx or Jupyter Book

### 1-to-1 Mapping with Jupyter
Every MyST notebook can be converted to `.ipynb`:
- Same execution model
- Same metadata structure
- Same kernel support
- Can open in Jupyter Lab/Notebook

### Integration with EPIST
MyST notebooks are ideal for EPIST workflows:
- Track analysis code + narrative + outputs together
- Version control for provenance chains
- Embed facts/conclusions with supporting code
- Reproducible evidence for claims

## Installation

```bash
# Install MyST-NB
pip install myst-nb

# For Jupyter interface support
pip install jupytext

# Quick start a project
mystnb-quickstart my_project/docs/
```

## MyST Notebook Structure

### 1. Notebook-Level Metadata

Every MyST notebook starts with YAML frontmatter:

```markdown
---
file_format: mystnb
kernelspec:
  name: python3
  display_name: Python 3
jupytext:
  text_representation:
    extension: .md
    format_name: myst
---
# Analysis Title

Your narrative begins here...
```

**Required fields:**
- `file_format: mystnb` - Identifies this as a MyST notebook
- `kernelspec.name` - Kernel to execute code (python3, julia, R, etc.)

### 2. Markdown Cells

Write regular Markdown between code cells:

```markdown
## Introduction

This analysis explores customer churn patterns using the Q4 2024 dataset.

**Key questions:**
- What factors correlate with churn?
- Which customer segments are at highest risk?
```

**MyST Markdown features:**
- Cross-references: `{ref}`my-label``
- Figures: `{figure}` directive
- Admonitions: `{note}`, `{warning}`, etc.
- Math: `$$...$$` or `` `{math}` ``
- Citations: `{cite}`paper2024``

### 3. Code Cells

Execute code with the `{code-cell}` directive:

````markdown
```{code-cell} ipython3
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('data.csv')
print(f"Loaded {len(df)} rows")
df.head()
```
````

**Key points:**
- Language after `{code-cell}` is optional (just for syntax highlighting)
- Code executes in order during build
- Outputs are captured and displayed

### 4. Cell-Level Metadata

Control cell behavior with YAML metadata:

````markdown
```{code-cell} ipython3
---
tags: [hide-input, remove-output]
---
# This code runs but input/output are hidden
secret_config = load_credentials()
```
````

**Alternative shorthand syntax:**

````markdown
```{code-cell} ipython3
:tags: [hide-output]
:linenos:

for i in range(100):
    process(i)
```
````

## Common Cell Tags

### Hiding Content

```markdown
tags: [hide-input]      # Hide code, show output
tags: [hide-output]     # Show code, hide output
tags: [hide-cell]       # Hide everything (still executes)
tags: [remove-input]    # Remove code from output
tags: [remove-output]   # Remove output from build
tags: [remove-cell]     # Remove entire cell
```

### Execution Control

```markdown
tags: [skip-execution]     # Don't execute this cell
tags: [raises-exception]   # Allow cell to raise exception
```

### Formatting

```markdown
:linenos:                  # Show line numbers
:emphasize-lines: 2,3      # Highlight specific lines
```

## Building MyST Notebooks

### With Sphinx

```bash
# Install and configure
pip install myst-nb sphinx

# In conf.py
extensions = ["myst_nb"]

# Build
sphinx-build -nW --keep-going -b html docs/ docs/_build/html

# Parallel execution (4 processes)
sphinx-build -j 4 -b html docs/ docs/_build/html
```

### With Jupyter Book

```bash
# Install
pip install jupyter-book

# Create book
jupyter-book create mybook/

# Build
jupyter-book build mybook/

# Publish to GitHub Pages
ghp-import -n -p -f mybook/_build/html
```

## Conversion Between Formats

### MyST → Jupyter Notebook

```bash
# Using built-in command
mystnb-to-jupyter analysis.md
# Creates: analysis.ipynb

# Using jupytext
jupytext analysis.md --to ipynb
```

### Jupyter Notebook → MyST

```bash
# Using jupytext
jupytext notebook.ipynb --to myst

# Set as paired notebook (auto-sync)
jupytext --set-formats ipynb,md:myst notebook.ipynb
```

## Execution and Caching

### Execution Modes

Configure in `conf.py` or `_config.yml`:

```python
# Execute all notebooks
nb_execution_mode = "auto"

# Execute only if outputs are missing
nb_execution_mode = "cache"

# Never execute (use existing outputs)
nb_execution_mode = "off"

# Force execute all
nb_execution_mode = "force"
```

### Caching with jupyter-cache

```bash
# Install
pip install jupyter-cache

# Configure in conf.py
nb_execution_mode = "cache"
nb_execution_cache_path = ".jupyter_cache"

# Clear cache
jcache cache clear
```

## Advanced Features

### Inline Code Evaluation

Execute code inline with `` {eval} ``:

```markdown
The dataset contains {eval}`len(df)` rows and {eval}`len(df.columns)` columns.
```

### Glue for Variable Reuse

Save variables to reuse across cells:

````markdown
```{code-cell} ipython3
from myst_nb import glue

total_revenue = df['revenue'].sum()
glue("total_revenue", total_revenue, display=False)
```

Later in the document:

The total revenue was {glue:text}`total_revenue:.2f`.
````

### Code from Files

Load code from external files:

````markdown
```{code-cell} ipython3
:load: scripts/analysis.py
```
````

### Multiple Markdown Cells

Break Markdown into separate cells:

```markdown
First markdown cell content.

+++ {"metadata": "value"}

Second markdown cell content.
```

## MyST Notebooks + EPIST Workflow

### Pattern 1: Analysis Notebook as Fact Source

```markdown
---
file_format: mystnb
kernelspec:
  name: python3
---

# Customer Churn Analysis - Q4 2024

## Data Loading

```{code-cell} ipython3
import pandas as pd
from epist import FactRecorder

recorder = FactRecorder("churn_analysis_q4_2024")
df = pd.read_csv('customers_q4.csv')

recorder.record_fact(
    "dataset_size",
    len(df),
    source="customers_q4.csv",
    description="Number of customer records analyzed"
)
```

## Churn Rate Calculation

```{code-cell} ipython3
churn_rate = (df['churned'] == True).mean()

recorder.record_fact(
    "overall_churn_rate", 
    churn_rate,
    calculation="(churned == True).mean()",
    description="Percentage of customers who churned in Q4"
)

print(f"Q4 Churn Rate: {churn_rate:.2%}")
```

## Conclusion

The Q4 2024 churn rate was {eval}`f"{churn_rate:.2%}"`, which represents
{eval}`int(len(df) * churn_rate)` customers.

```{code-cell} ipython3
# Save provenance chain
recorder.save("analyses/churn_q4_2024.json")
```
```

### Pattern 2: Exploratory Data Analysis

```markdown
---
file_format: mystnb
kernelspec:
  name: python3
---

# Exploring Survey Response Data

## Setup

```{code-cell} ipython3
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Load data extracted with conform
df = pd.read_csv('survey_responses_structured.csv')
```

## Distribution Analysis

```{code-cell} ipython3
# Sentiment distribution
sentiment_counts = df['sentiment'].value_counts()

plt.figure(figsize=(10, 6))
sentiment_counts.plot(kind='bar')
plt.title('Sentiment Distribution')
plt.xlabel('Sentiment')
plt.ylabel('Count')
plt.tight_layout()
plt.show()

# Record finding
from epist import record_conclusion
record_conclusion(
    "negative_sentiment_dominates",
    f"Negative sentiment represents {sentiment_counts['negative'] / len(df):.1%} of responses",
    evidence={"total": len(df), "negative": sentiment_counts['negative']}
)
```

## Statistical Summary

```{code-cell} ipython3
:tags: [hide-input]

# Detailed statistics
summary = df.describe()
summary
```

Key metrics saved to EPIST for downstream analysis.
```

### Pattern 3: Report Generation

```markdown
---
file_format: mystnb
kernelspec:
  name: python3
---

# Weekly Metrics Report

**Generated:** {eval}`pd.Timestamp.now().strftime('%Y-%m-%d')`

## Executive Summary

```{code-cell} ipython3
---
tags: [remove-cell]
---
import pandas as pd
from epist import load_facts

# Load facts from EPIST
facts = load_facts("weekly_metrics")
```

This week's key metrics:

- **Active Users:** {glue:text}`active_users:,`
- **Conversion Rate:** {glue:text}`conversion_rate:.2%`
- **Revenue:** ${glue:text}`revenue:,.2f`

## Detailed Analysis

```{code-cell} ipython3
# Load and visualize trends
trends = pd.read_csv('weekly_trends.csv')
trends.plot(x='week', y='active_users', figsize=(12, 6))
plt.title('Active User Trend')
plt.show()
```

All metrics tracked in EPIST for provenance.
```

## Configuration

### Sphinx Configuration (conf.py)

```python
# Basic setup
extensions = [
    "myst_nb",
    # myst_parser is loaded automatically, remove if present
]

# Execution settings
nb_execution_mode = "cache"
nb_execution_timeout = 300  # 5 minutes per cell

# MyST Markdown extensions
myst_enable_extensions = [
    "dollarmath",       # $...$ for inline math
    "amsmath",          # $$...$$ for display math
    "colon_fence",      # ::: for directives
    "deflist",          # Definition lists
    "fieldlist",        # Field lists
    "substitution",     # Variable substitution
]

# Notebook kernel timeout
nb_kernel_rgx_aliases = {"python3": "python"}

# Hide cell source by default (optional)
# nb_render_priority = {"html": ("application/vnd.jupyter.widget-view+json", "text/html")}
```

### Jupyter Book Configuration (_config.yml)

```yaml
# Book settings
title: My Analysis Book
author: Your Name

# Execution settings
execute:
  execute_notebooks: cache
  timeout: 300
  allow_errors: false

# MyST settings
parse:
  myst_enable_extensions:
    - dollarmath
    - colon_fence
    - deflist

# Sphinx extensions
sphinx:
  extra_extensions:
    - sphinx.ext.autodoc
```

## Best Practices

### 1. Notebook Organization

```markdown
# Good structure:
---
file_format: mystnb
kernelspec:
  name: python3
---

# Title (H1 - only one)

## Introduction (H2)
Narrative text...

## Data Loading (H2)
Code + narrative...

## Analysis (H2)
Code + narrative...

## Conclusions (H2)
Final narrative...
```

### 2. Cell Management

**Do:**
- One logical operation per cell
- Add narrative before/after code cells
- Use hide-input for setup code
- Use hide-output for verbose operations

**Don't:**
- Put too much code in one cell
- Mix unrelated operations
- Leave cells without explanation

### 3. Version Control

```bash
# Good: Text-based MyST notebook
git diff analysis.md  # Readable changes

# Less ideal: Binary .ipynb
git diff analysis.ipynb  # JSON diff noise
```

### 4. EPIST Integration

```python
# Always include provenance metadata
recorder.record_fact(
    key="metric_name",
    value=result,
    source="data_file.csv",
    calculation="df.groupby('x').mean()",
    timestamp=pd.Timestamp.now(),
    notebook="analysis.md"
)
```

### 5. Reproducibility

```markdown
## Environment

```{code-cell} ipython3
---
tags: [hide-output]
---
import sys
import pandas as pd
import numpy as np

print(f"Python: {sys.version}")
print(f"Pandas: {pd.__version__}")
print(f"NumPy: {np.__version__}")
```

Document your environment for future reproducibility.
```

## Common Patterns

### Data Analysis Pipeline

```markdown
---
file_format: mystnb
kernelspec:
  name: python3
---

# Pipeline: Raw Data → Insights

## 1. Load Raw Data

```{code-cell} ipython3
import pandas as pd
raw_df = pd.read_csv('raw_data.csv')
print(f"Loaded {len(raw_df)} rows")
```

## 2. Clean Data

```{code-cell} ipython3
:tags: [hide-input]

# Cleaning steps
clean_df = raw_df.dropna()
clean_df = clean_df[clean_df['value'] > 0]
print(f"After cleaning: {len(clean_df)} rows")
```

## 3. Analyze

```{code-cell} ipython3
summary = clean_df.groupby('category').agg({
    'value': ['mean', 'std', 'count']
})
summary
```

## 4. Visualize

```{code-cell} ipython3
import matplotlib.pyplot as plt

clean_df.boxplot(column='value', by='category', figsize=(10, 6))
plt.suptitle('')
plt.tight_layout()
plt.show()
```

## Conclusions

Key findings documented in EPIST for downstream use.
```

### Comparative Analysis

```markdown
---
file_format: mystnb
kernelspec:
  name: python3
---

# A/B Test Results - Feature Launch

## Load Both Variants

```{code-cell} ipython3
import pandas as pd

control = pd.read_csv('control_group.csv')
treatment = pd.read_csv('treatment_group.csv')

print(f"Control: {len(control)} users")
print(f"Treatment: {len(treatment)} users")
```

## Statistical Test

```{code-cell} ipython3
from scipy import stats

control_conv = control['converted'].mean()
treatment_conv = treatment['converted'].mean()

# Chi-square test
_, p_value = stats.chi2_contingency([[
    control['converted'].sum(), len(control) - control['converted'].sum()
], [
    treatment['converted'].sum(), len(treatment) - treatment['converted'].sum()
]])[:2]

print(f"Control conversion: {control_conv:.2%}")
print(f"Treatment conversion: {treatment_conv:.2%}")
print(f"P-value: {p_value:.4f}")
```

## Conclusion

{eval}`"Statistically significant" if p_value < 0.05 else "Not significant"` 
difference detected (p={eval}`p_value:.4f`).

Record this finding in EPIST for decision tracking.
```

## Troubleshooting

### Kernel Not Found

```bash
# List available kernels
jupyter kernelspec list

# Install Python kernel
python -m ipykernel install --user --name python3

# Update notebook metadata
---
kernelspec:
  name: python3  # Must match installed kernel
---
```

### Execution Errors

```python
# Allow errors in specific cells
tags: [raises-exception]

# Or configure globally (conf.py)
nb_execution_allow_errors = False  # Fail on errors
```

### Timeout Issues

```python
# Increase timeout (conf.py)
nb_execution_timeout = 600  # 10 minutes

# Or per-cell
:timeout: 120  # 2 minutes for this cell
```

### Cache Issues

```bash
# Clear Jupyter cache
jcache cache clear

# Or delete cache directory
rm -rf .jupyter_cache

# Force re-execution
sphinx-build -E -b html docs/ docs/_build/html
```

## Integration with Other Tools

### With DuckDB

````markdown
```{code-cell} ipython3
import duckdb

# Analyze CSV with SQL
result = duckdb.query("""
    SELECT category, AVG(amount) as avg_amount
    FROM 'data.csv'
    GROUP BY category
""").df()

result
```
````

### With Conform

````markdown
```{code-cell} ipython3
# Load conform-extracted data
import pandas as pd

# Conform extracted structured data from PDF
df = pd.read_json('invoices_extracted.json')

# Now analyze with pandas/duckdb
summary = df.groupby('vendor').sum()
summary
```
````

### With EPIST

````markdown
```{code-cell} ipython3
from epist import FactRecorder, record_conclusion

# Initialize recorder
recorder = FactRecorder("analysis_2024_q4")

# Record facts as you analyze
churn_rate = df['churned'].mean()
recorder.record_fact("churn_rate_q4", churn_rate, 
                     source="customers.csv",
                     notebook="churn_analysis.md")

# Record conclusions
if churn_rate > 0.15:
    record_conclusion(
        "high_churn_alert",
        f"Q4 churn rate ({churn_rate:.1%}) exceeds threshold",
        evidence={"threshold": 0.15, "actual": churn_rate}
    )

# Save provenance chain
recorder.save("analyses/churn_q4.json")
```
````

## Quick Reference

### Basic Notebook Template

```markdown
---
file_format: mystnb
kernelspec:
  name: python3
---

# Analysis Title

## Introduction

Background and context...

## Data Loading

```{code-cell} ipython3
import pandas as pd
df = pd.read_csv('data.csv')
```

## Analysis

```{code-cell} ipython3
# Your analysis code
result = df.groupby('category').mean()
result
```

## Conclusions

Summary of findings...
```

### Common Commands

```bash
# Create project
mystnb-quickstart my_analysis/

# Build with Sphinx
sphinx-build -b html docs/ docs/_build/html

# Convert to notebook
mystnb-to-jupyter analysis.md

# Build with Jupyter Book
jupyter-book build mybook/

# Clear cache
jcache cache clear
```

## Resources

- Official docs: https://myst-nb.readthedocs.io
- Jupyter Book: https://jupyterbook.org
- MyST Markdown: https://myst-parser.readthedocs.io
- Jupytext: https://jupytext.readthedocs.io
- Gallery: https://executablebooks.org/en/latest/gallery
