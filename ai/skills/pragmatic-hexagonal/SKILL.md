---
name: pragmatic-hexagonal
description: "Use when designing, implementing, refactoring, or reviewing software behavior or architecture; apply pragmatic functional-core/imperative-shell boundaries and falsifiable verification proportional to the change."
---

# Pragmatic Hexagonal Architecture

Read `~/.files/docs/pragmatic-hexagonal-architecture.md` (or the repository copy) when changing architectural boundaries, introducing integrations, designing a nontrivial feature, or reviewing such a change.

## Procedure

1. Identify the real workflow, caller-facing entrypoint, observable success, and likely failure.
2. Separate **facts and decisions** (functional core) from **orchestration and effects** (imperative shell).
3. Normalize only owned domain concepts; keep vendor-specific features explicit in integrations.
4. Introduce ports only for real substitution, isolation, independent ownership or lifecycle; never create generic interfaces reflexively.
5. Identify the simplest counterexample to each important design or behavioral claim and the detector that would expose it.
6. Build a thin end-to-end slice; verify through the real entrypoint and observable outcome.
7. Enforce objectively testable import boundaries with project-appropriate tooling where justified. Review semantic boundaries manually.
8. Report observed verification and gaps; do not claim static lint proves good architecture.

For a trivial edit, preserve existing boundaries and use the repository's normal lightweight checks. Do not introduce architecture diagrams, interfaces, or new tests solely to satisfy this skill.

The repository `methodology` skill controls test cadence and rigor; do not duplicate it here.
