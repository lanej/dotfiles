---
name: pragmatic-hexagonal
description: "Use when designing, implementing, modifying, debugging, or reviewing software; preserve inspectable behavior, challengeable claims, and revisable policies with the minimum supporting architecture."
---

# Pragmatic Hexagonal Architecture

Read [the standard](references/standard.md) before software work. It governs
properties of the software produced, by humans or agents. Test completion,
agent instruction following, and architectural appearance cannot substitute
for those properties.

## Apply the standard

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

For small changes, preserve the properties with ordinary code and proportionate
verification; no architecture report is required. Existing project instructions
control development procedure and test cadence. Apply documented instruction
precedence; record material deviations using the standard's exception format.

For concrete examples or to inspect their limitations, read the standard's
reference examples and run `python3 scripts/check_examples.py` from this skill
directory. That exercises software examples, not assistant adherence.
