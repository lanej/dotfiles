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
- It must be the *narrowest* such check (tier V1, see the `methodology` skill's Verification Rigor Tiers). A full-suite run is not a valid per-task Feedback signal: the full suite is a branch-level gate (V2) that runs once, in Stage 6. Broader tests can catch interactions they exercise; they do not replace the Stage 6 whole-branch review. The escalation rule overrides the default scoped signal
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

Otherwise use `/subagent-driven-development` to execute sequentially following Stage 4's dependency order. Never use inline execution.

**Wave review checkpoint (V3a).** At each wave boundary in Stage 4's graph — after the last task of a parallel wave completes, or after each task in a fully sequential plan's natural grouping — dispatch a review agent over **only the diff since the last checkpoint**, briefed with the `methodology` skill's Review Fault Classes. Do not re-review the whole branch here; that is Stage 6's job and its cost grows with the branch, while this one stays bounded.

This is the cadence lever on compounding. The historical audit found faults that the existing tests missed, so review wave 1 when it lands rather than waiting until Stage 6. A wave-boundary checkpoint also keeps attribution tight: a finding traces to the two or three tasks in that wave, not to a forty-file branch diff.

Fix wave-review findings before starting the next wave. A finding carried forward is the compounding case this checkpoint exists to prevent.

### Stage 6 — Verification

Runs on the final branch after the last task; repeat affected checks and the branch gate if review fixes change verified code. This is the *full-suite and whole-branch* pass — it does not run between tasks. (Incremental review does, at Stage 5's wave checkpoints; that is a different, bounded thing.) Three steps in order, each gating the next:

1. **Branch gate (V2)** — full test suite, full lint/type-check, on the complete branch. First point in the flow where the whole suite runs.
2. **Whole-branch review (V3b)** — review agent over the complete diff against `spec.md`. This is the stage that catches what per-task checks structurally cannot: cross-task interaction faults, pattern-level bug classes, spec drift. Budget rigor here, not in Stages 4–5.
3. **`/verify`** — validate the spec's validation contract.

Where the branch merges into a repo with CI, **V4** follows: poll the merged commit's own check-runs and classify against the pre-merge commit. A clean local V2 is not a CI pass — one audited fault was a task's own regression test passing locally and failing on main's post-merge CI.

Goal:
- validate true-positive completion
- evaluate regression boundaries
- detect silent failure

If step 1 or 2 surfaces a fault a per-task `Feedback signal:` should have caught, the trip-wire in `CLAUDE.md` (Proportional Verification) applies to any remaining or follow-up work: promote per-task checks to V2 and say so.

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
