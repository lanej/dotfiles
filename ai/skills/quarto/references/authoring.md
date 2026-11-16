# Authoring computational documents

Start with the reader’s question and the decision or understanding the document supports. State the finding, show the evidence, and explain material uncertainty. Choose headings, prose, charts, and tables for their communicative purpose; inherit project editorial rules rather than imposing a report template or word quota.

## Computed text and tables

Show formatted results appropriate to the output format. Diagnostic prints and raw data frames can help development, but review whether they belong in the delivered document. In Python/Jupyter, formatted narrative can use the display API:

```python
from IPython.display import Markdown, display

sample_count = len(observations)
display(Markdown(f"The sample contains **{sample_count:,} observations**."))
```

Compute values before formatting them. Keep labels, units, denominators, dates, and rounding consistent across prose, tables, and figures. Use the project’s table library or Quarto’s supported table features; check long tables, captions, and cross-references in each required output format.

## Provenance and reproducibility

Explain sources and methods where readers need them. Keep extraction logic, query parameters, date ranges, and transformations inspectable in code or supporting material. Cite external claims with usable source links. Do not hide provenance in an unavailable local path or forbid useful source names in prose.

When using cached results, record enough context to identify their inputs and freshness. A cache hit does not establish that the result is current. Report unavailable data and failed queries; do not substitute synthetic results or constants while presenting them as observations. Label examples and synthetic data clearly.

## Export and review

Preserve essential qualifications beside the result they qualify. Inspect the actual exported file for missing assets, broken references, clipping, and changed table or equation layout. For editable handoff, use the recipient’s requested format and the authorized document workflow. Exporting a file does not prove that another editor imported it faithfully.

Read Quarto’s [tables](https://quarto.org/docs/authoring/tables.html), [citations](https://quarto.org/docs/authoring/citations.html), and [cross-reference](https://quarto.org/docs/authoring/cross-references.html) guides for supported syntax.
