---
name: critique
description: Adversarially review a Socrates specification for ambiguity, missing authority, and weak acceptance evidence. Use when explicitly asked to critique a specification or during the shape workflow.
---

# Specification critique

Read [the shared evidence and session contract](../socrates/references/dialogue.txt). Resolve the supplied spec path/session directory, or use the contract's resolver without starting its interview or migrating the spec. Read the spec and existing critique/reconciliation records.

Run two independent fresh-context critics, with no inherited conversation history. Give each only the spec and the shared evidence/readiness contract. Ask for findings inline; the parent owns the saved report. Critics must not edit the spec or dispatch further agents.

- **Literal executor:** identify undefined terms, contradictory requirements, unclear ownership, missing interfaces, undelegated choices, and ambiguous execution boundaries.
- **Verification critic:** identify gameable or unobservable acceptance criteria, regression gaps, missing failure signals, false positives/negatives, and unsupported uncertainty acceptance. Check that any promised feedback signal is actually usable.

Use the host's available agent tools. If independent dispatch is unavailable, perform a clearly labeled inline review, state that independence is unverified, and do not report two independent passes. A required independent-review gate remains unmet until it can be completed.

Write findings beside the spec as `critique.md`, preserving a prior report under a unique timestamped `history/` path. Record the exact specification version and reviewed artifact. Organize critical/major/minor findings, false-positive/negative risks, validation weaknesses, and recommended revisions only where useful.

Give each finding a stable F1, F2, ... ID, affected requirement/decision, evidence, consequence, and concrete proposed correction. Retain an ID for an unchanged finding and never recycle it. Existing dispositions are not new blockers without a changed evidence/requirement trigger. For legacy unnumbered findings, use the shared contract's path/heading/excerpt identity.

Critique is advisory and read-only toward the specification. Do not rewrite intent, weaken requirements, approve a plan, or silently migrate legacy sessions. Reconciliation belongs to `specify`/`socrates`, which record pending, accepted, rejected, or deferred dispositions in the specification. Accepted means actually incorporated. If writes are restricted, return the report inline and state that persistence is pending.
