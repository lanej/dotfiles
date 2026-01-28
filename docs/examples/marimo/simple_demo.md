---
title: Simple Epist Demo
marimo-version: 0.19.6
width: medium
---

```python {.marimo}
import marimo as mo
```

# Marimo + EPIST Demo

This demonstrates marimo's key advantages for EPIST workflows:

1. **Pure Python** - Direct EPIST integration
2. **Reactive execution** - Everything updates automatically
3. **Single-file execution** - No project required
4. **Version control friendly** - Plain `.py` file
5. **Multiple export formats** - HTML, PDF, Markdown, Jupyter

Try changing the values below and watch everything update!
<!---->
## Interactive Inputs

```python {.marimo}
# Interactive sliders for data
revenue_slider = mo.ui.slider(
    start=100000, stop=1000000, value=500000, step=10000, label="Revenue ($)"
)

cost_slider = mo.ui.slider(
    start=50000, stop=800000, value=300000, step=10000, label="Costs ($)"
)

mo.vstack([revenue_slider, cost_slider])
```

## Simulated EPIST Integration

```python {.marimo}
# Simulated EPIST module for demo
class SimpleFactRecorder:
    def __init__(self):
        self.facts = []

    def record_fact(self, name, value, calculation=None):
        self.facts.append(
            {
                "type": "fact",
                "name": name,
                "value": value,
                "calculation": calculation,
            }
        )
        return len(self.facts) - 1

    def record_conclusion(self, text, depends_on=None):
        self.facts.append(
            {"type": "conclusion", "text": text, "depends_on": depends_on or []}
        )
        return len(self.facts) - 1

    def get_summary(self):
        return "\n".join(
            [
                f"- {f['name']}: {f['value']}"
                if f["type"] == "fact"
                else f"- Conclusion: {f['text']}"
                for f in self.facts
            ]
        )

epist = SimpleFactRecorder()
```

## Reactive Calculations

```python {.marimo}
# Get values from sliders
revenue = revenue_slider.value
costs = cost_slider.value

# Calculate profit (reactive - updates when sliders change!)
profit = revenue - costs
profit_margin = (profit / revenue * 100) if revenue > 0 else 0

# Record facts in EPIST
fact_revenue = epist.record_fact("revenue", revenue, calculation="from user input")

fact_costs = epist.record_fact("costs", costs, calculation="from user input")

fact_profit = epist.record_fact("profit", profit, calculation="revenue - costs")

fact_margin = epist.record_fact(
    "profit_margin", f"{profit_margin:.1f}%", calculation="(profit / revenue) * 100"
)

# Store for use in other cells
_calculation_results = {
    "revenue": revenue,
    "costs": costs,
    "profit": profit,
    "profit_margin": profit_margin,
}

_calculation_results
```

## Conclusions (Reactive)

```python {.marimo}
# This cell updates automatically when profit_margin changes!

if profit_margin > 40:
    conclusion = "Excellent profitability - business is thriving!"
    status = "🟢"
elif profit_margin > 25:
    conclusion = "Good profitability - healthy margins"
    status = "🟡"
elif profit_margin > 10:
    conclusion = "Moderate profitability - room for improvement"
    status = "🟠"
else:
    conclusion = "Low profitability - needs attention"
    status = "🔴"

# Record conclusion in EPIST
conclusion_id = epist.record_conclusion(
    conclusion, depends_on=[fact_revenue, fact_profit, fact_margin]
)

f"{status} {conclusion}"
```

## Summary Report

```python {.marimo}
mo.md(
    f"""
    ### Financial Analysis

    **Metrics:**
    - Revenue: ${revenue:,}
    - Costs: ${costs:,}
    - Profit: ${profit:,}
    - Profit Margin: {profit_margin:.1f}%

    **Assessment:**
    {status} {conclusion}

    ---

    **Provenance:** All calculations tracked in EPIST with full dependency chains.
    """
)
```

## EPIST Provenance Summary

```python {.marimo}
mo.md(
    f"""
    **Recorded Facts & Conclusions:**

    {epist.get_summary()}

    *(In real usage, this would be saved to a structured provenance database)*
    """
)
```

## Export This Notebook

**To HTML:**
```bash
marimo export html simple_epist_demo.py -o demo.html
```

**To PDF (via Jupyter):**
```bash
marimo export ipynb simple_epist_demo.py -o demo.ipynb
uvx --with nbconvert --from jupyter-core jupyter nbconvert --to pdf demo.ipynb
```

**To Markdown:**
```bash
marimo export md simple_epist_demo.py -o demo.md
```

**Run as Python script:**
```bash
python simple_epist_demo.py
```

**Edit interactively:**
```bash
marimo edit simple_epist_demo.py
```