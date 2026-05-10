---
description: "Run the semantic alignment workflow from specification through validation-ready execution planning"
argument-hint: [task description]
allowed-tools:
  - Read
  - Write
  - Edit
  - Task
  - Bash
  - ExitPlanMode
  - EnterPlanMode
tags:
  - workflow
  - shaping
  - orchestration
---

# /shape — Intent Shaping Workflow

Purpose: orchestrate the cognitive lifecycle from ambiguous intent to validated execution-ready planning.

`/shape` is the workflow controller.

It coordinates:
- semantic alignment
- adversarial critique
- reconciliation
- specification freezing
- execution planning
- optional orchestration
- verification preparation

It does NOT replace:
- `/socrates`
- `/critique`
- `/plan`
- `/lead`
- `/verify`

Instead, it composes them into a staged workflow.

## Workflow Philosophy

The goal is not:
- maximum questioning
- maximum detail
- maximum planning

The goal is:
- bounded semantic alignment before execution commitment.

Optimize for:
- minimizing false positives
- minimizing false negatives
- producing validated execution-ready specifications

## Lifecycle

```text
Intent
→ Socrates
→ Critique
→ Reconcile
→ Freeze
→ Plan
→ Execute
→ Verify
```

## Workflow Stages

### Stage 1 — Specification

Run `/socrates`.

Output:

```text
.socrates/TIMESTAMP/spec.md
```

Goal:
- interrogate ambiguity
- define requirements
- define validation semantics
- establish execution boundaries

### Stage 2 — Critique

Run `/critique`.

Output:

```text
.socrates/TIMESTAMP/critique.md
```

Goal:
- expose hidden assumptions
- expose semantic ambiguity
- identify false-positive risks
- identify weak validation semantics

### Stage 3 — Reconciliation

Run `/socrates` again.

Goal:
- adjudicate critique findings
- revise specification
- classify unresolved ambiguity
- freeze the specification

Transition only when:
- semantic ambiguity is bounded
- validation semantics exist
- execution readiness is explicit

### Stage 4 — Planning

Run `/plan`.

Output:

```text
.socrates/TIMESTAMP/plan.md
```

Goal:
- execution decomposition
- dependency topology
- orchestration strategy

Planning may not:
- redefine requirements
- weaken validation semantics
- silently mutate the frozen specification

### Stage 5 — Optional Orchestration

If parallel execution is beneficial:
- recommend `/lead`

Otherwise:
- execute sequentially.

### Stage 6 — Verification

Run `/verify` after execution.

Goal:
- validate true-positive completion
- evaluate regression boundaries
- detect silent failure

## Transition Rules

Do not proceed to planning until:
- specification status is `Validated`
- specification is frozen
- validation contract exists
- authority boundaries exist

If:
- critique reveals unresolved ambiguity
- execution changes assumptions
- validation fails
- regression checks fail

then:
- reopen the specification
- transition back to Socrates reconciliation

## Artifact Discipline

All stages operate on explicit artifacts.

Do not rely on conversational history when structured artifacts exist.

Primary artifacts:

```text
spec.md
critique.md
plan.md
verification.md
```

Artifacts are authoritative.
Conversation is transient.

## Low-Context Critique Principle

Critics should receive:
- the specification
- minimal surrounding context

This intentionally surfaces:
- hidden assumptions
- overloaded terminology
- missing interfaces
- ambiguous execution semantics

Low-context confusion is diagnostic.

## Recommended Usage

```bash
/shape "Add carbon-aware carrier recommendations"
```

Typical flow:

```text
1. /socrates
2. /critique
3. /socrates
4. STOP + review
5. /plan
6. optional /lead
7. /verify
```

## Review Checkpoints

`/shape` should pause at:
- validated specification freeze
- before orchestration
- before irreversible execution

Do not optimize for full autonomy by default.

Optimize for legible delegation.
