---
name: quarto
description: Use when authoring or rendering Quarto documents, editing QMD equations and notation, troubleshooting figures or PDF output, or exporting computational reports to Markdown, HTML, PDF, Word, or presentations.
---

# Quarto

Follow the target project’s configuration, execution environment, templates, and requested output format. Prefer Markdown for composable output when no distribution format is specified. Keep organization-specific scaffolding, libraries, branding, and editorial rules in their owning projects.

Read the matching references before working on these parts of a document:

| Task | Read |
| --- | --- |
| Project inspection, environments, render commands, output selection | [Rendering](references/rendering.md) |
| Narrative, tables, computed text, provenance, and export handoff | [Authoring](references/authoring.md) |
| Inline/display math, aligned definitions, subscripts, and delimiters | [Math notation](references/math.md) |
| Figure chunks, reusable plotting code, dimensions, and inspection | [Figures](references/figures.md) |
| PDF engines, title blocks, floats, fonts, and sizing failures | [PDF output](references/pdf.md) |

Render the changed document in the requested format and inspect the affected output. A successful command does not establish correct equations, readable charts, complete citations, or sound page layout. Report unavailable runtimes, dependencies, data, or renderers explicitly. Rendering does not authorize publishing or opening a signed-in service.
