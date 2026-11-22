# TypeScript correctness

Before selecting application tools or an API protocol, read [the installed project policy](../../source-code-lifecycle/SKILL.md). Apply the declared authority and adoption at the configured maturity; preserve external providers’ protocols and established stacks according to that policy.

Follow the verification commands and enforcement in this skill’s installed entrypoint. Preserve existing repository checks.

For comment decisions, read the [shared comment guidance](../../code-comments/SKILL.md). For public library APIs, also read the [library comment guidance](../../library-code-comments/SKILL.md). Bootstrap bundles both with this skill in tracked or local mode; apply the library perspective only to library work and preserve project requirements.

Make decisions explicit, preserve failures, and validate untrusted data at boundaries. Follow the repository's existing architecture and stronger checks; do not replace them with a generic framework.

## Implementation

- Use discriminated unions for variants, exhaustive switches, and `satisfies Record<Key, Value>` for total tables. A default branch is a runtime guard, not coverage for an omitted declared variant.
- Accept external data as `unknown` and validate it before treating it as domain data. Do not replace validation with assertions, `any`, or non-null assertions.
- Await promises or attach a meaningful rejection handler. `void promise` does not handle rejection. Preserve cancellation and cleanup with `finally` or supported disposable resources.
- Isolate domain decisions from I/O where useful. Introduce ports or interfaces for demonstrated boundaries, not for every function. Retain existing import and architecture checks.

## Verification boundaries

Types are erased at runtime. Lint and tests do not establish business correctness; use independently derived expected behavior and actual boundary validation. Fix findings at their cause and review suppressions, exclusions, and tool upgrades as policy changes.
