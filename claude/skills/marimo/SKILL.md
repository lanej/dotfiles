---
name: marimo
description: Create reactive Python notebooks with marimo for data analysis and EPIST provenance tracking. Use for ad-hoc analysis, interactive reports, reproducible research with automatic reactivity. Triggers on "notebook", "reactive notebook", "data analysis", "interactive analysis", "EPIST analysis", "computational narrative", or single-file analysis workflows. STRONGLY PREFERRED over MyST-NB for EPIST workflows.
---

# Marimo Skill

Marimo is a reactive Python notebook that runs as a pure `.py` file. Perfect for EPIST data analysis workflows where you need single-file execution, automatic reactivity, and direct Python integration.

## Visual Expression Philosophy

**CRITICAL: Marimo notebooks are for VISUAL COMMUNICATION, not raw data dumps.**

### Visualize, Don't Serialize

```python
# ❌ BAD: Dumping raw JSON/dicts
@app.cell
def __(data):
    data  # Just returns raw dict/JSON

# ✅ GOOD: Visual representation
@app.cell
def __(data, mo):
    mo.ui.table(data)  # Interactive table
    
# ✅ GOOD: Charts and plots
@app.cell
def __(data, plt):
    fig, ax = plt.subplots()
    ax.plot(data['x'], data['y'])
    fig

# ✅ GOOD: Formatted markdown
@app.cell
def __(metrics, mo):
    mo.md(f"""
    ## Key Metrics
    
    - **Revenue**: ${metrics['revenue']:,.2f}
    - **Growth**: {metrics['growth']:.1%}
    - **Customers**: {metrics['customers']:,}
    """)
```

### Why Visual Expression Matters

- **Notebooks are for humans**: Show insights, not raw data structures
- **EPIST provenance**: Visualize relationships between facts and conclusions
- **Interactive exploration**: Use widgets for parameter sweeps, not print statements
- **Shareable reports**: Visual outputs communicate better than JSON blobs
- **Reproducibility**: Visual outputs + code = complete story

### Visual Hierarchy

1. **Charts/plots** - For trends, distributions, relationships (matplotlib, altair, plotly)
2. **Tables** - For structured data exploration (`mo.ui.table()`)
3. **Formatted text** - For metrics, summaries, conclusions (`mo.md()`, `mo.callout()`)
4. **Raw output** - ONLY for debugging (use `mo.tree()` for dicts, not bare dicts)

## When to Use Marimo

**Perfect for:**
- EPIST data analysis with provenance tracking (visualized!)
- Ad-hoc single-file analysis (no project scaffolding needed)
- Interactive reports with sliders/widgets
- Reproducible research with automatic updates
- Version-controlled analysis (git-friendly `.py` files)
- Analyses that need to run as scripts
- No hidden state - deterministic execution

**NOT for:**
- Large multi-document documentation sites (use Quarto/Jupyter Book)
- Static content without computation (use Markdown)
- Static reports with no interactivity needed (use Quarto `.qmd` files directly)
- When you specifically need Jupyter notebook format
- Dumping raw JSON/data without visualization

## Why Marimo > MyST-NB for EPIST

| Feature | Marimo | MyST-NB |
|---------|--------|---------|
| Single-file execution | ✅ Perfect | ❌ Requires Sphinx project |
| EPIST integration | ✅ `import epist` | ⚠️ YAML metadata workarounds |
| Reactive updates | ✅ Automatic | ❌ Manual rerun |
| Run as script | ✅ `python file.py` | ❌ Not supported |
| Version control | ✅ Pure `.py` | ✅ Text `.md` |
| PDF export | ✅ 4 methods | ✅ Via Sphinx |
| Learning curve | ✅ Low | ⚠️ Medium |

## Editor Integration & Export

### Using Marimo with Your Own Editor

Marimo works seamlessly with any text editor (Neovim, Zed, VS Code, PyCharm) through file-watching mode. Edit marimo notebooks as plain `.py` files in your preferred editor, and changes sync automatically to your browser.

**Development workflow:**

```bash
# Edit notebook in Neovim/your editor, sync changes to browser
marimo edit notebook.py --watch

# Changes are marked as stale (manual run required)
# Or configure autorun in pyproject.toml:
# [tool.marimo.runtime]
# watcher_on_save = "autorun"
```

**App workflow:**

```bash
# Run as app, auto-refresh browser on file save
marimo run notebook.py --watch
```

