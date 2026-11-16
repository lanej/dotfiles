---
name: verify
description: Evaluate execution evidence against a saved Socrates specification and its validation contract. Use when asked to verify a Socrates result or during shape's final verification, not for unrelated routine checks.
---

# Specification verification

Read [the shared evidence and session contract](../socrates/references/dialogue.txt). Resolve the explicitly supplied spec/session or the bound session without starting its interview. For an execution artifact, require its explicit session/version reference; ask when that association is ambiguous rather than choosing the newest nearby spec.

Read the specification, decision record, relevant critique dispositions, approved plan, and execution evidence. Record the specification version and exact artifact or commit being verified. Old plans, reviews, or results establish only the version/content they actually covered; inspect relevance after reopening. Do not migrate or rewrite the spec during verification.

Evaluate:

- Every requirement's observable acceptance criterion: passed, failed, or unverifiable, with evidence and its limits.
- Regression boundaries and defined failure signals, distinguishing checks actually run from checks merely proposed.
- Promised in-progress feedback and task-level checks: distinguish a missing design, a skipped check, and a failed check. Apply the equivalent recorded contract for writing/analysis rather than inventing software tests.
- Preserved decisions, authority boundaries, review requirements, critique dispositions, and any consequential drift. Accepted uncertainty requires recorded user acceptance, its implications, and the promised check. A future check cannot prove a present outcome.
- False-positive risks: apparent success that violates intent, weak metrics, missing evidence, and unaddressed contradictions.

Classify the overall result:

| Result | Meaning |
|---|---|
| `VERIFIED` | All applicable required criteria have confirming evidence and no unresolved blocking contradiction or defined failure remains. |
| `PARTIALLY VERIFIED` | Some criteria have confirming evidence, others remain unverifiable, and no defined failure is established. |
| `UNVERIFIABLE` | Available evidence cannot establish the required acceptance outcomes. |
| `FAILED` | Evidence establishes a violated acceptance criterion, authority boundary, blocking decision, or defined failure signal. |

Write `verification.md` beside the spec, preserving an existing report in a unique timestamped `history/` file. Include specification version, verified target, classification, per-criterion evidence, regression results, feedback usage, decisions/readiness, failure signals, false-positive risks, and residual uncertainty as applicable. Distinguish local checks, hosted CI, delivery, and live acceptance when relevant. Set the spec to `Verified` only when the matching current version earns `VERIFIED` and writes are permitted; preserve its frozen decisions. Other results do not advance lifecycle state.

Missing evidence is unknown, not success. Do not redefine success, weaken requirements, manufacture acceptance, or reopen settled questions just to fill the report. State unavailable review or execution capabilities. When writes are restricted, return findings inline and identify unsaved artifacts.
