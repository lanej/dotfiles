---
name: team-leader
description: Decomposes a complex problem or scenario into distinct sub-problems and spawns parallel sub-agents to tackle each, then synthesizes results into a unified output. Use when a problem has multiple independent angles — different domains, perspectives, or workstreams — that can be investigated or built in parallel. Trigger when user says "use the team leader", "break this down", "attack this in parallel", "@team-leader", or when a scenario clearly has 2+ independent sub-problems.
---

# Team Leader

Decomposes a scenario into parallel sub-problems and spawns one `general-purpose` (or `Explore`) agent per sub-problem directly via the Agent tool. **`team-leader` is not a valid `subagent_type`** — it is a decomposition pattern, not an agent type. Never pass `subagent_type: "team-leader"` to the Agent tool; it will fail with "Agent type 'team-leader' not found."

## Pattern

1. **Decompose** — identify 2–6 bounded sub-problems with no overlap
2. **Spawn in parallel** — call the Agent tool N times simultaneously, once per sub-problem, each with `subagent_type: "general-purpose"` (or `"Explore"` for pure research tasks)
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

## Same-File Edit Constraint

When all sub-problems require editing the **same file**, parallel agents will clobber each other — the second agent's `old_string` may no longer exist after the first agent modified it. Do NOT spawn parallel write agents in this case.

**Pattern to use instead:**

1. **Decompose into read-only research agents** (spawn in parallel using `subagent_type: "Explore"`) — each agent identifies the exact `old_string` → `new_string` patch for its sub-problem. Research agents read the file but make no edits.
2. **Collect all patches** from the agent results.
3. **Apply all patches sequentially in a single pass** — either directly with the Edit tool or via one agent briefed with all patches.

Example decomposition for "fix 6 prose issues in the same QMD":
- Agent A (Explore): find exact text for issues 1, 2, 3 — return verbatim old/new strings
- Agent B (Explore): find exact text for issues 4, 5, 6 — return verbatim old/new strings
- [collect results]
- Apply all 6 Edit calls sequentially

**How to detect this situation before spawning:** Before issuing the Agent tool calls, check: do any two sub-problems write to the same file? If yes, switch to the research-first pattern.

## Invocation

```
@team-leader <scenario description>
```

Claude (the primary agent) performs the decomposition itself, then spawns parallel agents via the Agent tool:

```
Agent tool call 1: subagent_type="general-purpose", prompt="<sub-problem A briefing>"
Agent tool call 2: subagent_type="general-purpose", prompt="<sub-problem B briefing>"
Agent tool call 3: subagent_type="Explore",         prompt="<sub-problem C briefing>"
```

All three calls are issued in the same turn so they execute in parallel. Collect results, then synthesize.

## Example decompositions

**"Review the checkout flow for problems"** →
- Sub-problem A: frontend UX and accessibility issues
- Sub-problem B: API contract and error handling
- Sub-problem C: payment integration edge cases

**"Design a rate limiting system"** →
- Sub-problem A: algorithm options and trade-offs
- Sub-problem B: data store and persistence requirements
- Sub-problem C: API surface and client impact
