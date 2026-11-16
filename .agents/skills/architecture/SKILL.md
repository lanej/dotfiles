---
name: architecture
description: "Use when designing or reviewing software architecture, boundaries, or tradeoffs. Apply Pragmatic Hexagonal Architecture: functional core, imperative shell, a thin canonical model, and selective ports and adapters."
---

# Pragmatic Hexagonal Architecture

Use **a functional core, an imperative shell, a thin canonical model, and selective ports and adapters at genuine substitution or isolation boundaries**. Organize around capabilities and choose the minimum structure that preserves understandable decisions, observable effects, and localized policy changes.

Read [the canonical PHA standard](../builder/references/standard.md) before assessing a design or implementation. It defines required solution properties (`PHA-P01`–`PHA-P06`), default architectural constraints (`PHA-A01`–`PHA-A06`), applicability, and exceptions. The orientation below does not replace that standard.

## Apply the architecture

Trace the changed capability from its contract and external assumptions through decisions, effects, and observable outcomes. Use these architectural constraints to support explicit expectations, inspectable decisions, observable effects, preserved evidence, revisability, and falsifiable claims:

| Constraint | Apply to the changed capability |
| --- | --- |
| **PHA-A01 — Functional core** | Supply facts and relevant state explicitly; keep domain decisions exercisable without unnecessary infrastructure. |
| **PHA-A02 — Imperative shell** | Put input/output, orchestration, composition, and effect execution in the shell; keep meaningful policy identifiable outside transport and vendor glue. |
| **PHA-A03 — Thin canonical model** | Model application-owned concepts and preserve consequential provider distinctions; avoid forcing a universal model over different capabilities. |
| **PHA-A04 — Selective ports and adapters** | Introduce a boundary for real substitution or isolation needs. Direct calls are appropriate when an interface adds no useful boundary; test doubles alone do not justify one. |
| **PHA-A05 — Capability locality and minimum structure** | Keep related decisions and effects local. Avoid universal layers, mandatory directory trees, and premature shared machinery. |
| **PHA-A06 — External clients** | Prefer official SDKs; otherwise use authoritative generated clients; justify handwritten clients with a concrete constraint and preserve protocol/error distinctions. |

Apply the standard proportionally. Small utilities need no interface hierarchy; transactional rules can remain near authoritative state when isolation requires it. Existing systems need no unrelated rewrite. Evaluate the whole capability’s behavior and change locality, not whether files resemble a hexagonal diagram.

For findings, identify the affected behavior, relevant requirement ID, and evidence. Distinguish facts, assumptions, and verification gaps. Record material deviations as **requirement ID → concrete constraint → retained protections → revisit condition**. Layout, passing checks, and a written explanation cannot establish compliance in the face of contradictory behavior. Do not require a separate architecture report or begin implementation by default.

## Load supporting guidance when relevant

- Read [tool choices](../source-code-lifecycle/references/tool-choices.md) when selecting libraries, API protocols, or migration scope; preserve project authority and adoption.
- Read [data and interface planning](../data-change-planning/SKILL.md) for a software plan or substantial model/interface change; apply those expectations to delegated briefs.
- Read [Unix design principles](references/unix-philosophy.md) for applicable modularity, composition, clarity, and policy/mechanism tradeoffs alongside PHA.
- Read [design lessons](references/design-lessons.md) when considering a new layer or extending an existing idiom. They supplement the PHA standard.

Use [Builder](../builder/SKILL.md) for the construction workflow when implementation is also requested. This skill owns architectural judgment, not an additional development ceremony.
