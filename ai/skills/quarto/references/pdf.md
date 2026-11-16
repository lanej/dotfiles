# PDF output

Inspect the project’s PDF engine, document class, fonts, templates, and header includes before changing layout. Preserve its choices unless the task requires changing them. A missing TeX installation is a setup requirement; do not assume a company scaffold or an external checkout will supply it.

## Titles and page structure

Quarto can generate a title block from document metadata. If the project also draws a custom title, inspect whether both are appearing and resolve the duplication in that project’s configuration. Do not universally suppress title, author, or date metadata. Use the document’s supported heading and cross-reference syntax.

Review page breaks, detached headings, large blank areas, oversized tables, and figure/caption grouping. Avoid forcing every figure to one placement rule: floats and fixed placement have different tradeoffs. Keep the finding and its essential qualifications readable together.

## Diagnose figure sizing

When a figure appears too small or unexpectedly stretched:

1. Inspect the saved figure’s actual dimensions and content bounds.
2. Check chunk dimensions and document placement options against the intended page width.
3. Look for out-of-bounds labels or mixed coordinate transforms that expand the canvas.
4. Check whether tight bounding-box settings changed the saved dimensions.
5. Re-render the affected page after correcting the specific cause.

Avoid universal canvas sizes, forced DPI values, or global clipping as a workaround. A single figure with malformed bounds should not drive unrelated document-wide layout changes.

## LaTeX troubleshooting

Read the first relevant error and inspect the generated TeX when needed. Temporarily enabling `keep-tex` in the PDF format configuration can help locate the corresponding source. Distinguish a missing font/package, unresolved reference, malformed equation, and repeated convergence warning before changing settings or raising iteration limits.

Inspect the final PDF pages for missing glyphs, math overflow, captions, table breaks, and artifact legibility. Report a missing renderer or unavailable visual inspection instead of claiming that a configuration check established the final appearance.

See Quarto’s [PDF basics](https://quarto.org/docs/output-formats/pdf-basics.html) and [PDF engines](https://quarto.org/docs/output-formats/pdf-engine.html) for current options and dependencies.
