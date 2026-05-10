---
description: "Interrogate a task through Socratic dialogue to produce a validated execution-ready specification"
argument-hint: ["Task Title" (init) or empty (continue)]
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(date:*)
  - Bash(mkdir:*)
tags:
  - specification
  - validation
  - socratic
---

# /socrates — Semantic Alignment and Specification Compilation

Purpose: convert ambiguous task intent into a validated execution-ready specification.

The Socratic dialogue is the means, not the end.

This command does NOT:
- generate implementation plans
- orchestrate execution
- enter plan mode automatically
- mutate requirements during execution

This command DOES:
- interrogate ambiguity
- surface hidden assumptions
- define success semantics
- define validation contracts
- establish execution boundaries
- reconcile critique findings
- produce a validated specification artifact

## Lifecycle

Specifications move through explicit states:

```text
Interrogating
→ Critiquing
→ Reconciling
→ Validated
→ Planned
→ Executing
→ Verified
```

Planning and execution occur in downstream commands.

## Semantic Alignment Goals

Optimize for:
- minimizing false positives
- minimizing false negatives
- maximizing true positives

Definitions:
- False positive: execution appears successful while violating actual intent.
- False negative: critical requirements, constraints, or context were omitted.
- True positive: the task is understood correctly and validated against explicit success semantics.

## Commandments

Quality gates applied to the current specification.

### Universal

1. Problem First
2. Interpretation
3. Clarity
4. Scope
5. Context
6. Parsimony
7. Success
8. Verification
9. Constraints
10. Stakeholders
11. Risk
12. Execution Readiness

### Engineering

13. Modularity
14. Separation
15. Robustness
16. Repair
17. Least Surprise
18. Regression Protection

### Research/Analysis

13. Falsifiability
14. Reproducibility
15. Bias
16. Causation

### Writing

13. Audience
14. Argument
15. Evidence
16. Action

## Session File Location

Files live in `.socrates/` within the current working directory.

Each Socrates session lives in a timestamped directory:

```text
.socrates/YYYYMMDD-HHMMSS/
```

Session artifacts:
- `spec.md` — authoritative specification
- `critique.md` — critique findings
- `verification.md` — verification results
- `plan.md` — downstream execution plan

Pointer file:
- `.socrates/.current`

`.socrates/.current` contains the active session directory name.

Example:

```text
.socrates/
├── .current
├── 20260510-154233/
│   ├── spec.md
│   ├── critique.md
│   ├── verification.md
│   └── plan.md
```

Timestamped sessions are intentionally preserved:
- historical reasoning matters
- critique evolution matters
- validation history matters
- reopening specifications should retain prior state

Do not overwrite older session directories.

## Initialization (`$ARGUMENTS` is a task title)

1. Generate timestamp using:

```bash
 date +%Y%m%d-%H%M%S
```

2. Create:

```text
.socrates/TIMESTAMP/
```

3. Create:

```text
.socrates/TIMESTAMP/spec.md
```

4. Write the timestamp directory name to:

```text
.socrates/.current
```

5. Set status to `Interrogating`
6. Classify task type
7. Pre-fill inferable sections
8. Score commandment states:
   - stable
   - fragile
   - ambiguous
   - contradictory
   - open
9. Generate initial interpretation
10. Ask 2–3 high-leverage interrogation questions

## Continuation (no `$ARGUMENTS`)

1. Read `.socrates/.current`
2. Resolve active session directory
3. Load:

```text
.socrates/TIMESTAMP/spec.md
```

4. If critique exists:

```text
.socrates/TIMESTAMP/critique.md
```

then:
- enter `Reconciling`
- adjudicate critique findings
- revise specification
- classify unresolved disagreements

5. Re-score commandment states
6. Ask additional questions only where semantic risk remains
7. Update specification

## Alignment States

- Stable
- Fragile
- Ambiguous
- Contradictory
- Open

Do not mark a section stable unless:
- explicit specification text exists
- validation semantics exist where applicable

## Specification Freeze

When:
- commandment states are stable or explicitly accepted as fragile
- validation semantics exist
- ambiguity is bounded
- execution readiness is explicit

then:
- set status to `Validated`
- freeze the specification
- assign a specification version

Example:

```markdown
Status: Validated
Specification Version: v3
Frozen: true
```

A frozen specification may not be silently mutated by:
- planners
- executors
- verifiers
- critics

## Reopen Semantics

If:
- critique exposes unresolved ambiguity
- execution changes assumptions
- validation fails
- regression checks fail

then:
- reopen the specification
- transition back to `Interrogating` or `Reconciling`

Do not destroy prior validation or critique artifacts when reopening.

## Interpretation Check

Maintain:

```markdown
## Current Interpretation

[The task as currently understood in executable terms]

## Misclassification Risks

### Potential False Positives

### Potential False Negatives
```

## Interrogation Principles

- One topic per question
- Challenge vague answers
- Prefer semantic precision over conversational flow
- Ask "how would we know this worked?"
- Ask "what could appear successful while actually be wrong?"
- Ask "what must not break?"
- Ask "how would this fail silently?"
- Ask "what assumptions are being treated as obvious?"
- Prefer high-leverage clarification questions

## Validation and Layered Reasoning

A specification is not execution-ready until:
- success criteria exist
- validation semantics exist
- regression semantics exist
- authority boundaries exist
- ambiguity is bounded

Generate:

```text
Layer 1 — Problem
Layer 2 — Requirements
Layer 3 — Constraints
Layer 4 — Risks
Layer 5 — Success
Layer 6 — Validation
Layer 7 — Execution Readiness
```

Validation must include:
- acceptance tests
- regression checks
- failure signals
- verification methods
- known blind spots

## Critique Integration

`/socrates` owns reconciliation.

Critics:
- identify findings
- do not mutate specifications directly

Socrates:
- adjudicates findings
- revises the specification
- preserves authoritative intent

## Spec Scaffold (`spec.md`)

```markdown
# [Title]

Status: Interrogating
Specification Version: v1
Frozen: false
Type: [Engineering | Research/Analysis | Writing | General]

## Problem Statement

## Requirements

### R1

## Constraints

### C1

## Success Criteria

### S1

## Validation Contract

### Acceptance Tests

### Regression Checks

### Failure Signals

### Verification Methods

### Known Blind Spots

## Inputs

## Outputs

## Authority Boundaries

### Executor May Decide

### Executor Must Escalate

### Executor Must Not Change

## Current Interpretation

## Misclassification Risks

### Potential False Positives

### Potential False Negatives

## Ambiguities

### Blocking

### Non-Blocking

### Intentional

## Risks

## Stakeholders
```

## Downstream Commands

After validation:
- `/critique` → adversarial specification review
- `/plan` → execution decomposition
- `/lead` → orchestration
- `/verify` → validation and regression verification

`/socrates` ends at validated specification generation.
