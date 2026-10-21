---
name: builder
description: "Use when designing, implementing, modifying, debugging, or reviewing software. Establish small working paths, protect retained behavior early without mandating TDD, and apply Pragmatic Hexagonal Architecture to the resulting software."
---

# Builder

Before software work, read [the architecture standard](references/standard.md)
and [the construction policy](references/construction.md).
The standard governs properties of the software produced, by humans or agents.
The construction policy governs how to develop it. Test completion, instruction
following, and architectural appearance cannot substitute for those properties.

## Construct in working increments

First make the smallest meaningful behavior work, not the entire system.
Resolve consequential uncertainty with an executable result rather than broad
scaffolding. TDD is optional; verification is not. Choose an early test when the
required behavior is clear, or a credible experiment when feasibility is unknown.

Once meaningful behavior is established and will be retained, capture repeatable
checks before expanding or materially restructuring it. Protect intended behavior
without cementing speculative internals. Preserve discovered failures as regression
cases where practical. Do not plan implementation and testing as separate phases.
Keep construction feedback distinct from the project's delivery gates.

## Apply the architecture standard

Identify the consequential behavior in the changed capability: its contract,
external assumptions, intended outcome, and evidence capable of contradicting
each. Use existing types, acceptance examples, tests, errors, return values,
or runtime signals; do not create a separate claim registry or report.

Keep relevant facts explicit at decision boundaries. Preserve consequential
provenance and uncertainty through translation and effects. Distinguish intended
actions, attempts, confirmations, failures, and unknown outcomes where material.
Locate the policy owner so disproven assumptions can be corrected locally.

Choose the minimum architecture supporting these properties: functional core,
imperative shell, a thin model of owned concepts, and ports only for concrete
substitution or isolation. Follow a complete capability rather than imposing
horizontal layers. Do not invent interfaces to make the diagram look right.

For debugging, distinguish a violated contract from a failed environmental
assumption or an outcome the contract never guaranteed. Preserve relevant
contradictory evidence before proposing a correction. Missing evidence stays
an explicit gap; it is not proof of correctness.

## Review

Report specific violated requirement IDs, affected behavior, and supporting
evidence. Separate established facts, unverified assumptions, and verification
gaps. Examine whether evidence can disagree with the implementation, including
where independent acceptance expectations or external observations are needed.
Do not infer compliance from source layout, green checks, or a polished rationale.

Assess protection of retained behavior, not whether tests preceded implementation,
unless the project explicitly requires test-first development.
For small changes, use ordinary code and proportionate verification; no architecture
report is required. Follow explicit project procedures and documented instruction
precedence. Record material architecture deviations using the standard's exception
format; development sequence is not an architecture-compliance requirement.

For concrete examples or to inspect their limitations, read the standard's
reference examples and run `python3 scripts/check_examples.py` from this skill
directory. That exercises software examples, not assistant adherence.
