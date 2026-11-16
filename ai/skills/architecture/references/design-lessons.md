# Design lessons

## Extend an idiom or introduce a boundary

Compare the proposed change with the closest working capability. If a report already computes cohorts in SQL, another query step may express a new grouping rule beside the data it needs. A separate processing stage adds a data exchange and another place where partial failure can occur. It may still earn its place when the query engine hits a planner limit or the calculation needs a different freshness or consistency guarantee. Choose the location that can uphold the contract, accounting for the cost of moving data and the owner of the rule.

## Use a threshold as policy

Distinguish a cutoff set by contract from one inferred from measurements. For an empirical cutoff, inspect representative values, including cases near the boundary. Compare the metric with an independently understood example before applying it across a population. For instance, if a rule concerns the duration of one observed workday, a median across several days measures something else. A matching classification can conceal that error. Preserve the unit, observation window, and sampling limits when they affect the decision.
