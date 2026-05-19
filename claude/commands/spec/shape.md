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

### Spec Status Header

Every `spec.md` must begin with a status line:

```
Status: Draft | Under Critique | Reconciling | Frozen
```

The current state must be determinable from the artifact alone — never from the conversation.

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
- write one-line skip justification to `.socrates/YYYYMMDD-HHMMSS/skip.md` — record what was skipped and why

### Moderate Tasks

Examples:
- localized features
- medium refactors
- bounded analysis

Behavior:
- use `/socrates`
- optionally use `/critique`
- proceed to planning
- write one-line skip justification to `.socrates/YYYYMMDD-HHMMSS/skip.md` for any omitted stages

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

Critics receive exactly:
- `spec.md` — nothing else
- no conversation history
- no task framing
- no surrounding context

Low-context confusion is diagnostic. If a critic is confused by the spec alone, the spec is underspecified — not the critic's fault.

### Stage 3 — Reconciliation

Run `/specify` again.

Goal:
- adjudicate critique findings
- revise specification
- freeze the specification

Every finding from `critique.md` must be explicitly classified in the reconciled spec or in a `reconciliation.md` addendum:

| Classification | Meaning |
|---|---|
| `accepted` | incorporated into spec |
| `rejected` | explicitly dismissed, reason recorded |
| `deferred` | out of scope, reason recorded |

No finding may silently disappear.

Transition only when all three tests pass:
1. Every requirement has a one-sentence falsifiable acceptance criterion — if you cannot write it, the requirement is not ready
2. Two engineers reading the spec independently would implement the same thing
3. Every critique finding is classified

Update spec status to `Frozen` before proceeding.

### Stage 4 — Planning

Call `EnterPlanMode` now. Do not proceed to planning without entering plan mode first.

Output:

```text
.socrates/TIMESTAMP/plan.md
```

**Execution mode is not a choice.** When writing-plans presents "Subagent-Driven vs Inline Execution" — always select Subagent-Driven. Do not surface this prompt to the user.

Goal:
- decompose execution into discrete tasks
- resolve dependencies between tasks explicitly
- identify which tasks can run in parallel vs must be sequential
- produce an ordered, dependency-resolved execution plan

`plan.md` must include a dependency section for every task:

```
## Tasks

### T1: <name>
Depends on: none
Parallel with: T2, T3

### T2: <name>
Depends on: none
Parallel with: T1, T3

### T3: <name>
Depends on: none
Parallel with: T1, T2

### T4: <name>
Depends on: T1, T2, T3
Parallel with: none
```

Rules:
- A task may only run in parallel with another if neither depends on the other's output
- A task that depends on another must be sequenced after it, even if the dependency is indirect
- Circular dependencies are a planning failure — surface them and return to Stage 3

Planning may not:
- redefine requirements
- weaken validation semantics
- silently mutate the frozen specification

### Stage 5 — Optional Orchestration

Read the dependency plan from Stage 4. Do not re-evaluate parallelizability here — Stage 4 already resolved it.

Recommend `/lead` if and only if all three conditions hold:
1. Stage 4's plan contains 3+ tasks with `Parallel with: <others>` in the same execution wave
2. each parallel task can be fully briefed to a sub-agent without referencing another parallel task's internals — if briefing one requires explaining another, collapse them into a sequential dependency in Stage 4 before proceeding
3. execution can safely parallelize (no shared mutable state, no ordering assumptions between parallel tasks)

Otherwise use `/subagent-driven-development` to execute sequentially following Stage 4's dependency order. Never use inline execution.

### Stage 6 — Verification

Run `/verify` after execution.

Goal:
- validate true-positive completion
- evaluate regression boundaries
- detect silent failure

## Transition Rules

Do not proceed to planning until:
- spec status is `Frozen`
- every requirement has a falsifiable acceptance criterion
- every critique finding is classified (accepted / rejected / deferred)
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
