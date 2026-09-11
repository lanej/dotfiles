---
name: xsv
description: Fast CSV processing with xsv - select, search, slice, sort, join, stats, frequency, and indexing for large delimited files. Prefer over pandas or awk for CSV-shaped work on the command line.
---

# xsv

Per-command flags work as documented (`xsv <cmd> --help`). This file covers tool selection and the
streaming-vs-in-memory distinction, which is what actually determines whether a pipeline finishes.

## Reach for xsv when

The data is CSV/TSV-shaped and the job is selection, filtering, joining, or summary statistics.
Faster and less ceremony than loading pandas. For anything needing SQL (GROUP BY, windows,
multi-way joins), switch to `duckdb`. For Excel formats, formulas, formatting, or multiple sheets,
use `xlsx` — xsv has none of those.

## Always start with headers

```bash
xsv headers data.csv
```

Column-name errors are the most common failure; check the structure before writing a pipeline.

## Streaming vs. in-memory — the thing that matters

**Streaming** (safe on files of any size): `select`, `search`, `slice`, `headers`, `cat`, `fmt`,
`count` (with an index).

**Loads the whole file**: `sort`, `table`, `frequency`, `stats --median`, `stats --mode`.

On a large file, sample or slice before an in-memory command:

```bash
xsv sample 100000 huge.csv | xsv stats --everything
```

## Index large files once

```bash
xsv index large.csv
```

Makes `count` O(1), gives `slice` and `sample` direct access, and enables parallel `stats -j 0`.

## Pipelines, not temp files

```bash
xsv select Name,Age data.csv | xsv search -s Age "^[3-9]" | xsv table
xsv sort -s Revenue -N -R customers.csv | xsv slice -l 10 | xsv table   # top 10
```

Each `-o temp.csv` hop re-reads and re-parses; chaining keeps it streaming.

## Delimiters

`-d` reads, `-t` writes — so `fmt` is the format converter:

```bash
xsv select 1,3 -d '\t' data.tsv       # read TSV
xsv fmt -t '\t' data.csv -o data.tsv  # write TSV
```

## `record has different length`

Ragged rows. Normalize first: `xsv fixlengths data.csv -o fixed.csv`.
