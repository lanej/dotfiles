# LookML Measure Gotchas

## Named, filtered measures for key/value ("EAV") metric tables

A common warehouse pattern is a "long" metrics table with one row per named
metric — `metric STRING, value FLOAT` (or similar), one row per computed
figure rather than one wide row with a column per figure. It's a clean shape
for the pipeline that populates it, but it's awkward to dashboard directly:
a single generic `measure: value { type: sum; sql: ${TABLE}.value ;; }` can't
carry a correct `value_format_name` (some rows are percentages, some are day
counts, some are raw integers), and building one dashboard tile per metric
means either a per-tile dashboard-level filter (works, but the underlying
field is still generically typed) or hand-picking rows in the query.

**Better idiom: one named, filtered measure per metric actually surfaced on a
dashboard**, each with its own correct format:

```lookml
view: my_metrics_table {
  sql_table_name: `project.dataset.my_metrics_table` ;;

  dimension: metric {
    primary_key: yes
    type: string
    sql: ${TABLE}.metric ;;
  }

  measure: value {
    type: sum
    sql: ${TABLE}.value ;;
    value_format_name: decimal_2
  }

  # Named, pre-filtered, correctly-formatted -- built for one specific
  # dashboard scorecard tile.
  measure: bot_payout_resolved_pct {
    type: sum
    sql: ${TABLE}.value ;;
    filters: [metric: "bot_payout_resolved_pct"]
    value_format_name: percent_1
  }
}
```

A dashboard tile then just does `fields: [my_metrics_table.bot_payout_resolved_pct]`
with **no** per-tile `filters:` hash needed — the measure carries its own
filter and its own format everywhere it's used, not just on one dashboard.

## "Measures with Looker aggregations ... may not reference other measures"

The one way to get this wrong: writing the filtered measure's `sql:` against
the sibling **measure** instead of the raw column —

```lookml
# WRONG -- ${value} resolves to the sibling MEASURE named `value`, not a
# dimension or the raw column. LookML Validator error:
# "Measures with Looker aggregations (sum, average, min, max, list types)
# may not reference other measures."
measure: bot_payout_resolved_pct {
  type: sum
  sql: ${value} ;;
  filters: [metric: "bot_payout_resolved_pct"]
  value_format_name: percent_1
}
```

The fix is trivial once you know the rule — reference the raw column
directly (`${TABLE}.value`), same as the base `value` measure already does.
`type: sum`/`average`/`min`/`max`/`list` measures can aggregate a dimension
or a raw column, but never another measure — that restriction doesn't apply
to `type: number` measures (which compute a value from already-aggregated
measures at the SQL-generation stage, not row-by-row), which is the other
legitimate way to build a derived measure if you actually do need to
reference an existing aggregate.

**This is easy to introduce by analogy**: the `filters:` parameter's own
syntax (`filters: [metric: "..."]`) looks like it's filtering on a
*dimension* named in the filter key, which makes `sql: ${value} ;;` feel
consistent with "filter down to one metric, then reference that value" —
but `filters:` on a measure filters the rows contributing to the
aggregation, it doesn't change what `sql:` is allowed to reference. Always
verify a new filtered measure resolves against the real BigQuery/warehouse
column, not a same-view field name, when the view already has a
generically-named measure that's tempting to reuse.

## Verifying before pushing

LookML Validator does catch this — but only on a full CI round-trip (several
minutes). Before pushing, grep every new filtered measure's `sql:` line and
confirm it references `${TABLE}.<column>` (or a real `dimension:`), never a
bare `${<name>}` where `<name>` is itself a `measure:` in the same view:

```bash
grep -B3 'sql: \${[a-z_]*} ;;' path/to/view.lkml
```

Cross-check any hit's `${...}` name against that same file's `measure:`
block names — if it matches one, it's this bug.
