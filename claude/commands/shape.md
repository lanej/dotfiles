---
description: "Run the semantic alignment workflow from specification through validation-ready execution planning"
argument-hint: "task description"
allowed-tools:
  - Read
  - Write
  - Edit
  - Agent
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

This command owns orchestration. Read `$HOME/.claude/commands/socrates/dialogue.txt`
for the canonical dialogue, session, evidence, readiness, reconciliation, and reopen
semantics. Do not duplicate those gates here. Read `phases-2-3.txt` beside it for
plan-mode writing and approval rules before Stage 4.

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

Artifacts preserve decisions and evidence across sessions. A new user instruction can revise an earlier decision; record the change through the shared reopen procedure.

### Spec Status Header

Every `spec.md` must begin with a status line:

```
Status: Interrogating | Critiquing | Reconciling | Validated | Planned | Executing | Verified
Frozen: true | false
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
- use `/specify` for the shared dialogue, stopping before planning
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
- `spec.md` plus the shared evidence/readiness contract — no additional task facts
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

Use the shared critique reconciliation procedure and readiness gate. Process only
unresolved relevant findings, record each disposition and its reason/change, and
preserve prior artifacts. A rejected or deferred finding must not conceal a blocker.
Freeze the spec only when the shared gate passes; classification alone is not
resolution. Proceed to planning without a redundant approval pause for the freeze.

### Stage 4 — Planning

Call `EnterPlanMode` after the shared readiness gate passes. Follow the planning companion: write only the harness plan file while in plan mode, seek plan approval through `ExitPlanMode`, and persist the approved version as the session plan only after writes are permitted. Record the specification version in the plan and set the spec to `Planned` only after approval. Preserve any previous plan before replacing it.

Output:

```text
.socrates/TIMESTAMP/plan.md
```

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
Feedback signal: <the cheapest concrete check that would catch a fault in this task's own deliverable — scoped to the changed file/package, not the full suite, and not a pointer to the final review>

### T2: <name>
Depends on: none
Parallel with: T1, T3
Feedback signal: <the cheapest concrete check that would catch a fault in this task's own deliverable — scoped to the changed file/package, not the full suite, and not a pointer to the final review>

### T3: <name>
Depends on: none
Parallel with: T1, T2
Feedback signal: <the cheapest concrete check that would catch a fault in this task's own deliverable — scoped to the changed file/package, not the full suite, and not a pointer to the final review>

### T4: <name>
Depends on: T1, T2, T3
Parallel with: none
Feedback signal: <the cheapest concrete check that would catch a fault in this task's own deliverable — scoped to the changed file/package, not the full suite, and not a pointer to the final review>
```

Example:

```
### T7: Add rate-limit header parsing
Depends on: none
Parallel with: T8
Feedback signal: unit test asserting `parse_headers()` returns the documented `Retry-After` value for a captured 429 response fixture
```

Rules:
- A task may only run in parallel with another if neither depends on the other's output
- A task that depends on another must be sequenced after it, even if the dependency is indirect
- Circular dependencies are a planning failure — surface them and return to Stage 3
- A task's `Feedback signal:` must name a check specific to that task's own deliverable — never a pointer to the final whole-plan review
- Choose the affected feature's acceptance check (V1, see `~/.files/docs/verification.md`). Broaden it when shared behavior or evidence of an interaction requires more coverage. State which uncertainty the additional check resolves.
- Every task ends in its own commit. That, not suite breadth, is what preserves attribution when Stage 6 surfaces a fault

Planning may not:
- redefine requirements
- weaken validation semantics
- silently mutate the frozen specification

### Stage 5 — Optional Orchestration

Read the dependency plan from Stage 4. Do not re-evaluate parallelizability here — Stage 4 already resolved it.

Recommend invoking `Workflow` directly (author a script matching Stage 4's task graph — `parallel()` for the concurrent wave, sequential `agent()` calls for the rest) if and only if all three conditions hold:
1. Stage 4's plan contains 3+ tasks with `Parallel with: <others>` in the same execution wave
2. each parallel task can be fully briefed to a sub-agent without referencing another parallel task's internals — if briefing one requires explaining another, collapse them into a sequential dependency in Stage 4 before proceeding
3. execution can safely parallelize (no shared mutable state, no ordering assumptions between parallel tasks)

Otherwise execute sequentially with one `Agent` dispatch per task, following Stage 4's dependency order. Never use inline execution.

**Incremental review (V3a).** Use a bounded review at a wave boundary when interacting
changes or unresolved uncertainty warrant independent judgment. Brief it with the relevant
fault classes in `~/.files/docs/verification.md`. Address actionable findings before work
that depends on them. Reserve review of the assembled change for Stage 6 when required
by its complexity or repository policy.

### Stage 6 — Verification

Validate the assembled result against `spec.md` and the repository's requirements:

1. Run affected acceptance checks and any broader suite, lint, or type checks needed for
   the changed interactions (V1/V2). Avoid repeating valid results without a new reason.
2. Obtain independent review of the complete diff when complexity or repository policy
   requires it (V3b). Address actionable findings and rerun checks invalidated by fixes.
3. Use `/verify` to assess the spec's validation contract and report unresolved gaps.

Where CI exists, distinguish its results from local validation. After an authorized merge,
check the merged commit's CI status (V4) before claiming CI success. A failed check or
review finding may justify broader validation of related work; name the concrete risk
and choose checks that can detect it.

## Transition Rules

Proceed to planning only when the shared evidence/readiness gate passes. Readiness
is not execution authorization. Obtain approval of the resulting plan before
execution and honor applicable authority boundaries for orchestration or irreversible
actions. No extra pause is required merely because specification freeze completed.

If critique, changed evidence, scope, or verification invalidates a frozen decision,
use the shared reopen procedure, including versioning and preservation. Revisit only
the affected decisions; do not restart the interview.

## Recommended Usage

```bash
/shape "Add carbon-aware carrier recommendations"
```

Typical flow:

```text
1. /specify
2. /critique
3. /specify — reconcile findings and validate using the shared gate
4. EnterPlanMode — draft the implementation plan automatically
5. ExitPlanMode — obtain approval of the completed plan
6. Execute the approved plan; optional Workflow when appropriate
7. /verify
```

Do not optimize for full autonomy by default.

Optimize for legible delegation.
