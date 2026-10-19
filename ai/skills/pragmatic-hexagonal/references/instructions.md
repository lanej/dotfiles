# Default software architecture

Use Pragmatic Hexagonal Architecture for software design, implementation,
modification, debugging, and review. Before that work, read
`~/.local/share/software-standards/pragmatic-hexagonal/SKILL.md` and
`~/.local/share/software-standards/pragmatic-hexagonal/references/standard.md`.

Preserve explicit expectations, inspectable decisions, observable effects,
preserved evidence, and revisability. These are properties of the resulting
software. Instruction following, passing checks, or architectural appearance
cannot establish them.

Choose the minimum supporting architecture: functional core, imperative shell,
thin canonical model, and selective ports at real substitution or isolation
boundaries. Adopt incrementally within the changed capability.

Identify consequential claims, applicability conditions, observable
contradictions, evidence sources, and interpretation limits. Use existing
contracts, types, examples, tests, return values, errors, or runtime signals.
Evidence must be capable of disagreeing with the implementation. Distinguish
contract correctness, environmental assumptions, and intended outcomes.

During reviews, report specific requirement violations, affected behavior,
and supporting evidence. Distinguish established facts, unverified assumptions,
and verification gaps. Missing evidence does not confirm correctness.

Scale implementation and verification to consequence and complexity. Trivial
changes require no architecture report or prescribed ceremony. Written
explanations cannot substitute for software properties.

Follow the host's documented instruction precedence and applicable project
constraints. These defaults do not override higher-priority instructions.
Document material deviations with the requirement, concrete constraint,
retained protections, and conditions for reconsideration. Report unavailable
standard files as a limitation; do not claim they were loaded.
