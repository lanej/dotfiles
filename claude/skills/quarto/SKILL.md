---
name: quarto
description: Render computational documents to publication-quality PDF, HTML, Word, and presentations using Quarto. Use for static reports, multi-format publishing, scientific documents with citations/cross-references, or exporting marimo/Jupyter notebooks. Triggers on "render PDF", "publish document", "create presentation", "quarto render", or multi-format publishing needs.
---

# Quarto Skill

Quarto is an open-source scientific and technical publishing system built on Pandoc. It renders computational documents (with Python, R, Julia code) to publication-quality output in multiple formats.

## When to Use Quarto

**Perfect for:**
- Static reports and documentation (no interactivity needed)
- Multi-format publishing (PDF + HTML + Word from single source)
- Scientific documents (equations, citations, cross-references)
- Presentations (RevealJS HTML slides, PowerPoint, Beamer PDF)
- Websites and blogs (multi-page projects)
- EPIST provenance in static reports
- Exporting marimo/Jupyter notebooks for publication

**NOT for:**
- Interactive dashboards (use marimo `run` mode or Shiny)
- Reactive exploration during development (use marimo `edit` mode)
- Real-time data updates (use marimo or web dashboards)
- When you need widgets/sliders for end users (use marimo WASM export)

## Decision Tree: Quarto vs Alternatives

```
Need user interactivity? (sliders, dropdowns, real-time updates)
├─ YES → Use marimo (edit/run mode or WASM export)
└─ NO → Static output needed
   │
   ├─ Complex multi-page documentation site?
   │  └─ YES → Use Quarto website/book projects
   │
   ├─ Single analysis with code + results?
   │  ├─ Pure Python required (run as script)?
   │  │  └─ YES → marimo → export md → quarto render
   │  └─ NO → Native Quarto .qmd files (recommended)
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
author: "Your Name"
date: "2024-01-30"
format:
  pdf:
    toc: true
    number-sections: true
  html:
    code-fold: true
---

## Data Loading

```{python}
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("sales.csv")
print(f"Loaded {len(df)} rows")
df.head()
```

## Analysis

```{python}
total_sales = df['sales'].sum()
print(f"Total: ${total_sales:,.2f}")

# Visualization
fig, ax = plt.subplots(figsize=(10, 6))
df.groupby('date')['sales'].sum().plot(ax=ax)
ax.set_title('Sales Trend')
plt.show()
```

## Conclusion

Total sales for Q4: **${total_sales:,.2f}**
EOF

# Render to PDF
quarto render analysis.qmd --to pdf

# Render to HTML
quarto render analysis.qmd --to html

# Render to Word
quarto render analysis.qmd --to docx
```

### File Formats Quarto Can Render

**Input formats:**
- `.qmd` - Quarto markdown (native, recommended)
- `.ipynb` - Jupyter notebooks
- `.md` - Plain markdown (no code execution)
- `.Rmd` - R Markdown files

**Output formats:**
- **Documents**: PDF, HTML, Word, ODT, ePub, Typst
- **Presentations**: RevealJS (HTML), PowerPoint, Beamer (PDF)
- **Websites**: Multi-page sites, blogs, books
- **Dashboards**: Interactive dashboards (with Shiny or Observable JS)

## Core Commands

```bash
# Render document
quarto render document.qmd                    # Default format
quarto render document.qmd --to pdf          # Specific format
quarto render document.qmd --to html --toc   # With options

# Render Jupyter notebook
quarto render notebook.ipynb --to pdf

# Render plain markdown (no code execution)
quarto render README.md --to pdf

# Multiple formats at once
quarto render document.qmd --to pdf,html,docx

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

## YAML Frontmatter

### Simple Document

```yaml
---
title: "My Report"
author: "Your Name"
date: "2024-01-30"
format: pdf
---
```

### Multiple Formats

```yaml
---
title: "Analysis Report"
format:
  html:
    toc: true
    code-fold: true
    theme: cosmo
  pdf:
    toc: true
    number-sections: true
    geometry: margin=1in
  docx:
    reference-doc: template.docx
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

