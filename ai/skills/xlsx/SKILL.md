---
name: xlsx
description: Use the xlsx CLI for local workbook inspection, row filtering, extraction, conversion, and targeted edits when a command-line workflow fits the task. For workbook authoring, charts, formatting, and recalculation, use the available spreadsheet authoring workflow.
---

# XLSX CLI

Use the `xlsx` CLI for local workbook inspection, filtering, extraction, conversion, and targeted edits when it fits the task. Preserve an explicitly requested tool or spreadsheet authoring workflow. Check the installed `xlsx --help` and selected command’s help before adapting examples.

Inspect the workbook’s sheets and headers before selecting ranges or columns. Prefer verified sheet names over ambiguous numeric indexes. Preserve the original workbook and default backup behavior unless the authorized task calls for a different write strategy. Read the relevant notes:

| Task | Read |
| --- | --- |
| Find an operation or inspect sheets, headers, counts, and formulas | [Command lookup](references/commands.md) |
| Filter rows, select columns, export complete data, or format dates | [Filtering and export](references/filtering-and-export.md) |
| Change cells, broadcast formulas, insert or delete rows/columns | [Editing](references/editing.md) |
| Diagnose empty/truncated views, indexing, filter parsing, or range behavior | [Gotchas](references/gotchas.md) |

A bounded view is not complete extraction. Use `to-csv` for full-file extraction, then verify the resulting rows and columns. Before reporting an edit complete, inspect the intended cells, formulas, and affected structure. CLI success alone does not establish recalculation or rendered workbook correctness; use the selected authoring workflow when those outcomes matter.
