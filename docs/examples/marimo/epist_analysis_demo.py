import marimo

__generated_with = "0.19.6"
app = marimo.App(width="medium")


@app.cell
def __():
    import marimo as mo

    return (mo,)


@app.cell
def __(mo):
    mo.md(
        """
        # EPIST Data Analysis Demo with Marimo

        This notebook demonstrates how marimo integrates perfectly with EPIST for 
        provenance tracking in data analysis.

        **Key features:**
        - Reactive execution (when data changes, everything updates)
        - Pure Python (direct EPIST integration)
        - Version control friendly (plain .py file)
        - Can run as script, app, or export to HTML/PDF
        """
    )
    return


@app.cell
def __():
    # Simulated EPIST module for demo
    # In real usage: from epist import FactRecorder, record_conclusion

    class FactRecorder:
        def __init__(self, analysis_name):
            self.analysis_name = analysis_name
            self.facts = {}

        def record_fact(
            self, key, value, source=None, calculation=None, description=None
        ):
            fact = {
                "value": value,
                "source": source,
                "calculation": calculation,
                "description": description,
            }
            self.facts[key] = fact
            print(f"✓ Recorded fact: {key} = {value}")
            return key

        def record_conclusion(self, key, text, depends_on=None):
            conclusion = {"text": text, "depends_on": depends_on or []}
            self.facts[key] = conclusion
            print(f"✓ Recorded conclusion: {key}")
            return key

        def save(self, filename):
            import json

            with open(filename, "w") as f:
                json.dump(
                    {"analysis": self.analysis_name, "facts": self.facts}, f, indent=2
                )
            print(f"✓ Saved provenance to {filename}")

    epist = FactRecorder("q4_sales_analysis")
    return FactRecorder, epist


@app.cell
def __(mo):
    mo.md("## 1. Data Loading with Provenance Tracking")
    return


@app.cell
def __(epist):
    import pandas as pd
    import numpy as np

    # Simulate loading data
    np.random.seed(42)
    data = {
        "date": pd.date_range("2024-10-01", periods=90, freq="D"),
        "sales": np.random.uniform(5000, 15000, 90),
        "costs": np.random.uniform(3000, 8000, 90),
        "customers": np.random.randint(50, 200, 90),
    }
    df = pd.DataFrame(data)

    # Record data source in EPIST
    source_id = epist.record_fact(
        "data_source",
        "sales_q4_2024.csv",
        source="simulated_data",
        description="Q4 2024 sales data",
    )

    df.head()
    return data, df, np, pd, source_id


@app.cell
def __(mo):
    mo.md("## 2. Key Metrics Calculation (Reactive)")
    return


@app.cell
def __(df, epist, source_id):
    # Calculate key metrics
    total_sales = df["sales"].sum()
    total_costs = df["costs"].sum()
    total_profit = total_sales - total_costs
    avg_daily_sales = df["sales"].mean()
    total_customers = df["customers"].sum()

    # Record facts in EPIST
    fact_total_sales = epist.record_fact(
        "total_sales_q4",
        float(total_sales),
        source=source_id,
        calculation="df['sales'].sum()",
        description="Total sales for Q4 2024",
    )

    fact_total_profit = epist.record_fact(
        "total_profit_q4",
        float(total_profit),
        source=source_id,
        calculation="total_sales - total_costs",
        description="Total profit for Q4 2024",
    )

    fact_avg_daily = epist.record_fact(
        "avg_daily_sales",
        float(avg_daily_sales),
        source=source_id,
        calculation="df['sales'].mean()",
        description="Average daily sales",
    )

    # Display metrics
    metrics = {
        "Total Sales": f"${total_sales:,.2f}",
        "Total Costs": f"${total_costs:,.2f}",
        "Total Profit": f"${total_profit:,.2f}",
        "Avg Daily Sales": f"${avg_daily_sales:,.2f}",
        "Total Customers": f"{total_customers:,}",
    }
    metrics
    return (
        avg_daily_sales,
        fact_avg_daily,
        fact_total_profit,
        fact_total_sales,
        metrics,
        total_costs,
        total_customers,
        total_profit,
        total_sales,
    )


@app.cell
def __(mo):
    mo.md("## 3. Visualizations")
    return