```yaml
---
format:
  html:
    theme: cosmo  # or flatly, darkly, journal, minty, etc.
    css: custom.css
    toc: true
    toc-location: left
    code-fold: show
    code-tools: true
---
```

### Dark Mode with Auto-Dark Extension

**Install auto-dark extension:**

```bash
# In your project directory
quarto add gadenbuie/quarto-auto-dark --no-prompt
```

**Use in document:**

```yaml
---
title: "My Analysis"
format:
  html:
    theme:
      dark: darkly      # Theme for dark mode
      light: flatly     # Theme for light mode
filters:
  - auto-dark          # Automatically switch based on system preference
---
```

**Available dark themes:**
- `darkly` - Dark Bootstrap theme (recommended)
- `cyborg` - Dark blue theme
- `slate` - Dark gray theme
- `solar` - Dark solarized theme
- `superhero` - Dark comic book theme
- `vapor` - Dark retro theme

**Light themes:**
- `flatly` - Clean modern theme (recommended)
- `cosmo` - Friendly blue theme
- `lumen` - Light gray theme
- `sandstone` - Warm sandy theme
- `minty` - Fresh mint theme
- `journal` - Newspaper style

The `auto-dark` filter automatically detects system dark mode preference and switches themes accordingly.

## EPIST Integration

**EPIST works seamlessly in Quarto documents:**

```qmd
---
title: "Customer Churn Analysis"
format:
  pdf:
    toc: true
---

## Setup

```{python}
import pandas as pd
from epist import FactRecorder

# Initialize EPIST
recorder = FactRecorder("churn_analysis_2024")
```

## Data Loading

```{python}
df = pd.read_csv("customers.csv")

# Record data source
source_id = recorder.record_fact(
    "data_source",
    "customers.csv",
    description="Customer database snapshot",
    checksum="abc123"
)

print(f"Loaded {len(df):,} customers")
```

## Analysis

```{python}
#| label: fig-churn
#| fig-cap: "Churn rate over time"

# Calculate churn rate
total_customers = len(df)
churned = (df['status'] == 'churned').sum()
churn_rate = churned / total_customers

# Record fact
churn_fact_id = recorder.record_fact(
    "churn_rate",
    float(churn_rate),
    source_ids=[source_id],
    calculation="(df['status'] == 'churned').sum() / len(df)"
)

# Visualize
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(10, 6))
df['status'].value_counts().plot(kind='pie', ax=ax, autopct='%1.1f%%')
ax.set_title('Customer Status Distribution')
plt.show()
```

**Churn Rate**: `{python} f"{churn_rate:.1%}"`

## Conclusion

```{python}
# Determine conclusion
if churn_rate > 0.15:
    conclusion = f"HIGH RISK: Churn rate at {churn_rate:.1%}"
    severity = "critical"
elif churn_rate > 0.10:
    conclusion = f"MODERATE: Churn rate at {churn_rate:.1%}"
    severity = "warning"
else:
    conclusion = f"HEALTHY: Churn rate at {churn_rate:.1%}"
    severity = "normal"

# Record conclusion
conclusion_id = recorder.record_conclusion(
    conclusion,
    fact_ids=[churn_fact_id],
    severity=severity
)

# Save provenance
recorder.save("churn_provenance.json")

print(f"**{conclusion}**")
```
```

**Key Points:**
- EPIST tracks provenance just like in marimo
- No reactivity (re-render document to update)
- Provenance saved to JSON for external use
- Visualizations + facts = complete story

## Marimo Integration

### Workflow: Marimo → Quarto

**When to use this:**
- Developed interactive analysis in marimo
- Need publication-quality static output
- Want multiple formats (PDF + HTML + Word)

**Process:**

