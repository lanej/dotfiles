# Command and operation lookup

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