@app.cell
def __(df):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    # Sales over time
    axes[0, 0].plot(df["date"], df["sales"], label="Sales")
    axes[0, 0].set_title("Daily Sales Trend")
    axes[0, 0].set_xlabel("Date")
    axes[0, 0].set_ylabel("Sales ($)")
    axes[0, 0].tick_params(axis="x", rotation=45)

    # Profit over time
    profit_daily = df["sales"] - df["costs"]
    axes[0, 1].plot(df["date"], profit_daily, label="Profit", color="green")
    axes[0, 1].set_title("Daily Profit Trend")
    axes[0, 1].set_xlabel("Date")
    axes[0, 1].set_ylabel("Profit ($)")
    axes[0, 1].tick_params(axis="x", rotation=45)

    # Customers histogram
    axes[1, 0].hist(df["customers"], bins=20, edgecolor="black")
    axes[1, 0].set_title("Customer Distribution")
    axes[1, 0].set_xlabel("Daily Customers")
    axes[1, 0].set_ylabel("Frequency")

    # Sales vs Costs scatter
    axes[1, 1].scatter(df["costs"], df["sales"], alpha=0.6)
    axes[1, 1].set_title("Sales vs Costs")
    axes[1, 1].set_xlabel("Costs ($)")
    axes[1, 1].set_ylabel("Sales ($)")

    plt.tight_layout()
    fig
    return axes, fig, plt, profit_daily


@app.cell
def __(mo):
    mo.md("## 4. Analysis & Conclusions (Reactive)")
    return


@app.cell
def __(
    epist,
    fact_avg_daily,
    fact_total_profit,
    fact_total_sales,
    total_profit,
    total_sales,
):
    # Make conclusions based on data
    # These will update automatically if data changes!

    profit_margin = (total_profit / total_sales) * 100

    if profit_margin > 30:
        conclusion_text = f"Strong profitability: {profit_margin:.1f}% profit margin"
        conclusion_type = "positive"
    elif profit_margin > 20:
        conclusion_text = f"Healthy profitability: {profit_margin:.1f}% profit margin"
        conclusion_type = "neutral"
    else:
        conclusion_text = (
            f"Low profitability: {profit_margin:.1f}% profit margin - needs improvement"
        )
        conclusion_type = "negative"

    # Record conclusion in EPIST
    conclusion_id = epist.record_conclusion(
        "q4_profitability_assessment",
        conclusion_text,
        depends_on=[fact_total_sales, fact_total_profit, fact_avg_daily],
    )

    conclusion_text
    return conclusion_id, conclusion_text, conclusion_type, profit_margin


@app.cell
def __(mo):
    mo.md("## 5. Interactive Summary")
    return


@app.cell
def __(
    avg_daily_sales,
    conclusion_text,
    mo,
    profit_margin,
    total_customers,
    total_profit,
    total_sales,
):
    mo.md(
        f"""
        ### Q4 2024 Sales Analysis Summary

        **Financial Metrics:**
        - Total Sales: ${total_sales:,.2f}
        - Total Profit: ${total_profit:,.2f}
        - Profit Margin: {profit_margin:.1f}%
        - Average Daily Sales: ${avg_daily_sales:,.2f}

        **Customer Metrics:**
        - Total Customers: {total_customers:,}

        **Conclusion:**
        > {conclusion_text}

        ---

        **Provenance Tracking:**
        All metrics and conclusions have been recorded in EPIST with full 
        provenance chains linking back to source data.
        """
    )
    return


@app.cell
def __(mo):
    mo.md("## 6. Save EPIST Provenance Chain")
    return


@app.cell
def __(epist):
    # Save the complete provenance chain
    provenance_file = "q4_sales_provenance.json"
    epist.save(provenance_file)

    f"Provenance saved to: {provenance_file}"
    return (provenance_file,)


@app.cell
def __(mo):
    mo.md(
        """
        ## Export Options

        This marimo notebook can be exported to multiple formats:

        **Command line:**
        ```bash
        # Export to HTML
        marimo export html epist_analysis_demo.py -o report.html

        # Export to PDF (via Jupyter notebook)
        marimo export ipynb epist_analysis_demo.py -o report.ipynb
        uvx --with nbconvert --from jupyter-core jupyter nbconvert --to pdf report.ipynb

        # Export to Markdown
        marimo export md epist_analysis_demo.py -o report.md

        # Run as script
        python epist_analysis_demo.py
        ```

        **Or use the notebook menu:** File → Export
        """
    )
    return


if __name__ == "__main__":
    app.run()
