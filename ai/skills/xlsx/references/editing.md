# Edit workbook cells, formulas, and structure

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
