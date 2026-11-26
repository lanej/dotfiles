---
name: shape
description: Coordinate specification, critique, reconciliation, planning, approved execution, and verification. Use when asked to shape a task, run the complete Socrates workflow, or execute and verify a saved approved Socrates plan.
---

# Shape

This skill owns orchestration and the linked capabilities own their contracts. Read [the dialogue contract](../socrates/references/dialogue.txt) and apply its session resolver and lifecycle rules. Keep all artifacts together under the selected `.socrates/` session directory.

When the user explicitly instructs execution of a saved approved plan, resolve that session and start at **Execute and verify** with the current artifacts. Approval alone ends at `Planned`. For a `Verified` session, match the requested spec version and plan revision to the current artifacts and verification evidence before returning that evidence. Report a mismatch without replaying tasks.

Choose rigor from actual consequence. A trivial isolated edit can skip shaping and proceed within existing authority; record why in the session's `skip.md`. A localized moderate task uses specification and planning, with critique when consequential uncertainty warrants it; record any critique skip. Architectural, shared-state, ambiguous, or high-risk tasks require the full path below. Do not classify a task merely to bypass an applicable repository gate.

1. Read and apply [specify](../specify/SKILL.md). Resolve consequential ambiguity and develop the validation contract. A resumed session retains supported later states and settled decisions.
2. Read and apply [critique](../critique/SKILL.md) when required. Independent critics receive the spec and readiness contract, not the author's conversation. If independence is unavailable, report the unmet gate rather than treating an inline pass as independent.
3. Reconcile only relevant unresolved findings through `specify`. Preserve evidence, record dispositions, and reopen/version a frozen spec before substantive changes. Freeze only when the shared readiness gate passes.
4. Read and apply [the planning handoff](../socrates/references/phases-2-3.txt). Draft immediately after readiness, with requirements traced to tasks, dependencies, safe parallel work, and proportionate feedback checks. Obtain approval of the concrete plan before execution; freezing is not approval. Do not claim to change Codex's collaboration mode.
5. When execution is authorized, continue to **Execute and verify**.

## Execute and verify

Read `spec.md` and `plan.md` for the selected session. Confirm that the requested versions match the frozen spec and approved plan. Compare the plan with the recorded reviewed draft, allowing only status, approval, and authorization metadata to differ. When an older plan lacks that reference, use existing evidence of approval for its exact content. If the match cannot be established, resolve that approval gap before execution. Confirm execution authority, record the instruction against that revision if needed, and satisfy applicable pre-execution gates within current authority. A valid handoff proceeds without repeating settled questions, planning, or approval. New evidence that invalidates a decision returns through the shared reopen procedure before affected work proceeds.

Set `Executing` when authorized work starts. Run tasks in dependency order and check each deliverable. Apply the shared progress record procedure, including a checkpoint after each task check and before starting dependent work. On resume, reconcile actual results and interrupted actions with the progress record before taking further action. Use the per-task model and reasoning recommendations where the host supports them. If a recommendation is unavailable, choose an available option that meets the task's required capabilities. Use the host's available agents for independently bounded tracks when useful. Keep tasks that share mutable state sequential. Inline execution fits tasks that gain no benefit from delegation or lack an available agent. Follow repository commit and review conventions. Obtain required independent review and resolve actionable findings.

Follow the plan's failure actions and fix recoverable problems within the approved scope. Carry the work through final acceptance without asking for another prompt between tasks. Escalate when a new decision, additional authority, or an unavailable requirement actually blocks progress. Complete independent work within scope before returning a blocker.

Read and apply [verify](../verify/SKILL.md) against the matching specification version and exact delivered target. The intended outcome is `verification.md` with evidence for the promised checks and `Verified` when the full contract passes. Preserve failed, partial, and unknown outcomes and report what remains.

The spec's saved status distinguishes `Interrogating`, `Critiquing`, `Reconciling`, `Validated`, `Planned`, `Executing`, and `Verified`. Do not regress a supported later state just because the workflow was invoked again. Set `Planned` only after approval of the matching plan and `Executing` only when authorized execution starts. Before execution, confirm that the planned version still matches the frozen spec. New evidence that invalidates a decision returns through the shared reopen procedure; do not silently rewrite intent during execution.

Honor host write/approval restrictions throughout. A missing capability or an unresolved blocking choice remains an explicit blocker; neither a saved artifact nor an agent's dispatch proves the next stage happened.
