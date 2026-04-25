---
name: gspace/sheets
description: "Use when reading or writing spreadsheet data, updating cell ranges, appending rows, creating new spreadsheets, managing tables, or working with Google Sheets URLs or IDs. Covers sheets_get, sheets_get_values, sheets_update, sheets_append, sheets_create, sheets_tables_* MCP tools and their CLI equivalents."
---

# Sheets

## CLI

`file-id` accepts raw spreadsheet ID or Google Sheets URL.

```
gspace sheets get <file-id> [ranges...]           # full spreadsheet metadata + values; ranges optional
gspace sheets get-values <file-id> <range>        # values from a single range only
gspace sheets update <file-id> <range> <values-json> [--input-option RAW|USER_ENTERED]
gspace sheets append <file-id> <values-json> [--range <range>] [--input-option RAW|USER_ENTERED]
gspace sheets create <title> [sheet-titles...]    # sheet-titles are tab names

# Tables (indices are 0-based)
gspace sheets tables list <file-id>
gspace sheets tables create <file-id> <name> --sheet-id <id> --start-row <n> --start-col <n> --end-row <n> --end-col <n>
gspace sheets tables update <file-id> <table-id> [--name <name>] [--fields <mask>]
gspace sheets tables delete <file-id> <table-id>
```

`values-json` is a JSON 2D array: `'[["a","b"],["c","d"]]'`

## MCP Tools

| Tool | Description |
|---|---|
| `sheets_get` | Get spreadsheet metadata and values; accepts optional `ranges` array |
| `sheets_get_values` | Get cell values from a single named range |
| `sheets_update` | Overwrite values in a range (full replacement of that range) |
| `sheets_append` | Append rows after the last row with data |
| `sheets_create` | Create a new spreadsheet with optional named tabs |
| `sheets_tables_list` | List all tables across all sheets in a spreadsheet |
| `sheets_tables_create` | Create a named table over a range (requires sheet_id, row/col bounds) |
| `sheets_tables_update` | Update table metadata (name, etc.) by table_id with a field mask |
| `sheets_tables_delete` | Delete a table by table_id |
| `sheets_check_auth` | Verify Sheets API auth (MCP-only) |

## Patterns and Gotchas

**`sheets_get` vs `sheets_get_values`**: `sheets_get` returns full spreadsheet structure (sheets, properties, all values). `sheets_get_values` returns just the cell values for one range — prefer it when you know the range and don't need metadata.

**Range notation**: use A1 notation with sheet name prefix when targeting a specific tab: `Sheet1!A1:D10`. Omitting the sheet name targets the first sheet.

**`sheets_get` with multiple ranges**: MCP `ranges` is an array; CLI takes variadic positional args. Returns a `valueRanges` array in the same order.

**`input_option`**:
- `USER_ENTERED` (default): values are parsed as if typed by a user — formulas evaluate, dates parse, numbers coerce.
- `RAW`: values stored as-is, no interpretation. Use when writing strings that look like formulas or dates you don't want parsed.

**`sheets_update` replaces, not merges**: it overwrites exactly the cells in the specified range. Cells outside the range are untouched. Cells inside the range but not covered by the values array are cleared.

**`sheets_append` range behavior**: the `range` parameter (default `A1`) is used to find the table to append to, not a literal write target. Google Sheets API finds the last row with data in that region and appends below it.

**Creating tabs on `sheets_create`**: pass tab names as `sheet_titles` (MCP) or positional args (CLI). Omitting them creates a spreadsheet with a single default sheet. Tab names can be changed later but IDs are immutable.

**Write gate**: `sheets_update`, `sheets_append`, `sheets_create`, `sheets_tables_create`, `sheets_tables_update`, `sheets_tables_delete` are gated when `GSPACE_NTFY_TOPIC` is set. `sheets_get`, `sheets_get_values`, `sheets_tables_list` are read-only (no gate).

**Tables**: Sheets tables (introduced May 2024 in UI, API support April 2025) are structured ranges with named columns, alternating row colors, and optional header/footer. They are returned under `sheets[].tables[]` in `sheets_get` responses. `sheets_tables_list` is a convenience wrapper that flattens tables from all sheets. Row/column indices in `create` are 0-based; `end_row_index` and `end_column_index` are exclusive. Table names must be unique within a spreadsheet. `update` uses a field mask — pass `"name"` to rename only, `"*"` to update all fields.

**File ID resolution**: both CLI and MCP use `resolveFileId()` — pass a full `https://docs.google.com/spreadsheets/d/<id>/edit` URL or just the bare spreadsheet ID. Both work.

**Multi-sheet exports**: when downloading a spreadsheet (via `drive_files_download`), use `xlsx` format — `csv` only exports the first sheet.
