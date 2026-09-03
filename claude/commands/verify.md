---
description: "Verify execution results against a Socrates validation contract"
argument-hint: [artifact path, task output, or empty]
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(cat:*)
  - Task
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

If `$ARGUMENTS` is empty:
1. Read `.socrates/.current`.
2. Treat its contents as the active session directory name.
3. Read `.socrates/<active-session>/spec.md`.
4. Write verification output to `.socrates/<active-session>/verification.md`.

If `$ARGUMENTS` is provided:
1. Read the provided artifact or execution output.
2. Resolve the nearest matching Socrates `spec.md` if possible.
3. Write verification output next to the resolved specification as `verification.md`.

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

Surface "loop skipped" as its own failure category, distinct from "acceptance test failed."

### Step 5 — Evaluate Harmony Cadence and Deferral

Reading only spec.md's `## Commandment Scores` table (no conversation access needed):

- Collect the set of distinct `Pass` numbers across all rows. Confirm a Harmony row exists for
  every integer from 1 to `Current Pass`. Any gap is a cadence failure — Harmony was skipped on at
  least one pass.
- For every row with `Score < 70%`, confirm `Escalated: Yes` and a non-empty `Resolution`. Any
  miss is a deferral-rule failure — a low-confidence score was recorded without ever being
  surfaced to the user.

Both are self-contained checks against spec.md alone. Surface either failure as its own category,
distinct from "acceptance test failed."

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

## Harmony Cadence and Deferral
[Does every pass 1..Current Pass have a Harmony row? Does every sub-70% row show Escalated: Yes
with a non-empty Resolution?]

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