```bash
# 1. Develop in marimo (interactive)
marimo edit analysis.py

# 2. Export to markdown
marimo export md analysis.py -o analysis.md

# 3. Add Quarto frontmatter (optional)
cat > final.qmd << 'EOF'
---
title: "Sales Analysis"
format:
  pdf:
    toc: true
  html:
    code-fold: true
---
EOF
cat analysis.md >> final.qmd

# 4. Render with Quarto
quarto render final.qmd --to pdf
quarto render final.qmd --to html
```

### Automated Pipeline

```bash
# Watch marimo, auto-export, auto-render
marimo export md analysis.py -o analysis.md --watch &
quarto preview analysis.md
```

### Limitations of Marimo → Quarto Export

**What works:**
- ✅ Static outputs (charts, tables, text)
- ✅ Code syntax highlighting
- ✅ Markdown formatting
- ✅ EPIST provenance (static snapshot)

**What doesn't work:**
- ❌ Interactive widgets (`mo.ui.*` components)
- ❌ Reactive updates (rendered once)
- ❌ Live data exploration

**Recommendation:**
- **Development**: Use `marimo edit` for interactive exploration
- **Sharing (interactive)**: Use `marimo run` or WASM export
- **Publishing (static)**: Export to markdown → Quarto render

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

**Quarto as a Pipeline Component:**

```bash
# Composition pattern: process → transform → render
conform notes.txt --schema schema.json | \
  jq '.items[]' | \
  python generate_qmd.py > report.qmd && \
  quarto render report.qmd --to pdf

# Marimo → Quarto → Distribution
marimo export md analysis.py | \
  quarto render /dev/stdin --to pdf --output report.pdf
```

**Do One Thing Well:**
- Quarto: Document rendering + format conversion
- NOT: Data analysis, interactive exploration, storage
- Delegate: Python for analysis, marimo for interactivity, Quarto for rendering

**Text Streams:**
```bash
# Quarto accepts stdin
cat document.md | quarto render - --to pdf --output report.pdf

# Pipe through processing
cat data.json | \
  jq -r '.[] | "- \(.item)"' | \
  quarto render /dev/stdin --to html
```

**Silent Success:**
```bash
# Quarto is quiet on success
quarto render doc.qmd --to pdf
echo $?  # 0 = success

# Use --quiet for scripts
quarto render doc.qmd --to pdf --quiet
```

## Common Patterns

### Pattern 1: Single Source, Multiple Formats

```bash
# Render all formats
quarto render report.qmd --to pdf,html,docx

# Or explicitly
quarto render report.qmd --to pdf
quarto render report.qmd --to html
quarto render report.qmd --to docx
```

### Pattern 2: Batch Processing

```bash
# Render all .qmd files in directory
for file in *.qmd; do
  quarto render "$file" --to pdf
done

# Or use find
find . -name "*.qmd" -exec quarto render {} --to pdf \;
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
quarto render report.qmd -P month:February -P year:2024
```

### Pattern 5: EPIST Provenance Reports

```bash
# Generate analysis with provenance
python analysis.py > data.json

# Create Quarto report referencing provenance
cat > report.qmd << 'EOF'
---
title: "Analysis Report"
---

```{python}
import json
with open('data.json') as f:
    data = json.load(f)
# Render findings
```
EOF

quarto render report.qmd --to pdf
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

**Use marimo → `.md` when:**
- Developed interactively in marimo
- Need pure Python files
- Want reactive development

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
*.docx
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
--to pdf            # PDF via LaTeX or typst
--to html           # HTML
--to docx           # Microsoft Word
--to revealjs       # HTML slides
--to pptx           # PowerPoint
--to typst          # Typst (modern LaTeX alternative)
--to markdown       # GitHub-flavored markdown
--to epub           # eBook
```

### Common YAML Frontmatter

```yaml
---
title: "Document Title"
author: "Author Name"
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
