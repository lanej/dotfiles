# Marimo + EPIST Demo

This directory demonstrates **marimo** as a superior alternative to MyST-NB for EPIST data analysis workflows.

## What is Marimo?

[Marimo](https://marimo.io) is a reactive Python notebook that's designed to be:
- **Pure Python** - notebooks are `.py` files, not JSON
- **Reactive** - cells re-execute automatically when dependencies change
- **Reproducible** - no hidden state, deterministic execution
- **Git-friendly** - plain text format with clean diffs
- **Versatile** - run as script, app, or export to multiple formats

## Why Marimo > MyST-NB for EPIST?

| Feature | Marimo | MyST-NB |
|---------|--------|---------|
| **Single-file execution** | ✅ Perfect | ❌ Requires full Sphinx project |
| **EPIST integration** | ✅ Direct Python imports | ⚠️ Requires workarounds |
| **Version control** | ✅ Pure `.py` files | ✅ Text-based `.md` |
| **Run as script** | ✅ `python notebook.py` | ❌ Not supported |
| **Reactive execution** | ✅ Auto-updates | ❌ Manual re-run |
| **PDF export** | ✅ Via Jupyter/nbconvert | ✅ Via Sphinx |
| **Learning curve** | ✅ Low (if know Python) | ⚠️ Medium (Sphinx/MyST syntax) |

## Demo Files

### 1. `simple_epist_demo.py`
Interactive demo showing:
- Reactive calculations with sliders
- EPIST fact recording
- Automatic conclusion updates
- Provenance tracking

**Run it:**
```bash
# Edit interactively
marimo edit simple_epist_demo.py

# Run as app
marimo run simple_epist_demo.py

# Run as script
python simple_epist_demo.py

# Export to HTML
marimo export html simple_epist_demo.py -o output.html

# Export to Markdown
marimo export md simple_epist_demo.py -o output.md
```

### 2. `epist_analysis_demo.py`
Full data analysis demo with:
- Pandas DataFrame operations
- Matplotlib visualizations
- EPIST provenance chains
- Metric calculations
- Automated conclusions

**Requires pandas & matplotlib:**
```bash
uv pip install pandas matplotlib

# Then run
marimo edit epist_analysis_demo.py
```

## Exporting to PDF

Marimo supports PDF export via multiple methods:

### Method 1: Via Jupyter Notebook (Requires Pandoc & TeX)

```bash
# Export to Jupyter notebook
marimo export ipynb simple_epist_demo.py -o demo.ipynb

# Convert to PDF with nbconvert
uv pip install nbconvert
uvx --with nbconvert --from jupyter-core jupyter nbconvert --to pdf demo.ipynb
```

### Method 2: Via WebPDF (Easier - uses Chromium)

```bash
# Install nbconvert with webpdf support
uv pip install "nbconvert[webpdf]"

# Export to notebook then PDF
marimo export ipynb simple_epist_demo.py -o demo.ipynb
uvx --with "nbconvert[webpdf]" --from jupyter-core \
    jupyter nbconvert --to webpdf demo.ipynb --allow-chromium-download
```

### Method 3: Via Quarto (Best quality)

```bash
# Export to markdown
marimo export md simple_epist_demo.py -o demo.md

# Convert with Quarto
quarto render demo.md --to pdf
```

### Method 4: From Command Palette (Experimental)

In marimo editor (v0.19.6+):
1. Enable "Better PDF Export" in Settings → Experimental
2. Press Ctrl+K
3. Select "Download as PDF"

## EPIST Integration Pattern

Marimo's pure Python format makes EPIST integration trivial:

```python
import marimo as mo
import epist

# Cell 1: Load data
df = load_data("sales.csv")
source_id = epist.record_source("sales.csv")

# Cell 2: Calculate metric (reactive!)
total_sales = df["sales"].sum()
fact_id = epist.record_fact(
    "total_sales",
    total_sales,
    source_ids=[source_id],
    calculation="df['sales'].sum()"
)

# Cell 3: Make conclusion (reactive - updates when total_sales changes!)
conclusion = "Exceeded target" if total_sales > 1000000 else "Below target"
epist.record_conclusion(conclusion, fact_ids=[fact_id])
```

When data changes, **everything updates automatically** - calculations, conclusions, and EPIST provenance chains!

## Key Advantages for EPIST Workflows

### 1. Direct Integration
No need for YAML frontmatter or special directives. Just `import epist` and use it.

### 2. Reactive Provenance
When source data changes, all dependent facts and conclusions update automatically. Your provenance chain stays consistent.

### 3. Scriptable
Can run marimo notebooks as regular Python scripts:
```python
# analysis.py (marimo notebook)
if __name__ == "__main__":
    # Runs the entire analysis
    app.run()
```

### 4. No Hidden State
Unlike Jupyter, marimo enforces a dependency graph. No stale values, no run-order bugs.

### 5. Single-File Execution
No need for `_toc.yml`, `conf.py`, or project structure. Each analysis is self-contained.

## Comparison Table: Full Feature Set

| Feature | Marimo | MyST-NB | Quarto |
|---------|--------|---------|--------|
| Pure Python notebooks | ✅ | ❌ | ⚠️ (works with .ipynb) |
| Reactive execution | ✅ | ❌ | ❌ |
| Single-file workflow | ✅ | ❌ | ✅ |
| Version control friendly | ✅ | ✅ | ✅ |
| Run as script | ✅ | ❌ | ⚠️ (limited) |
| Interactive widgets | ✅ | ⚠️ (limited) | ✅ |
| HTML export | ✅ | ✅ | ✅ |
| PDF export | ✅ | ✅ | ✅ |
| Markdown export | ✅ | ✅ | ✅ |
| WASM/offline HTML | ✅ | ❌ | ⚠️ (limited) |
| No hidden state | ✅ | ❌ | ❌ |
| Direct EPIST integration | ✅ | ⚠️ | ⚠️ |
| Learning curve | Low | Medium | Medium |

## Next Steps

1. **Try the demos:**
   ```bash
   cd ~/marimo-epist-demo
   marimo edit simple_epist_demo.py
   ```

2. **Create your own EPIST analysis:**
   ```bash
   marimo edit my_analysis.py
   ```

3. **Export to share:**
   ```bash
   marimo export html my_analysis.py -o report.html
   ```

## Resources

- [Marimo Documentation](https://docs.marimo.io)
- [Marimo GitHub](https://github.com/marimo-team/marimo)
- [Export Guide](https://docs.marimo.io/guides/exporting.html)
- [Tutorial](https://docs.marimo.io/getting_started/tutorial.html)

## Installation

```bash
# Install marimo
uv tool install marimo

# Optional: data science packages
uv pip install pandas matplotlib numpy
```

## Conclusion

For EPIST workflows requiring:
- Ad-hoc single-file analysis
- Direct Python integration
- Reactive updates
- Clean version control
- Multiple export formats

**Marimo is the clear winner over MyST-NB.**

Choose MyST-NB only if you specifically need:
- Sphinx integration for large documentation projects
- MyST Markdown syntax features
- Cross-referencing across multiple documents
