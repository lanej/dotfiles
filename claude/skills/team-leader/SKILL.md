---
name: team-leader
description: Decomposes a complex problem or scenario into distinct sub-problems and spawns parallel sub-agents to tackle each, then synthesizes results into a unified output. Use when a problem has multiple independent angles — different domains, perspectives, or workstreams — that can be investigated or built in parallel. Trigger when user says "use the team leader", "break this down", "attack this in parallel", "@team-leader", or when a scenario clearly has 2+ independent sub-problems.
---

# Team Leader

Invokes the `team-leader` agent type to decompose a scenario into parallel sub-problems.

## Pattern

1. **Decompose** — identify 2–6 bounded sub-problems with no overlap
2. **Spawn in parallel** — one agent per sub-problem (`explore` or `general-purpose`)
3. **Synthesize** — integrate findings into a coherent unified output

## When to use

- Problem has multiple independent angles (e.g., security + performance + API design)
- Different parts of a problem require different agent types (exploration vs. coding)
- Parallel execution would meaningfully reduce total time
- You'd otherwise context-switch between unrelated concerns mid-task

## When NOT to use

- Sub-problems are sequential and each depends on the previous result
- The problem is simple enough for a single agent
- Discovery must precede decomposition (run `explore` first, then team-leader)

## Invocation

```
@team-leader <scenario description>
```

Or via Task tool with `subagent_type: "team-leader"` and the scenario as the prompt.

## Example decompositions

**"Review the checkout flow for problems"** →
- Sub-problem A: frontend UX and accessibility issues
- Sub-problem B: API contract and error handling
- Sub-problem C: payment integration edge cases

**"Design a rate limiting system"** →
- Sub-problem A: algorithm options and trade-offs
- Sub-problem B: data store and persistence requirements
- Sub-problem C: API surface and client impact
