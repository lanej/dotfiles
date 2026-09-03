---
description: "Compile ambiguous intent into a validated execution-ready specification"
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
  - shaping
---

# /specify — Semantic Alignment and Specification Compilation

Purpose: convert ambiguous task intent into a validated execution-ready specification.

The interrogation is the means, not the end.

This command does NOT:
- generate implementation plans
- orchestrate execution
- mutate requirements during execution

This command DOES:
- interrogate ambiguity
- challenge assumptions
- surface hidden constraints
- define validation contracts
- establish execution boundaries
- reconcile critique findings
- decompose problems into legible requirement layers
- produce a validated specification artifact suitable for downstream planning

## Core Principle

Challenge assumptions rather than validating them.

The goal is semantic precision, not conversational agreement.

Interrogate until:
- ambiguity is bounded
- validation semantics exist
- false-positive paths are identified
- false-negative risks are surfaced
- execution boundaries are explicit
- the problem is decomposed into stable, independently understandable requirement layers

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

Planning and orchestration occur in downstream commands.

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
8. Verification (completion + in-progress signal/cadence + fallback if no fast signal exists)
9. Constraints
10. Stakeholders
11. Risk
12. Execution Readiness
13. Harmony (evaluated every pass, not only when touched — see Commandment Scoring below)

### Engineering

14. Modularity
15. Separation
16. Robustness
17. Repair
18. Least Surprise
19. Regression Protection

### Research/Analysis

14. Falsifiability
15. Reproducibility
16. Bias
17. Causation

### Writing

14. Audience
15. Argument
16. Evidence
17. Action

## Session File Location

Files live in `.socrates/` within the current working directory.

Each specification session lives in a timestamped directory:

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

5. Set status to `Interrogating` and `Current Pass: 1`
6. Classify task type
7. Pre-fill inferable sections
8. Score commandment states:
   - stable
   - fragile
   - ambiguous
   - contradictory
   - open

   For each commandment touched this pass, also append a Pass 1 row to spec.md's `## Commandment
   Scores` table — state, confidence score (0-100%), Why, Why not 100%, Escalated, Resolution (see
   Commandment Scoring below). Harmony always gets a Pass 1 row, whether or not it was otherwise
   discussed.
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

5. Increment `Current Pass` by 1, regardless of whether anything gets a Commandment Scores row
   this pass
6. Re-score commandment states — for each commandment touched this pass, append a new row to the
   Commandment Scores table. Harmony always gets a new row this pass, whether or not it was
   otherwise discussed.
7. Ask additional questions only where semantic risk remains
8. Update specification

## Alignment States

- Stable
- Fragile
- Ambiguous
- Contradictory
- Open

Do not mark a section stable unless:
- explicit specification text exists
- validation semantics exist where applicable

## Commandment Scoring

In addition to its alignment state, every commandment touched in a pass gets a row in spec.md's
`## Commandment Scores` table (see Spec Scaffold) — never overwrite a prior row, always append:

- **Score** — a confidence percentage (0-100%) in the current alignment-state assessment.
- **Why** — the causal/historical reason the underlying requirement, constraint, or existing
  behavior is the way it is. Sourced from research, not from uncertainty about the score.
- **Why not 100%** — what's driving the confidence gap in the score itself.
- **Escalated** — Yes/No: was a sub-70% score surfaced to the user as a dialogue question this
  pass?
- **Resolution** — if Escalated is Yes, a one-line note of how it was resolved, or a pointer to
  where the resolution is recorded elsewhere in the spec.

**Harmony always runs.** Unlike every other commandment — scored only when touched — Harmony is
evaluated and given a new row every single pass, whether or not it came up in discussion, because
consistency can break silently in parts of the spec nobody is actively discussing.

**Deferral rule.** Any commandment (including Harmony) scoring below 70% must be surfaced to the
user as a dialogue question — framed as sharpening the user's own thinking and the assistant's
understanding, not just closing a spec gap — never silently recorded as an assumption. Record
`Escalated: Yes` and the `Resolution` once answered.

**Pass counter.** `Current Pass` (see Spec Scaffold) is an independent counter: set to 1 on
Initialization, incremented by 1 on every Continuation invocation, regardless of whether anything
gets a row that pass. This is what makes Harmony's cadence auditable later — verification checks
that every integer from 1 to `Current Pass` has a corresponding Harmony row.

A specification may not transition to `Validated`/`Frozen: true` while any row in the Commandment
Scores table has `Score < 70%` and `Escalated: No` (see Specification Freeze below).

## Interrogation Principles

- One topic per question.
- Ask "why" to surface unstated assumptions.
- Ask "what happens when X fails" to probe robustness.
- Ask "what happens if we don't do this?" to expose necessity and timing assumptions.
- Ask "who decides?" to surface ownership and escalation boundaries.
- Ask "what is explicitly excluded?" to sharpen scope.
- Ask "how would we know this worked?" to expose weak validation semantics.
- Ask "what could appear successful while actually be wrong?" to expose false positives.
- Ask "what would be missing from an apparently good result?" to expose false negatives.
- Ask "what must not break?" to surface regression boundaries.
- Ask "what tells you mid-flight that you're still on track, and what does that check cost?" to expose a missing Feedback Loop Design.
- Ask "how would this fail silently?" to identify observability gaps.
- Ask "why is this the way it is" before scoring a commandment — the rationale, not just the state, is the point.
- Challenge vague answers — sharpen them or classify them as ambiguous or fragile.
- Prefer one question that resolves multiple ambiguities.
- Prefer high-leverage clarification over exhaustive questioning.

## Contradiction Detection

Actively identify:
- conflicting goals
- conflicting constraints
- requirements that invalidate each other
- success criteria that undermine requirements
- validation semantics that can be gamed

Do not normalize contradictions into the specification.
Resolve them, bound them, or classify them explicitly.

## Interpretation Check

Maintain:

```markdown
## Current Interpretation

[The task as currently understood in executable terms]

## Misclassification Risks

### Potential False Positives

### Potential False Negatives
```

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

Each layer must be justified by the layer below it.

If a layer fails scrutiny:
- return to interrogation
- revise the specification
- re-evaluate downstream layers

### Problem Decomposition

The specification must decompose the problem into independently understandable requirement layers.

Requirements should:
- have stable identifiers (`R1`, `R2`, etc.)
- be traceable to the problem statement
- support downstream execution planning
- expose dependency relationships where meaningful
- separate policy from implementation mechanism

This decomposition exists to support downstream `/plan` usage.

### Validation Requirements

Validation must include:
- acceptance tests
- regression checks
- failure signals
- verification methods
- Feedback Loop Design (in-progress signal, cost/cadence, fallback if no fast signal exists)
- known blind spots

## Specification Freeze

When:
- commandment states are stable or explicitly accepted as fragile
- validation semantics exist
- Feedback Loop Design is populated for at least the load-bearing requirements (not left unpopulated)
- ambiguity is bounded
- execution readiness is explicit
- no row in the Commandment Scores table has `Score < 70%` and `Escalated: No`

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

## Critique Integration

`/specify` owns reconciliation.

Critics:
- identify findings
- do not mutate specifications directly

Specify:
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
Current Pass: 1

## Commandment Scores

| Pass | Commandment | State | Score | Why | Why not 100% | Escalated | Resolution |
|---|---|---|---|---|---|---|---|

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

### Feedback Loop Design

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
- Claude Code built-in `/plan` → execution decomposition and dependency topology
- `Workflow` → orchestration (author a script directly)
- `/verify` → validation and regression verification

`/specify` ends at validated specification generation.
