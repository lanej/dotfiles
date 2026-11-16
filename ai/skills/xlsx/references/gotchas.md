# Limits, indexes, formulas, and extraction pitfalls

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
