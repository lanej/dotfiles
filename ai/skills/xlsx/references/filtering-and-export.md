# Filter, extract, and format workbook data

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

## Date Formatting

Presets for `--date-format`: `iso8601` (default), `mdy`, `us-padded`, `us-time`, `unix`, `excel-serial`, `excel`. Custom: `"%Y-%m-%d"`.

## jq Integration

```bash
# Process JSON output with jq
xlsx view data.xlsx --format json | jq '.[] | select(.age > 30)'
xlsx filter data.xlsx --where "Status = 'Active'" --format json | jq 'length'
```
