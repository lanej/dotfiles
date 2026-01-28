---
name: marimo
description: Create reactive Python notebooks with marimo for data analysis and EPIST provenance tracking. Use for ad-hoc analysis, interactive reports, reproducible research with automatic reactivity. Triggers on "notebook", "reactive notebook", "data analysis", "interactive analysis", "EPIST analysis", "computational narrative", or single-file analysis workflows. STRONGLY PREFERRED over MyST-NB for EPIST workflows.
---

# Marimo Skill

Marimo is a reactive Python notebook that runs as a pure `.py` file. Perfect for EPIST data analysis workflows where you need single-file execution, automatic reactivity, and direct Python integration.

## When to Use Marimo

**Perfect for:**
- EPIST data analysis with provenance tracking
- Ad-hoc single-file analysis (no project scaffolding needed)
- Interactive reports with sliders/widgets
- Reproducible research with automatic updates
- Version-controlled analysis (git-friendly `.py` files)
- Analyses that need to run as scripts
- No hidden state - deterministic execution

**NOT for:**
- Large multi-document documentation sites (use Quarto/Jupyter Book)
- Static content without computation (use Markdown)
- When you specifically need Jupyter notebook format

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

### Pattern 1: Simple Fact Recording

```python
@app.cell
def __():
    import marimo as mo
    from epist import FactRecorder
    
    recorder = FactRecorder("sales_analysis")
    return mo, recorder

@app.cell
def __(recorder):
    import pandas as pd
    
    df = pd.read_csv("sales.csv")
    
    # Record data source
    source_id = recorder.record_fact(
        "data_source",
        "sales.csv",
        description="Q4 2024 sales data"
    )
    
    return df, source_id

@app.cell
def __(df, recorder, source_id):
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
    
    return total_sales, fact_id

@app.cell
def __(recorder, total_sales, fact_id):
    # Make conclusion (reactive - updates when total_sales changes!)
    if total_sales > 1000000:
        conclusion = "Exceeded target - excellent performance"
        status = "success"
    else:
        conclusion = "Below target - needs improvement"
        status = "warning"
    
    # Record conclusion
    conclusion_id = recorder.record_conclusion(
        conclusion,
        fact_ids=[fact_id],
        status=status
    )
    
    return conclusion, conclusion_id
```

**Key advantage:** When data changes, all facts and conclusions update automatically!

### Pattern 2: Interactive Analysis with Provenance

```python
@app.cell
def __(mo):
    # Interactive date range selector
    start_date = mo.ui.date(label="Start Date")
    end_date = mo.ui.date(label="End Date")
    
    mo.hstack([start_date, end_date])
    return start_date, end_date

@app.cell
def __(df, start_date, end_date, recorder):
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
    
    return filtered_df,

@app.cell
def __(filtered_df, recorder):
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
def __(churn_rate, churn_fact, epist, mo):
    # Determine conclusion (reactive!)
    if churn_rate > 0.15:
        conclusion_text = f"HIGH RISK: Churn rate at {churn_rate:.1%}"
        severity = "critical"
        color = "red"
    elif churn_rate > 0.10:
        conclusion_text = f"MODERATE: Churn rate at {churn_rate:.1%}"
        severity = "warning"
        color = "orange"
    else:
        conclusion_text = f"HEALTHY: Churn rate at {churn_rate:.1%}"
        severity = "normal"
        color = "green"
    
    # Record conclusion
    conclusion_id = epist.record_conclusion(
        conclusion_text,
        fact_ids=[churn_fact],
        severity=severity
    )
    
    # Display with styling
    mo.md(f"## Assessment\n\n**{conclusion_text}**").style({"color": color})
    
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

#### Method 3: Via Quarto (Best formatting)

```bash
# Export to Markdown
marimo export md analysis.py -o analysis.md

# Render with Quarto
quarto render analysis.md --to pdf
```

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

### Data Loading and Visualization

```python
@app.cell
def __(mo):
    import pandas as pd
    import matplotlib.pyplot as plt
    return pd, plt

@app.cell
def __(pd):
    # Load data
    df = pd.read_csv("data.csv")
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

### 1. Cell Organization

```python
# Good: One logical operation per cell
@app.cell
def __():
    import marimo as mo
    import pandas as pd
    return mo, pd

@app.cell
def __(pd):
    df = pd.read_csv("data.csv")
    return df,

@app.cell
def __(df):
    total = df['amount'].sum()
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

### 2. Return Explicitly

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

### 5. EPIST Integration

```python
# Good: Record facts as you calculate
@app.cell
def __(df, epist):
    total = df['amount'].sum()
    epist.record_fact("total", total, source="df")
    return total,

# Bad: Recording separately from calculation
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
