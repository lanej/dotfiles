# Default software guidance: Builder

Use the `builder` skill for software design, implementation, modification,
debugging, and review. Before that work, read
`~/.local/share/software-standards/builder/SKILL.md`,
`~/.local/share/software-standards/builder/references/standard.md`, and
`~/.local/share/software-standards/builder/references/construction.md`.

## Resulting software

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

## Software construction

First make the smallest meaningful behavior work, not the entire system.
Prefer an executable result that resolves consequential uncertainty over
broad scaffolding or speculative abstractions.

TDD is optional; verification is not. When expected behavior is clear,
tests may be the best starting point. When feasibility is uncertain,
use the smallest credible experiment against the relevant real boundary.

As soon as meaningful behavior is established and will be retained, capture
repeatable checks before expanding or materially restructuring it.
Do not defer testing merely because the implementation is still changing.
Protect intended behavior without cementing speculative internal structure.
Preserve discovered failures as regression cases where practical.

Plan in small working-and-verifying increments, not separate
"implement everything" and "add tests" phases. This does not waive the
project's delivery gates or explicit test-first requirements.

## Review and applicability

During reviews, report specific requirement violations, affected behavior,
and supporting evidence. Distinguish established facts, unverified assumptions,
and verification gaps. Missing evidence does not confirm correctness.
Assess protection of retained behavior, not test-writing order, except where
explicit project requirements govern that order.

Scale implementation and verification to consequence and complexity. Trivial
changes require no architecture report or prescribed ceremony. Written
explanations cannot substitute for software properties.

Follow the host's documented instruction precedence and applicable project
constraints. These defaults do not override higher-priority instructions.
Document material architecture deviations with the requirement, concrete
constraint, retained protections, and conditions for reconsideration. Report
unavailable guidance files as a limitation; do not claim they were loaded.
