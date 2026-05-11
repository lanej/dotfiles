---
description: "Run the semantic alignment workflow from specification through validation-ready execution planning"
argument-hint: [task description]
allowed-tools:
  - Read
  - Write
  - Edit
  - Task
  - Bash(cat:*)
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

The goal is bounded semantic alignment before execution commitment.

## Lifecycle

```text
Intent
→ Specify
→ Critique
→ Reconcile
→ Freeze
→ Plan
→ Execute
→ Verify
```

Lifecycle semantics are authoritative here.

## Artifact Model

All stages operate on explicit artifacts inside:

```text
.socrates/YYYYMMDD-HHMMSS/
```

Primary artifacts:
- `spec.md`
- `critique.md`
- `plan.md`
- `verification.md`

Artifacts are authoritative.
Conversation is transient.

## Adaptive Rigor

Do not apply full shaping rigor to every task.

### Trivial Tasks

Examples:
- typo fixes
- tiny refactors
- isolated edits

Behavior:
- bypass shaping workflow
- execute directly

### Moderate Tasks

Examples:
- localized features
- medium refactors
- bounded analysis

Behavior:
- use `/socrates`
- optionally use `/critique`
- proceed to planning

### Complex or High-Risk Tasks

Examples:
- infrastructure migrations
- architectural changes
- multi-system coordination
- ambiguous strategic work
- high regression risk

Behavior:
- require full shaping workflow
- require critique
- require explicit validation semantics
- require verification after execution

## Workflow Stages

### Stage 1 — Specification

Run `/specify`.

Output:

```text
.socrates/TIMESTAMP/spec.md
```

Goal:
- interrogate ambiguity
- define requirements
- define validation semantics
- establish execution boundaries
- decompose the problem into legible requirement layers

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

Critics should receive:
- the specification
- minimal surrounding context

Low-context confusion is diagnostic.

### Stage 3 — Reconciliation

Run `/specify` again.

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

Use Claude Code built-in `/plan` behavior.

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

If:
- 3+ independent execution tracks exist
- execution can safely parallelize
- interfaces are well-defined

then:
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

Pause automatically:
- after specification freeze
- before orchestration
- before irreversible execution

If:
- critique reveals unresolved ambiguity
- execution changes assumptions
- validation fails
- regression checks fail

then:
- reopen the specification
- transition back to specification reconciliation

## Recommended Usage

```bash
/shape "Add carbon-aware carrier recommendations"
```

Typical flow:

```text
1. /specify
2. /critique
3. /specify
4. STOP + review
5. /plan
6. optional /lead
7. /verify
```

Do not optimize for full autonomy by default.

Optimize for legible delegation.
