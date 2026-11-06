---
name: architecture
description: "Use when designing or reviewing software architecture, evaluating boundaries, or assessing architectural tradeoffs. Apply Pragmatic Hexagonal Architecture without prescribing an implementation workflow."
---

# Architecture

Read [the architecture standard](../builder/references/standard.md) before
assessing a design or implementation. The companion `builder` skill supplies
this shared standard; use its construction workflow only when implementation
work is also requested.

Trace the changed capability from its contract and external assumptions through
decisions, effects, and observable outcomes. Apply the standard proportionally:
small utilities need no interface hierarchy, and existing systems need no
unrelated rewrite.

Recommend the minimum boundaries that preserve inspectable decisions,
consequential evidence, and localized policy changes. Distinguish established
facts, assumptions, and verification gaps. A tidy layout or green checks do not
establish architectural compliance.

For findings, identify the affected behavior, requirement ID, and supporting
evidence. Record material deviations using the standard's exception format.
Keep the response focused on the requested design decision or review; do not
begin implementation or require a separate architecture report by default.
