# Rendering Quarto documents

Inspect `_quarto.yml`, document frontmatter, profiles, existing build commands, and the project’s dependency files before choosing commands. Preserve its selected engine, environment, templates, and formats. Use the installed `quarto --help` and `quarto render --help` to confirm available options.

## Existing projects

Run from the intended project directory. Reuse its declared Python/Jupyter or R environment; do not borrow a different project’s environment or silently install a new toolchain. A missing runtime or dependency is a concrete setup requirement to resolve within the task’s authority.

```sh
quarto render report.qmd --to gfm
quarto render report.qmd --to html
quarto render report.qmd --to pdf
```

Choose the requested output rather than rendering every format. For a new Markdown-first document, a minimal frontmatter example is:

```yaml
---
format: gfm
wrap: none
---
```

Keep Markdown prose paragraphs on one source line. Inspect generated Markdown for unresolved source syntax, citations, math, and asset links. For HTML, inspect the page and its affected states; for PDF, inspect the rendered pages. Keep generated outputs separate from authored sources according to repository policy.

## New documents and portability

Use ordinary Quarto files and the target project’s supported setup. Keep required templates, filters, stylesheets, and data dependencies explicit. Reusable documents should not depend on another checkout’s absolute path. Choose Word or a presentation format when the recipient needs that artifact; follow the selected format’s documented options.

Use the [Quarto CLI reference](https://quarto.org/docs/reference/), [Markdown output guide](https://quarto.org/docs/output-formats/gfm.html), and [Python execution guide](https://quarto.org/docs/computations/python.html) for version-sensitive options. Check execution and caching settings before a render that could query an external service or recompute costly work. Do not publish or upload the output without authorization.
