---
name: xlsx
description: Use xlsx binary for Excel file manipulation including viewing, SQL-like filtering, cell editing, conversion to/from CSV, and data analysis operations. Use this instead of Python (openpyxl, pandas, xlrd) or Node.js libraries for ALL .xlsx file operations — reading, writing, filtering, conversion, and analysis. Trigger on any request involving .xlsx or Excel files.
---
# XLSX Skill

The `xlsx` binary covers the full Excel manipulation surface without Python or Node.js.

## Commands

```
xlsx sheets <file>                         list sheets in workbook
xlsx view <file> [--sheet S] [--limit N] [--format table|json|csv|tsv]
xlsx headers <file> [--sheet S]            show column headers
xlsx select <file> "A,C,E" [--sheet S]    extract columns by letter or range A-E
xlsx slice <file> [--start N] [--end N] [--sheet S]   row range (1-indexed, inclusive)
xlsx search <file> <pattern> [--ignore-case] [--regex] [--sheet S]
xlsx filter <file> --where <expr> [--columns "Name,Email"] [--format json] [--limit N] [--offset N] [--sheet S] [--output file]
xlsx count <file> [--sheet S]             row and column count
xlsx stats <file> <COLUMN> [--sheet S]    statistics for one column (letter or name)
xlsx get-formula <file> <cell> [--sheet S]
xlsx eval "<formula>"                      evaluate formula expression
xlsx set <file> <cell|range> <value> [--value-type auto|string|number|bool|date|formula] [--sheet S] [--no-backup]
xlsx insert <file> row|column <ref> [--sheet S]
xlsx delete <file> row|column <ref|range> [--sheet S]
xlsx copy <file> <src-range> <dest-cell> [--sheet S]
xlsx to-csv <file> <out.csv> [--sheet S] [--date-format iso8601]
xlsx from-csv <in.csv> <out.xlsx> [--sheet S]
xlsx format <file> <range> ...            apply cell formatting
xlsx validate ...                          data validation rules
xlsx names ...                             named range management
xlsx pivot ...                             pivot table operations
xlsx chart ...                             chart operations
```

## Filter WHERE Clause

SQL-like syntax, case-insensitive by default.

```bash
# Column names with spaces use brackets
xlsx filter data.xlsx --where "[First Name] = 'John'"
xlsx filter data.xlsx --where "[Job Title] LIKE '%Engineer%'"

# Operators: =, !=, <>, >, <, >=, <=, LIKE, IN, BETWEEN, IS NULL, IS NOT NULL
xlsx filter data.xlsx --where "Status IN ('Active', 'Pending')"
xlsx filter data.xlsx --where "Age BETWEEN 25 AND 35"
xlsx filter data.xlsx --where "Manager IS NULL"
xlsx filter data.xlsx --where "(Status = 'Active' OR Status = 'Pending') AND Age > 25"

# Column selection, format, pagination, output file
xlsx filter data.xlsx --where "Dept = 'Sales'" --columns "Name,Email" --format csv --output out.csv
xlsx filter data.xlsx --where "Status = 'Active'" --limit 10 --offset 20

# Sheet by name or 0-based index
xlsx filter data.xlsx --where "Total > 1000" --sheet "Q4 Sales"
xlsx filter data.xlsx --where "Total > 1000" --sheet 2

# Case-sensitive matching
xlsx filter data.xlsx --where "Name = 'Bob'" --case-sensitive
```

## Editing

```bash
# Set single cell
xlsx set file.xlsx B5 42
xlsx set file.xlsx C1 "2025-01-15" --value-type date
xlsx set file.xlsx D1 "=SUM(A1:A10)" --value-type formula

# Set range — broadcasts same value to all cells; formulas adjust relative references
xlsx set file.xlsx B5:B10 "Pending"
xlsx set file.xlsx F2:F100 "=D2+E2" --value-type formula

# Insert / delete
xlsx insert file.xlsx row 5
xlsx insert file.xlsx column C
xlsx delete file.xlsx row 5:10
xlsx delete file.xlsx column C:E
```

## Date Formatting

Presets for `--date-format`: `iso8601` (default), `mdy`, `us-padded`, `us-time`, `unix`, `excel-serial`, `excel`. Custom: `"%Y-%m-%d"`.

## jq Integration

```bash
# Process JSON output with jq
xlsx view data.xlsx --format json | jq '.[] | select(.age > 30)'
xlsx filter data.xlsx --where "Status = 'Active'" --format json | jq 'length'
```

## Gotchas

- **`--limit 0` means zero rows, not unlimited** — `xlsx view --format json --limit 0` returns an empty array; `--format tsv` similarly returns nothing. Use `--limit N` with a large N (e.g. `--limit 9999`) for in-process viewing, or `xlsx to-csv` for full extraction. The default cap is 100 rows.
- **`stats` requires a column argument** — `xlsx stats file.xlsx Amount` not `xlsx stats file.xlsx`. Works on one column at a time.
- **`slice` uses flags, not positional args** — `xlsx slice file.xlsx --start 10 --end 20`, not `xlsx slice file.xlsx 10 20`.
- **`filter --sheet` is 0-based for integer index** — `--sheet 2` is the third sheet. Use the sheet name to avoid off-by-one.
- **Editing creates a backup by default** — use `--no-backup` to skip when running in a loop or script.
- **Filter string comparisons are case-insensitive by default** — use `--case-sensitive` to change.
- **`set` on a range with a formula adjusts references** — `=D2+E2` set over `F2:F100` produces `=D3+E3` in F3, etc.
- **`filter --where "1=1"` throws a parse error** — tautology clauses are not supported (`Parsing Error: Error { input: "1=1", code: Tag }`). To select all rows, omit `--where` entirely, or use `xlsx to-csv`.
- **Full-file extraction: use `xlsx to-csv`, not `view`** — for all rows and all columns, `xlsx to-csv file.xlsx out.csv --date-format iso8601` is reliable; downstream tooling is `duckdb` (`read_csv_auto()`) or Python `csv.DictReader`. `xlsx view --format json` with large limits is unreliable on big sheets.

## Quick Reference

```bash
xlsx sheets file.xlsx                         # list sheets
xlsx view file.xlsx --limit 9999              # view all rows (--limit 0 = zero rows)
xlsx headers file.xlsx                        # show headers
xlsx filter file.xlsx --where "A = 'x'"      # SQL filter
xlsx filter file.xlsx --where "A = 'x'" --format json | jq ...
xlsx stats file.xlsx Amount                   # stats for column
xlsx count file.xlsx                          # row/col count
xlsx set file.xlsx A1 "value"                # set cell
xlsx to-csv file.xlsx out.csv                 # export to CSV
xlsx from-csv in.csv file.xlsx                # import from CSV
```
