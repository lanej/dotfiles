---
name: shape
description: Coordinate specification, critique, reconciliation, planning, approved execution, and verification. Use when explicitly asked to shape a task or run the complete Socrates workflow.
---

# Shape

This skill owns orchestration; the linked capabilities own their contracts. Read [the dialogue contract](../socrates/references/dialogue.txt) and apply its session resolver and lifecycle rules. All specification artifacts remain in the same `.socrates/YYYYMMDD-HHMMSS/` directory.

Choose rigor from actual consequence. A trivial isolated edit can skip shaping and proceed within existing authority; record why in the session's `skip.md`. A localized moderate task uses specification and planning, with critique when consequential uncertainty warrants it; record any critique skip. Architectural, shared-state, ambiguous, or high-risk tasks require the full path below. Do not classify a task merely to bypass an applicable repository gate.

1. Read and apply [specify](../specify/SKILL.md). Resolve consequential ambiguity and develop the validation contract. A resumed session retains supported later states and settled decisions.
2. Read and apply [critique](../critique/SKILL.md) when required. Independent critics receive the spec and readiness contract, not the author's conversation. If independence is unavailable, report the unmet gate rather than treating an inline pass as independent.
3. Reconcile only relevant unresolved findings through `specify`. Preserve evidence, record dispositions, and reopen/version a frozen spec before substantive changes. Freeze only when the shared readiness gate passes.
4. Read and apply [the planning handoff](../socrates/references/phases-2-3.txt). Draft immediately after readiness, with requirements traced to tasks, dependencies, safe parallel work, and proportionate feedback checks. Obtain approval of the concrete plan before execution; freezing is not approval. Do not claim to change Codex's collaboration mode.
5. Execute the approved plan within its authority. Use the host's actual agent capabilities for independently bounded tracks when useful; keep dependent/shared-state tasks sequential. Inline execution is appropriate where delegation adds no benefit or is unavailable. Do not require a nonexistent `Workflow` tool or impose a new per-task commit policy over the repository's conventions. Obtain required independent review and resolve actionable findings.
6. Read and apply [verify](../verify/SKILL.md) against the matching specification version and exact delivered target. Preserve failed, partial, and unknown outcomes; report remaining work without calling it verified.

The spec's saved status distinguishes `Interrogating`, `Critiquing`, `Reconciling`, `Validated`, `Planned`, `Executing`, and `Verified`. Do not regress a supported later state just because the workflow was invoked again. Set `Planned` only after approval of the matching plan and `Executing` only when authorized execution starts. Before execution, confirm that the planned version still matches the frozen spec. New evidence that invalidates a decision returns through the shared reopen procedure; do not silently rewrite intent during execution.

Honor host write/approval restrictions throughout. A missing capability or an unresolved blocking choice remains an explicit blocker; neither a saved artifact nor an agent's dispatch proves the next stage happened.
