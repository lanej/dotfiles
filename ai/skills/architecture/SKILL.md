---
name: architecture
description: Use when designing or reviewing software architecture, deciding where policy and effects belong, or evaluating a model or integration boundary. Apply Pragmatic Hexagonal Architecture to the changed capability.
---

# Pragmatic Hexagonal Architecture

Use a **functional core** for domain decisions and an **imperative shell** to gather facts and execute effects. Keep the **canonical model thin** and introduce **ports and adapters selectively**, where callers need substitution or isolation.

Read [the canonical PHA standard](../builder/references/standard.md) when designing or reviewing a capability. Its required properties (PHA-P01–PHA-P06) define what the software must preserve. Its architectural defaults (PHA-A01–PHA-A06) guide how to achieve those properties.

## Place decisions and effects

Trace one use of the changed capability. Which decisions does it own, what facts do they need, and what can the caller conclude after an effect is attempted?

- **Functional core and imperative shell (PHA-A01, PHA-A02).** Supply the facts a rule needs so it can be exercised on its own. For example, the shell fetches quotes and reads the clock. The core selects an eligible offer from those values. The shell submits the selection and preserves an unknown outcome if confirmation times out.
- **Thin canonical model (PHA-A03).** Give application-owned concepts a shared meaning. Preserve provider distinctions and provenance when they affect a decision or its explanation. Provider types can stay local where the application owns no shared concept.
- **Selective ports and adapters (PHA-A04).** When a caller needs an interchangeable operation or meaningful isolation, define the operation in the caller’s terms. Its adapter translates between that contract and the external system. Check how a failure travels back through it. A direct SDK call in the shell can be sufficient. The ability to insert a test double alone does not justify a port.
- **Capability locality (PHA-A05).** Place a rule where its owner can revise it without disturbing unrelated behavior. A small utility may need only a transformation and its caller. Share a rule when multiple callers depend on the same invariant.
- **Authoritative external clients (PHA-A06).** Prefer the official SDK, then a client generated from an authoritative specification. A handwritten client needs a concrete reason and explicit protocol and error semantics.

## Judge a boundary

Trace a plausible correction through the design. If one provider changes its expiry convention, which callers need to change? Can the caller still distinguish an expired quote from a provider it could never reach? Use the actual dependencies, outcomes, and evidence to explain which boundary earns its place.

Consider where the required property can hold. A function can check that stock is available, but concurrent reservations may both pass that check. When atomicity requires enforcement at storage, keep the invariant explicit and verify what happens to competing reservations.

For a review finding, identify the affected behavior, the PHA requirement, and the evidence or missing observation. Record a departure near the affected contract with its requirement ID, concrete constraint, retained protections, and revisit condition. A justified alternative can satisfy the properties while departing from a default. An unmet required property remains a gap.

## Related guidance

- Read [design lessons](references/design-lessons.md) when deciding whether to extend a local idiom, move a computation, or rely on a measured threshold.
- Read [Unix design principles](references/unix-philosophy.md) when weighing choices about composition, representation, or interface behavior within PHA.
- Read [tool choices](../source-code-lifecycle/SKILL.md) when selecting libraries, API protocols, or migration scope.
- Read [data and interface planning](../data-change-planning/SKILL.md) when preparing or reviewing a plan that changes data structures or interfaces. Carry the relevant expectations into delegated planning briefs.
- Use [Builder](../builder/SKILL.md) for the construction workflow when implementation is requested.
