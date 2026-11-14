---
name: typescript
description: Use when writing or reviewing TypeScript, enforcing exhaustive state handling, or adopting strict compiler and typed lint checks in new or existing repositories.
---

# TypeScript correctness

Read the project’s stage through [source-code lifecycle](../source-code-lifecycle/SKILL.md), then run `python3 scripts/check-source-code.py typescript` for its generated gate. Full profile commands below remain available for extra evidence; they are required at beta and production. Research and alpha use the selected stage’s checks while preserving existing repository gates.

For comment decisions, read the [shared comment guidance](../code-comments/SKILL.md). For public library APIs, also read the [library comment guidance](../library-code-comments/SKILL.md). Bootstrap bundles both with this skill in tracked or local mode; apply the library perspective only to library work and preserve project requirements.

Make decisions explicit, preserve failures, and validate untrusted data at boundaries. Follow the repository's existing architecture and stronger checks; do not replace them with a generic framework.

Read [the correctness guide](references/correctness.md) before adopting or changing the profile. Use the shipped assets through `source-code setup --typescript`, or `--typescript-retrofit` for existing code. Installation changes tooling only; it does not install dependencies or rewrite source.

## Implementation

- Use discriminated unions for variants, exhaustive switches, and `satisfies Record<Key, Value>` for total tables. A default branch is a runtime guard, not coverage for an omitted declared variant.
- Accept external data as `unknown` and validate it before treating it as domain data. Do not replace validation with assertions, `any`, or non-null assertions.
- Await promises or attach a meaningful rejection handler. `void promise` does not handle rejection. Preserve cancellation and cleanup with `finally` or supported disposable resources.
- Isolate domain decisions from I/O where useful. Introduce ports or interfaces for demonstrated boundaries, not for every function. Retain existing import and architecture checks.

## Verification

When the stage requires lint, use Biome alongside typed ESLint and the existing formatter. Run the selected lifecycle gate before handoff. `lint`, `typecheck`, `test`, and `audit` isolate checks; the full command remains available explicitly. `fmt` requires explicit TypeScript file paths and is the only source-writing mode.

Treat missing tools, parser errors, uncovered source, failing project checks, and suppression-policy violations as failures. Never add a baseline allowance to unblock a feature. After repairing old findings, run `ratchet` and commit the reduced baseline with the fix. Review suppression explanations, exclusions, baseline changes, and tool upgrades as policy changes.

Types are erased at runtime. Lint and tests do not establish business correctness; use independently derived expected behavior and actual boundary validation. Do not claim that a ratcheted repository is fully compliant.
