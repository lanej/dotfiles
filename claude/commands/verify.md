---
description: "Verify execution results against a Socrates validation contract"
argument-hint: [artifact path, task output, or empty]
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
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
1. Resolve the active Socrates session from `.socrates/.current`
2. Read the associated specification.

Otherwise:
1. Read the provided artifact or execution output.
2. Resolve the nearest matching specification if possible.

## Verification Procedure

### Step 1 — Load Validation Contract

Extract:
- success criteria
- acceptance tests
- regression checks
- failure signals
- verification methods

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

### Step 4 — Evaluate False Positive Risk

Specifically identify:
- outputs that appear successful but violate intent
- metrics that can be satisfied while producing incorrect outcomes
- weak or gameable validation semantics

### Step 5 — Produce Verification Result

Classification:
- VERIFIED
- PARTIALLY VERIFIED
- UNVERIFIABLE
- FAILED

## Output

Write results to:

`.socrates/verification.md`

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