**Best practices:**
- Enable autosave in your editor for seamless experience
- Use `--watch` for both `.py` and `.md` notebook files
- Install `watchdog` package for better file-watching performance: `pip install watchdog`
- **VS Code/Cursor users**: Consider the [marimo VS Code extension](https://marketplace.visualstudio.com/items?itemName=marimo-team.vscode-marimo) for first-class integration

The file-watching approach works with marimo's pure Python format - your editor gets full Python LSP support, syntax highlighting, and linting while marimo provides the reactive runtime in the browser.

### Exporting to Markdown & PDF

Export marimo notebooks to markdown for integration with documentation tools, static site generators, or PDF generation workflows.

**Basic export:**

```bash
# Export notebook to markdown (top-to-bottom order)
marimo export md notebook.py -o notebook.md

# Continuous export on file changes
marimo export md notebook.py -o notebook.md --watch
```

**PDF generation with Quarto:**

```bash
# Export to markdown, then render with Quarto
marimo export md analysis.py -o analysis.md
quarto render analysis.md --to pdf

# Also works for HTML, slides, and other Quarto formats
quarto render analysis.md --to html
quarto render analysis.md --to revealjs  # Slides
```

**For comprehensive Quarto publishing workflows, see the `quarto` skill.**

**Integration with other tools:**
- **Quarto**: Full support via [quarto-marimo plugin](https://github.com/marimo-team/quarto-marimo) - use `skill quarto` for details
- **MyST/Sphinx**: Works with MyST Markdown parser for documentation sites
- **Static site generators**: Exported markdown integrates with Hugo, Jekyll, MkDocs

**Note:** Exported markdown uses top-to-bottom cell order (not reactive/topological order). Convert back to marimo with `marimo convert notebook.md > notebook.py`.

### Markdown Storage Format

Marimo notebooks can be stored as `.md` files instead of `.py` files - useful for prose-heavy analyses or documentation-centric workflows.

**Structure:**

```markdown
---
title: My Analysis
marimo-version: 0.19.6
---

# Analysis Title

```python {.marimo}
import marimo as mo
mo.md("Your analysis here")
```
```

**When to use `.md` format:**
- Prose-heavy reports with minimal code
- Documentation that needs to render nicely on GitHub
- Integration with markdown-first workflows

**Limitations of `.md` format:**
- Cannot use reactive tests
- Cannot import functions from markdown notebooks
- Cannot run as scripts with `python notebook.md`
- Missing some advanced marimo features

**Recommendation for EPIST workflows:** Use `.py` format for full feature set (reactive execution, importable functions, script execution, testing). Reserve `.md` format for final reports or documentation.

**Learn more:** Run `marimo tutorial markdown-format` for complete guide.

## Installation

```bash
# Install marimo
uv tool install marimo

# Verify installation
marimo --version
```

## Quick Start

### Create a New Notebook

```bash
# Create and edit new notebook
marimo edit my_analysis.py

# Or create from template
marimo tutorial intro  # Interactive tutorial
```

### Marimo Notebook Structure

Every marimo notebook is a pure Python file:

```python
import marimo

__generated_with = "0.19.6"
app = marimo.App(width="medium")

@app.cell
def __():
    import marimo as mo
    import pandas as pd
    return mo, pd

@app.cell
def __(mo, pd):
    # Load data - this cell is reactive!
    df = pd.read_csv("data.csv")
    mo.md(f"Loaded {len(df)} rows")
    return df,

@app.cell
def __(df):
    # Automatically reruns when df changes!
    total = df['amount'].sum()
    return total,

if __name__ == "__main__":
    app.run()
```

**Key points:**
- Each `@app.cell` is a reactive cell
- Cells automatically rerun when dependencies change
- Returns determine what's available to other cells
- No hidden state - always deterministic

## Core Commands

```bash
# Edit notebook interactively
marimo edit notebook.py

# Run as app (read-only)
marimo run notebook.py

# Run as script (headless)
python notebook.py

# Export to HTML
marimo export html notebook.py -o report.html

# Export to PDF (via Jupyter)
marimo export ipynb notebook.py -o notebook.ipynb
uvx --with nbconvert --from jupyter-core jupyter nbconvert --to pdf notebook.ipynb

# Export to Markdown
marimo export md notebook.py -o notebook.md

# Watch and auto-export
marimo export html notebook.py -o report.html --watch
```

## Reactive Execution Model

### How Reactivity Works

```python
@app.cell
def __():
    # Cell 1: Input
    slider = mo.ui.slider(1, 100, value=50)
    return slider,

@app.cell
def __(slider):
    # Cell 2: Calculation (reruns when slider changes!)
    doubled = slider.value * 2
    return doubled,

@app.cell
def __(doubled):
    # Cell 3: Conclusion (reruns when doubled changes!)
    conclusion = "High" if doubled > 100 else "Low"
    return conclusion,
```

**When you move the slider:**
1. Cell 2 automatically reruns (uses `slider`)
2. Cell 3 automatically reruns (uses `doubled`)
3. No manual intervention needed!

### No Hidden State

Unlike Jupyter:
- ✅ Variables can't be defined multiple times
- ✅ Execution order is deterministic
- ✅ No stale values from old runs
- ✅ Always reproducible

```python
# This is NOT allowed in marimo (good!)
@app.cell
def __():
    x = 1
    return x,

@app.cell
def __():
    x = 2  # ❌ Error: x already defined!
    return x,
```

## Interactive Widgets

### Built-in UI Elements

```python
@app.cell
def __(mo):
    # Sliders
    age = mo.ui.slider(0, 100, value=25, label="Age")
    
    # Text input
    name = mo.ui.text(placeholder="Enter name")
    
    # Dropdown
    city = mo.ui.dropdown(["NYC", "SF", "LA"], value="NYC")
    
    # Checkbox
    agree = mo.ui.checkbox(label="I agree")
    
    # Date picker
    start_date = mo.ui.date(label="Start date")
    
    # File upload
    file_upload = mo.ui.file(filetypes=[".csv", ".json"])
    
    # Display together
    mo.vstack([age, name, city, agree, start_date, file_upload])
    return age, name, city, agree, start_date, file_upload
```

### Using Widget Values

```python
@app.cell
def __(age, name, city):
    # Access values with .value
    # This cell reruns when any widget changes!
    summary = f"{name.value} is {age.value} years old from {city.value}"
    return summary,
```

## EPIST Integration Patterns

### Pattern 1: Visual Fact Recording with Charts

**CRITICAL: Always visualize facts and conclusions, don't just record them.**

```python
@app.cell
def __():
    import marimo as mo
    from epist import FactRecorder
    import matplotlib.pyplot as plt
    
    recorder = FactRecorder("sales_analysis")
    return mo, recorder, plt

@app.cell
def __(recorder, mo):
    import pandas as pd
    
    df = pd.read_csv("sales.csv")
    
    # Record data source
    source_id = recorder.record_fact(
        "data_source",
        "sales.csv",
        description="Q4 2024 sales data"
    )
    
    # ✅ Visualize the data immediately
    mo.vstack([
        mo.md("## Sales Data Overview"),
        mo.ui.table(df.head(10)),
        mo.md(f"**Loaded {len(df):,} transactions**")
    ])
    
    return df, source_id

@app.cell
def __(df, recorder, source_id, plt, mo):
    # Calculate metric (reactive!)
    total_sales = df['sales'].sum()
    
    # Record fact
    fact_id = recorder.record_fact(
        "total_sales_q4",
        float(total_sales),
        source_id=source_id,
        calculation="df['sales'].sum()",
        description="Total sales for Q4 2024"
    )
    
    # ✅ VISUALIZE the trend, not just the number
    fig, ax = plt.subplots(figsize=(10, 6))
    df.groupby('date')['sales'].sum().plot(ax=ax, kind='line')
    ax.set_title('Q4 Sales Trend')
    ax.set_ylabel('Sales ($)')
    
    mo.vstack([
        mo.md(f"## Total Sales: ${total_sales:,.2f}"),
        fig
    ])
    
    return total_sales, fact_id

@app.cell
def __(recorder, total_sales, fact_id, mo):
    # Make conclusion (reactive!)
    if total_sales > 1000000:
        conclusion = "Exceeded target - excellent performance"
        status = "success"
        color = "green"
        icon = "✅"
    else:
        conclusion = "Below target - needs improvement"
        status = "warning"
        color = "orange"
        icon = "⚠️"
    
    # Record conclusion
    conclusion_id = recorder.record_conclusion(
        conclusion,
        fact_ids=[fact_id],
        status=status
    )
    
    # ✅ VISUAL conclusion, not just text
    mo.callout(
        mo.md(f"{icon} **{conclusion}**"),
        kind=status
    )
    
    return conclusion, conclusion_id
```

**Key advantages:**
- When data changes, all facts, conclusions, AND visualizations update automatically!
- Readers see insights immediately, not raw numbers
- Charts communicate trends that numbers alone cannot

### Pattern 2: Interactive Visual Analysis with Provenance

**Use widgets + charts for exploratory analysis, not print statements.**

```python
@app.cell
def __(mo):
    # Interactive date range selector with clear labels
    mo.md("## 📅 Select Analysis Period")
    
    start_date = mo.ui.date(label="Start Date")
    end_date = mo.ui.date(label="End Date")
    
    mo.hstack([start_date, end_date])
    return start_date, end_date

@app.cell
def __(df, start_date, end_date, recorder, mo):
    # Filter data (reactive to date changes!)
    filtered_df = df[
        (df['date'] >= start_date.value) & 
        (df['date'] <= end_date.value)
    ]
    
    # Record filtered dataset fact
    recorder.record_fact(
        "filtered_date_range",
        f"{start_date.value} to {end_date.value}",
        description="User-selected date range for analysis"
    )
    
    # ✅ SHOW the filtered data visually
    mo.vstack([
        mo.md(f"**Showing {len(filtered_df):,} transactions**"),
        mo.ui.table(filtered_df, selection="multi")
    ])
    
    return filtered_df,

@app.cell
def __(filtered_df, recorder, plt, mo):
    # Analysis on filtered data (reactive!)
    metrics = {
        "count": len(filtered_df),
        "total": filtered_df['amount'].sum(),
        "average": filtered_df['amount'].mean()
    }
    
    # Record each metric
    for key, value in metrics.items():
        recorder.record_fact(
            f"metric_{key}",
            float(value),
            description=f"{key.title()} for selected date range"
        )
    
    # ✅ VISUALIZE metrics with cards + chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Distribution
    filtered_df['amount'].hist(ax=ax1, bins=30)
    ax1.set_title('Transaction Distribution')
    ax1.axvline(metrics['average'], color='red', linestyle='--', label='Average')
    ax1.legend()
    
    # Time series
    filtered_df.groupby('date')['amount'].sum().plot(ax=ax2)
    ax2.set_title('Daily Totals')
    
    mo.vstack([
        mo.md(f"""
        ## 📊 Analysis Results
        
        - **Transactions**: {metrics['count']:,}
        - **Total Amount**: ${metrics['total']:,.2f}
        - **Average**: ${metrics['average']:,.2f}
        """),
        fig
    ])
    
    return metrics,
```

### Pattern 3: Complete EPIST Workflow

```python
@app.cell
def __():
    import marimo as mo
    import pandas as pd
    from epist import FactRecorder, record_conclusion
    from datetime import datetime
    
    # Initialize EPIST recorder
    analysis_name = f"customer_churn_{datetime.now().strftime('%Y%m%d')}"
    epist = FactRecorder(analysis_name)
    
    return mo, pd, epist, datetime

@app.cell
def __(pd, epist):
    # Load and record source
    df = pd.read_csv("customers.csv")
    
    source_fact = epist.record_fact(
        "customer_data_source",
        "customers.csv",
        source="production_database",
        timestamp=datetime.now(),
        checksum="abc123"  # In real usage, calculate actual checksum
    )
    
    return df, source_fact

@app.cell
def __(df, epist, source_fact):
    # Calculate churn rate (reactive!)
    total_customers = len(df)
    churned_customers = (df['status'] == 'churned').sum()
    churn_rate = churned_customers / total_customers
    
    # Record facts
    epist.record_fact(
        "total_customers",
        total_customers,
        source_ids=[source_fact],
        calculation="len(df)"
    )
    
    churn_fact = epist.record_fact(
        "churn_rate",
        float(churn_rate),
        source_ids=[source_fact],
        calculation="(df['status'] == 'churned').sum() / len(df)"
    )
    
    return total_customers, churned_customers, churn_rate, churn_fact

@app.cell
def __(churn_rate, churn_fact, epist, mo, df, plt):
    # Determine conclusion (reactive!)
    if churn_rate > 0.15:
        conclusion_text = f"HIGH RISK: Churn rate at {churn_rate:.1%}"
        severity = "danger"
        icon = "🚨"
    elif churn_rate > 0.10:
        conclusion_text = f"MODERATE: Churn rate at {churn_rate:.1%}"
        severity = "warn"
        icon = "⚠️"
    else:
        conclusion_text = f"HEALTHY: Churn rate at {churn_rate:.1%}"
        severity = "success"
        icon = "✅"
    
    # Record conclusion
    conclusion_id = epist.record_conclusion(
        conclusion_text,
        fact_ids=[churn_fact],
        severity=severity
    )
    
    # ✅ VISUALIZE the conclusion with context
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Churn rate gauge
    categories = df['status'].value_counts()
    ax1.pie(categories, labels=categories.index, autopct='%1.1f%%')
    ax1.set_title('Customer Status Distribution')
    
    # Trend over time (if date column exists)
    if 'date' in df.columns:
        churn_by_month = df[df['status'] == 'churned'].groupby(
            df['date'].dt.to_period('M')
        ).size()
        churn_by_month.plot(ax=ax2, kind='bar')
        ax2.set_title('Churn Trend by Month')
        ax2.set_xlabel('Month')
        ax2.set_ylabel('Churned Customers')
    
    mo.vstack([
        mo.callout(
            mo.md(f"{icon} **{conclusion_text}**"),
            kind=severity
        ),
        fig,
        mo.md("""
        ### Recommendations
        
        - Monitor high-risk customer segments
        - Review customer satisfaction metrics
        - Implement retention campaigns
        """)
    ])
    
    return conclusion_text, conclusion_id

@app.cell
def __(epist):
    # Save provenance chain
    epist.save("analysis_provenance.json")
    
    "✓ Provenance chain saved"
```

## Export Options

### Export to HTML

```bash
# Static HTML export
marimo export html analysis.py -o report.html

# With auto-watch
marimo export html analysis.py -o report.html --watch
```

**Output:** Self-contained HTML file with all outputs rendered

### Export to PDF

#### Method 1: Via Jupyter + nbconvert (Best quality)

```bash
# Export to notebook
marimo export ipynb analysis.py -o analysis.ipynb

# Convert to PDF (requires Pandoc + TeX)
uvx --with nbconvert --from jupyter-core \
    jupyter nbconvert --to pdf analysis.ipynb
```

#### Method 2: Via WebPDF (Easier setup)

```bash
# Export to notebook
marimo export ipynb analysis.py -o analysis.ipynb

# Convert to PDF with Chromium
uvx --with "nbconvert[webpdf]" --from jupyter-core \
    jupyter nbconvert --to webpdf analysis.ipynb --allow-chromium-download
```

#### Method 3: Via Quarto (Best formatting, multi-format support)

```bash
# Export to Markdown
marimo export md analysis.py -o analysis.md

# Render with Quarto (PDF, HTML, Word, slides)
quarto render analysis.md --to pdf
quarto render analysis.md --to html
quarto render analysis.md --to docx
quarto render analysis.md --to revealjs  # Slides
```

**For advanced Quarto features (custom themes, citations, cross-references), see `skill quarto`.**

#### Method 4: From Command Palette (Most convenient)

In marimo editor (v0.19.6+):
1. Enable "Better PDF Export" in Settings → Experimental
2. Press `Ctrl+K`
3. Select "Download as PDF"

### Export to Markdown

```bash
# Export as Markdown
marimo export md analysis.py -o analysis.md

# Compatible with Quarto, MyST, Pandoc
quarto render analysis.md
```

### Export to Jupyter Notebook

```bash
# Export to .ipynb format
marimo export ipynb analysis.py -o analysis.ipynb

# Can then use with Jupyter ecosystem tools
jupyter notebook analysis.ipynb
```

### Export to Python Script

```bash
# Export as flat Python script (topological order)
marimo export script analysis.py -o script.py

# Run the exported script
python script.py
```

### Export to WASM HTML (Self-contained interactive)

```bash
# Export as WebAssembly-powered HTML
marimo export html-wasm analysis.py -o output_dir --mode run

# Creates fully self-contained interactive HTML
# No server needed - runs in browser via WASM
```

## Common Patterns

### Pattern 0: Never Return Raw Data (Anti-Pattern Guide)

**CRITICAL: Marimo notebooks are for visual communication, not data dumps.**

```python
# ❌ ANTI-PATTERN: Returning raw dicts/JSON
@app.cell
def __(df):
    stats = {
        "mean": df['value'].mean(),
        "median": df['value'].median(),
        "std": df['value'].std()
    }
    stats  # Returns bare dict - hard to read

# ✅ CORRECT: Visual representation
@app.cell
def __(df, mo):
    stats = {
        "mean": df['value'].mean(),
        "median": df['value'].median(),
        "std": df['value'].std()
    }
    
    mo.md(f"""
    ## Distribution Statistics
    
    | Metric | Value |
    |--------|-------|
    | Mean | {stats['mean']:.2f} |
    | Median | {stats['median']:.2f} |
    | Std Dev | {stats['std']:.2f} |
    """)

# ❌ ANTI-PATTERN: print() statements
@app.cell
def __(df):
    print(f"Rows: {len(df)}")  # Doesn't update reactively!
    print(f"Columns: {len(df.columns)}")

# ✅ CORRECT: Markdown output
@app.cell
def __(df, mo):
    mo.md(f"""
    **Dataset Shape**: {len(df):,} rows × {len(df.columns)} columns
    """)

# ❌ ANTI-PATTERN: Bare dataframe (ugly)
@app.cell
def __(df):
    df  # Shows plain repr

# ✅ CORRECT: Interactive table
@app.cell
def __(df, mo):
    mo.ui.table(df, selection="multi")
```

### Data Loading and Visualization

```python
@app.cell
def __(mo):
    import pandas as pd
    import matplotlib.pyplot as plt
    return pd, plt

@app.cell
def __(pd, mo):
    # Load data
    df = pd.read_csv("data.csv")
    
    # ✅ Show what you loaded
    mo.md(f"Loaded **{len(df):,}** rows from `data.csv`")
    
    return df,

@app.cell
def __(df, plt):
    # Create visualization
    fig, ax = plt.subplots(figsize=(10, 6))
    df.plot(x='date', y='value', ax=ax)
    ax.set_title('Data Over Time')
    fig
    return fig, ax

@app.cell
def __(df, mo):
    # Interactive data explorer
    mo.ui.table(df, selection="single")
```

### Parameterized Reports

```python
@app.cell
def __(mo):
    # Parameters at top
    date_range = mo.ui.date_range()
    metric_selector = mo.ui.dropdown(
        ["Revenue", "Profit", "Customers"],
        value="Revenue"
    )
    
    mo.vstack([
        mo.md("## Report Parameters"),
        date_range,
        metric_selector
    ])
    return date_range, metric_selector

@app.cell
def __(date_range, metric_selector, df):
    # Filter data based on parameters
    filtered = df[
        (df['date'] >= date_range.value[0]) &
        (df['date'] <= date_range.value[1])
    ]
    
    # Select metric
    metric_col = metric_selector.value.lower()
    result = filtered[metric_col].sum()
    
    return filtered, result

@app.cell
def __(metric_selector, result, mo):
    # Display result
    mo.md(f"**{metric_selector.value}:** ${result:,.2f}")
```

### Multiple Data Sources

```python
@app.cell
def __(pd):
    # Load multiple sources
    sales = pd.read_csv("sales.csv")
    costs = pd.read_csv("costs.csv")
    inventory = pd.read_csv("inventory.csv")
    
    return sales, costs, inventory

@app.cell
def __(sales, costs):
    # Join data (reactive to both sources)
    merged = sales.merge(costs, on='product_id', how='left')
    profit = merged['sales'] - merged['costs']
    merged['profit'] = profit
    
    return merged, profit

@app.cell
def __(merged, inventory):
    # Further joins (reactive to all sources)
    final = merged.merge(inventory, on='product_id')
    return final,
```

### Conditional Outputs

```python
@app.cell
def __(mo):
    show_details = mo.ui.checkbox(label="Show detailed analysis")
    return show_details,

@app.cell
def __(show_details, detailed_analysis, summary, mo):
    # Conditionally show content
    if show_details.value:
        mo.vstack([
            mo.md("## Detailed Analysis"),
            detailed_analysis
        ])
    else:
        mo.md("## Summary\n\n" + summary)
```

## Best Practices

### 1. Visualize Everything (Most Important!)

```python
# ❌ BAD: Returning raw data structures
@app.cell
def __(df):
    summary = {
        "total": df['amount'].sum(),
        "count": len(df),
        "avg": df['amount'].mean()
    }
    summary  # Just shows dict

# ✅ GOOD: Visual representation
@app.cell
def __(df, mo, plt):
    summary = {
        "total": df['amount'].sum(),
        "count": len(df),
        "avg": df['amount'].mean()
    }
    
    # Create visualization
    fig, ax = plt.subplots()
    ax.bar(summary.keys(), summary.values())
    ax.set_title('Summary Metrics')
    
    mo.vstack([
        mo.md(f"""
        ## Summary Statistics
        
        - **Total**: ${summary['total']:,.2f}
        - **Count**: {summary['count']:,}
        - **Average**: ${summary['avg']:,.2f}
        """),
        fig
    ])

# ✅ ALSO GOOD: Interactive table for exploration
@app.cell
def __(df, mo):
    mo.ui.table(df, selection="multi")

# ✅ ALSO GOOD: Tree view for nested data (not bare dict!)
@app.cell
def __(complex_dict, mo):
    mo.tree(complex_dict)  # Collapsible tree, not raw dict
```

### 2. Cell Organization

```python
# Good: One logical operation per cell
@app.cell
def __():
    import marimo as mo
    import pandas as pd
    import matplotlib.pyplot as plt
    return mo, pd, plt

@app.cell
def __(pd):
    df = pd.read_csv("data.csv")
    return df,

@app.cell
def __(df, mo, plt):
    total = df['amount'].sum()
    
    # Visualize immediately
    mo.md(f"**Total**: ${total:,.2f}")
    return total,

# Bad: Too much in one cell
@app.cell
def __():
    import marimo as mo
    import pandas as pd
    df = pd.read_csv("data.csv")
    total = df['amount'].sum()
    avg = df['amount'].mean()
    # ... more code
    return mo, pd, df, total, avg
```

### 2. Choose the Right Visualization

```python
# For distributions → Histogram
@app.cell
def __(df, plt):
    fig, ax = plt.subplots()
    df['amount'].hist(ax=ax, bins=30)
    ax.set_title('Amount Distribution')
    fig

# For trends → Line chart
@app.cell
def __(df, plt):
    fig, ax = plt.subplots()
    df.groupby('date')['value'].sum().plot(ax=ax)
    ax.set_title('Value Over Time')
    fig

# For comparisons → Bar chart
@app.cell
def __(df, plt):
    fig, ax = plt.subplots()
    df.groupby('category')['amount'].sum().plot(kind='bar', ax=ax)
    ax.set_title('Amount by Category')
    fig

# For proportions → Pie chart
@app.cell
def __(df, plt):
    fig, ax = plt.subplots()
    df['category'].value_counts().plot(kind='pie', ax=ax, autopct='%1.1f%%')
    ax.set_title('Category Distribution')
    fig

# For tabular exploration → Interactive table
@app.cell
def __(df, mo):
    mo.ui.table(df.head(100), selection="multi")

# For metrics → Formatted markdown with callouts
@app.cell
def __(metrics, mo):
    mo.callout(
        mo.md(f"""
        **Revenue**: ${metrics['revenue']:,.2f}  
        **Growth**: {metrics['growth']:+.1%}
        """),
        kind="success" if metrics['growth'] > 0 else "warn"
    )
```

### 3. Return Explicitly

```python
# Good: Return what you need
@app.cell
def __(df):
    total = df['amount'].sum()
    return total,  # Available to other cells

# Bad: Not returning
@app.cell
def __(df):
    total = df['amount'].sum()
    # total not available to other cells!
```

### 3. Use Markdown for Narrative

```python
@app.cell
def __(mo):
    mo.md(
        """
        # Analysis Overview
        
        This analysis examines Q4 2024 sales data to identify:
        - Revenue trends
        - Top performing products
        - Regional variations
        """
    )
```

### 4. Leverage Reactivity

```python
# Good: Let reactivity work for you
@app.cell
def __(mo):
    threshold = mo.ui.slider(0, 100, value=50)
    return threshold,

@app.cell
def __(df, threshold):
    # Automatically updates when threshold changes!
    filtered = df[df['score'] > threshold.value]
    return filtered,

# Bad: Manual updates
# Don't use buttons to trigger recalculation
# (marimo does it automatically)
```

### 5. EPIST Integration with Visual Provenance

```python
# ✅ GOOD: Record facts AND visualize them
@app.cell
def __(df, epist, mo, plt):
    total = df['amount'].sum()
    epist.record_fact("total", total, source="df")
    
    # Show the fact visually with context
    fig, ax = plt.subplots()
    df['amount'].plot(ax=ax)
    ax.axhline(total, color='red', linestyle='--', label=f'Total: ${total:,.0f}')
    ax.legend()
    
    mo.vstack([
        mo.md(f"### Total Amount: ${total:,.2f}"),
        fig
    ])
    
    return total,

# ❌ BAD: Recording without visualization
@app.cell
def __(df, epist):
    total = df['amount'].sum()
    epist.record_fact("total", total, source="df")
    total  # Just returns number
    return total,

# ❌ BAD: Recording separately from calculation
# (harder to maintain provenance)
```

## Troubleshooting

### Multiple Definition Error

```python
# Error: x is defined in multiple cells
@app.cell
def __():
    x = 1
    return x,

@app.cell
def __():
    x = 2  # ❌ Error!
    return x,

# Solution: Use different names
@app.cell
def __():
    x1 = 1
    return x1,

@app.cell
def __():
    x2 = 2
    return x2,
```

### Cyclic Dependency

```python
# Error: Cyclic dependency
@app.cell
def __(y):  # Uses y
    x = y + 1
    return x,

@app.cell
def __(x):  # Uses x
    y = x + 1  # ❌ Cycle!
    return y,

# Solution: Break the cycle
@app.cell
def __():
    x = 1  # Start value
    return x,

@app.cell
def __(x):
    y = x + 1
    return y,
```

### Package Not Found

```bash
# Install packages marimo needs
uv pip install pandas matplotlib numpy

# Or use marimo's package manager
# Click "Packages" in the marimo editor
```

## Version Control

### Git-Friendly Format

Marimo notebooks are pure Python:
```python
# .py file - clean git diffs!
import marimo

@app.cell
def __():
    import marimo as mo
    return mo,
```

### .gitignore Recommendations

```gitignore
# Marimo auto-saved snapshots (optional)
__marimo__/

# Exported outputs (optional)
*.ipynb
*.html
```

### Commit Best Practices

```bash
# Marimo notebooks are just Python files
git add analysis.py
git commit -m "Add Q4 sales analysis"

# Diffs are readable!
git diff analysis.py
```

## Integration with Other Tools

### With DuckDB

```python
@app.cell
def __():
    import duckdb
    return duckdb,

@app.cell
def __(duckdb):
    # Query CSV directly
    result = duckdb.query("""
        SELECT category, SUM(amount) as total
        FROM 'sales.csv'
        GROUP BY category
    """).df()
    
    return result,
```

### With Quarto

```bash
# Export to Markdown
marimo export md analysis.py -o analysis.md

# Render with Quarto
quarto render analysis.md --to html
quarto render analysis.md --to pdf
```

### With Jupyter Ecosystem

```bash
# Export to Jupyter format
marimo export ipynb analysis.py -o analysis.ipynb

# Use with nbconvert, nbgrader, etc.
jupyter nbconvert --to html analysis.ipynb
```

## Quick Reference

### Common Commands

```bash
marimo edit notebook.py          # Edit interactively
marimo run notebook.py           # Run as app
python notebook.py               # Run as script
marimo export html notebook.py   # Export to HTML
marimo export md notebook.py     # Export to Markdown
marimo export ipynb notebook.py  # Export to Jupyter
marimo tutorial intro            # Interactive tutorial
```

### Widget Gallery

```python
mo.ui.slider(0, 100, value=50)                    # Slider
mo.ui.text(placeholder="Enter text")              # Text input
mo.ui.number(value=42)                            # Number input
mo.ui.dropdown(["A", "B", "C"])                   # Dropdown
mo.ui.checkbox(label="Agree")                     # Checkbox
mo.ui.radio(["Option 1", "Option 2"])             # Radio buttons
mo.ui.date(label="Pick date")                     # Date picker
mo.ui.file(filetypes=[".csv"])                    # File upload
mo.ui.table(df)                                   # Interactive table
mo.ui.button(label="Click me")                    # Button
```

### Layout Helpers

```python
mo.vstack([item1, item2])         # Vertical stack
mo.hstack([item1, item2])         # Horizontal stack
mo.accordion({"Section": content}) # Accordion
mo.tabs({"Tab1": content})        # Tabs
mo.callout(content, kind="info")  # Callout box
```

## Resources

- Official docs: https://docs.marimo.io
- GitHub: https://github.com/marimo-team/marimo
- Tutorial: `marimo tutorial intro`
- Examples: https://marimo.io/examples
- Discord: https://marimo.io/discord
