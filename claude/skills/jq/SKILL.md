---
name: jq
description: JSON processing with jq - filtering, transforming, aggregating, and reshaping JSON from files, APIs, and command output on the command line.
---

# jq

Filter syntax works as documented. This file covers tool selection and the idioms that prevent the
common failure modes.

## When not to reach for jq

- CSV/TSV → `xsv`; YAML → `yq`; analytical SQL over JSON → `duckdb` (`read_json_auto`).
- No in-place editing. Write to a temp file and move it; `jq '...' f.json > f.json` truncates the
  input before jq reads it.

## Idioms that matter

```bash
jq -r '.name'                     # raw string output — no surrounding quotes
jq -c '.'                         # compact; required when piping NDJSON onward
jq '.field // "default"'          # alternative operator — survives null/missing
jq '.maybe?'                      # suppress "cannot index" instead of erroring out
jq --arg env prod '.[$env]'       # inject shell values; never interpolate into the filter string
jq -n --argjson d "$JSON" '$d.x'  # no input, build from arguments
jq -r '.[] | [.a, .b] | @csv'     # @csv / @tsv / @sh handle quoting correctly
jq 'to_entries | map(...) | from_entries'   # operate on keys
jq 'walk(if type == "object" then del(.secret) else . end)'   # recursive edit
```

## Slurp vs. stream

`-s` reads the whole input into one array — convenient, but loads everything into memory. For large
or NDJSON input, process record-by-record instead:

```bash
jq -c 'select(.important)' stream.ndjson    # one object per line, streaming
jq --stream 'select(length == 2)' huge.json # leaf-level streaming for a single huge document
```

Filter early, before any `group_by`/`sort_by`, which must materialize the whole set.

## Diagnosing errors

| Message | Cause |
|---|---|
| `parse error: Invalid numeric literal` | Malformed JSON — validate with `jq empty file.json` |
| `Cannot index string with string` | Field access on a non-object; check with `jq 'type'` |
| `Cannot iterate over null` | Missing field; use `.field // []` |

`jq empty file.json` is the fast validity check — silence means valid. `debug` prints intermediate
values to stderr without disturbing the output stream.
