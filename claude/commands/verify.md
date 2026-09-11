---
description: "Verify execution results against a Socrates validation contract"
argument-hint: "artifact path, task output, or empty"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(cat:*)
  - Agent
  - Bash(find:*)
  - Bash(printenv:*)
  - Bash(sort:*)
tags:
  - verification
  - validation
  - regression
---

# /verify — Validation Contract Verification

Purpose: determine whether task execution produced a true positive outcome according to the specification's validation contract.

This command verifies:
- acceptance tests
- regression checks
- failure signals
- verification methods

from a Socrates-generated specification.

## Verification Philosophy

Execution completion is not sufficient.

A task is only a true positive if:
- the success criteria are met
- validation passes
- regression boundaries hold
- no defined failure signals are triggered

## Inputs

Read `$HOME/.claude/commands/socrates/dialogue.txt` for the canonical session,
evidence, and readiness contract. With no arguments use its resolver, without
running its interview. For an explicit execution artifact, resolve its associated
spec using an explicit session/version reference; if the match is ambiguous, ask
which spec rather than guessing from proximity or recency. Do not reconstruct a
missing companion; name the file and the `make claude` link remedy.

Read the spec, decision and reconciliation records, the approved plan, and execution
evidence. Record the specification version and artifact/commit being verified. An
old plan or result is evidence only for the version/content it actually covers;
inspect relevance after reopening instead of inheriting its approval or success.

Write `verification.md` beside the resolved spec. Preserve a previous report in a
new non-overwriting timestamped `history/` file before replacing it. Verification
must not silently migrate a legacy spec or rewrite its decisions: evaluate the
actual recorded evidence, flag unresolved gaps, and leave adaptation to the shared
Socrates procedure.

## Verification Procedure

### Step 1 — Load Validation Contract

Extract:
- success criteria
- acceptance tests
- regression checks
- failure signals
- verification methods
- Feedback Loop Design (from spec.md), cross-referenced against per-task `Feedback signal:` lines in the session's plan.md if present

### Step 2 — Evaluate Acceptance Criteria

Determine:
- which success criteria passed
- which failed
- which remain unverifiable

Do not infer success without evidence.

### Step 3 — Evaluate Regression Boundaries

Determine:
- what existing behavior may have degraded
- whether regression checks actually ran
- whether any silent failure paths remain

### Step 4 — Evaluate Feedback Loop Design Usage

Determine:
- whether the spec's Feedback Loop Design (signal, cost/cadence, fallback) was actually invoked during execution
- whether plan.md's per-task `Feedback signal:` entries (if present) were actually run, not just written
- if not invoked, whether that's a spec gap (no Feedback Loop Design was ever specified) or an execution gap (designed but skipped)
- for engineering execution, whether the **branch-level gate** ran on the final code after the last task and any review fixes (full suite + full lint/type-check) — per-task signals are deliberately scoped (tier V1) and do not substitute for it. A run of per-task signals with no branch gate is an execution gap, not a pass
- whether any escalation trip-wire fired during execution (see `CLAUDE.md`, Proportional Verification) and, if so, whether remaining tasks were actually promoted to full-suite checks
- whether a **wave review (V3a)** ran at each dependency-graph wave boundary, and whether its findings were fixed before the next wave started rather than carried forward — a carried-forward finding is the compounding case the checkpoint exists to prevent
- whether each review dispatch was briefed with the `methodology` skill's Review Fault Classes, or was an unguided "review this diff"

For writing, analysis, or other non-code work, apply the equivalent checks actually specified in the validation contract; do not invent a software suite or dependency graph. Surface "loop skipped" separately from "acceptance test failed."

### Step 5 — Evaluate Decisions and Readiness

Apply `dialogue.txt`'s readiness gate to the current specification and decision
record. Check that accepted decisions survive in the delivered result, each
requirement has observable acceptance evidence, and no blocking contradiction or
undelegated consequential choice was silently made during execution.

For accepted uncertainty, locate the actual user acceptance, its implications, and
the promised check. Determine whether that check ran when due and whether its
result requires reopening. A scheduled future check can remain a named limitation;
it cannot support a present-tense claim that its unknown outcome already passed.

Check critique dispositions against the actual incorporated changes or recorded
rejection/deferral rationale. A disposed finding needs a new concrete trigger to
reopen. Legacy confidence scores, `Escalated: Yes`, and an old `Frozen: true` header
alone are not evidence of a resolved decision. Missing evidence is unverifiable,
not success; no percentage threshold or per-pass cadence audit applies.

Report decision drift, unresolved blockers, and unverifiable acceptance separately
from acceptance-test failures. Do not start a new interview for already settled
choices just to complete this audit.

### Step 6 — Evaluate False Positive Risk

Specifically identify:
- outputs that appear successful but violate intent
- metrics that can be satisfied while producing incorrect outcomes
- weak or gameable validation semantics

### Step 7 — Produce Verification Result

Classification:
- VERIFIED
- PARTIALLY VERIFIED
- UNVERIFIABLE
- FAILED

## Output

Write results to the current session artifact:

```text
.socrates/<active-session>/verification.md
```

Or, when `$ARGUMENTS` resolved a specific specification:

```text
verification.md
```

Structure:

```markdown
# Verification Result

Specification Version: vN
Verified Artifact / Commit: <exact target>

## Classification
[VERIFIED | PARTIALLY VERIFIED | UNVERIFIABLE | FAILED]

## Success Criteria
[Pass/fail status for each]

## Acceptance Test Results
[Evidence and outcomes]

## Regression Check Results
[What was validated and what remains uncertain]

## Feedback Loop Design Usage
[Was the designed in-progress signal actually invoked? Spec gap or execution gap if not?]

## Decisions and Readiness
[Were settled choices preserved? Are blockers resolved, critique findings disposed,
and accepted uncertainties backed by user acceptance and the promised checks?]

## Failure Signals
[Any triggered failure indicators]

## False Positive Risks
[Ways the result may still be incorrect]

## Residual Uncertainty
[What remains unknown or unverifiable]
```

## Verification Constraints

Do not:
- redefine success criteria during verification
- silently weaken validation requirements
- assume missing evidence implies success

Escalate unverifiable claims explicitly.
