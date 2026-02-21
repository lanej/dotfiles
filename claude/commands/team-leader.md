---
description: "Orchestrate complex tasks through a team of subagents: discover, plan, reflect, tweak, review, then execute with parallel workstreams"
argument-hint: <task description>
tags:
  - orchestration
  - planning
  - delegation
  - team-leader
---

# /team-leader — Team Leader Orchestrator

You are the **parent coordinator**. Do only these three things:

1. Spawn the pipeline follower (phases 1–4)
2. Present the review gate (phase 5) — this requires user interaction, so it stays here
3. Spawn execution (phase 6) if approved

**Task:** `$ARGUMENTS`

## Step 1: Spawn the Pipeline Follower

Generate a session ID by running: `SESSION=$(date +%Y%m%d-%H%M%S)` and capturing the output.

Then spawn a Task with `subagent_type: "follower"` using the following as the complete prompt. Before sending, substitute:
- The actual task description for `TASK`
- The actual session ID value for `SESSION`

---

**[PIPELINE FOLLOWER PROMPT — pass this verbatim, with TASK and SESSION filled in]**

You are the pipeline coordinator for this task. Run 4 phases sequentially, delegating each to a specialized subagent. Do NOT do the work yourself — delegate everything.

**Task:** TASK

**Session ID:** SESSION

All artifact paths use the prefix `~/.claude/plans/lead-SESSION-`.

**Phase 1: DISCOVER**

Spawn a Task with `subagent_type: "explore"` and `thoroughness: "very thorough"`. The prompt must:
- State the task description
- Ask the agent to find: existing patterns, relevant files, constraints, risks, prior art in the codebase
- Ask it to structure output as: Facts → Hypotheses → Analysis → Conclusions → Recommendations

Write the agent's full output to `~/.claude/plans/lead-SESSION-discovery.md`.

**Phase 2: PLAN**

Read `~/.claude/plans/lead-SESSION-discovery.md`. Spawn a Task with `subagent_type: "follower"`. The prompt must:
- State the task description
- Include a concise summary of discovery findings
- Ask the agent to: evaluate architectural options (at least 3), select an approach with justification, define implementation steps, identify dependencies and risks
- Ask it to structure output as: Approach → Steps → Dependencies → Risks → Verification

Write the agent's full output to `~/.claude/plans/lead-SESSION-plan.md`.

**Phase 3: REFLECT**

Read `~/.claude/plans/lead-SESSION-discovery.md` and `~/.claude/plans/lead-SESSION-plan.md`. Spawn a Task with `subagent_type: "follower"`. The prompt must:
- State the task description and include the plan content
- Frame the role: "You are a senior engineer reviewing this plan adversarially. Find what's wrong, not what's right."
- Ask it to apply layered reasoning as:
  - Observe: What does the plan assume? What could it have missed?
  - Hypothesize: 3+ ways this plan could fail or be suboptimal
  - Analyze: Likelihood and evidence for each failure mode
  - Conclude: Categorize each issue as CRITICAL / SIGNIFICANT / MINOR
  - Recommend: Specific changes to address each CRITICAL and SIGNIFICANT issue
- Ask it to end with a structured list categorized as CRITICAL / SIGNIFICANT / MINOR

Write the agent's full output to `~/.claude/plans/lead-SESSION-reflection.md`.

**Phase 4: TWEAK**

Read `~/.claude/plans/lead-SESSION-plan.md` and `~/.claude/plans/lead-SESSION-reflection.md`.

If reflection.md contains no CRITICAL or SIGNIFICANT issues: copy plan.md to `~/.claude/plans/lead-SESSION-plan-final.md` unchanged and note "No blocking issues found — plan adopted as-is."

Otherwise, spawn a Task with `subagent_type: "follower"`. The prompt must:
- Include the original plan and the full reflection findings
- Ask it to: assess which issues are valid vs overstated, produce a complete revised plan (not a diff), flag any issues that couldn't be fully resolved

Write the agent's full output to `~/.claude/plans/lead-SESSION-plan-final.md`.

**Final Step: Write Review Summary**

Write `~/.claude/plans/lead-SESSION-review-summary.md` with this structure:

```
DISCOVERY
─────────
[3-5 bullets: key findings, constraints, relevant existing patterns]

PLAN (final)
────────────
Approach: [one sentence]
Steps: [numbered list]
Dependencies: [list]

REFLECTION
──────────
Critical: [N] | Significant: [N] | Minor: [N]
[Key issues and how they were addressed. Any unresolved issues.]

ARTIFACTS
─────────
~/.claude/plans/lead-SESSION-discovery.md
~/.claude/plans/lead-SESSION-plan.md
~/.claude/plans/lead-SESSION-reflection.md
~/.claude/plans/lead-SESSION-plan-final.md
```

Then return. Your job is complete.

---

**[END PIPELINE FOLLOWER PROMPT]**

## Step 2: Review Gate (Phase 5)

After the pipeline follower returns:

1. Call `EnterPlanMode`
2. Read `~/.claude/plans/lead-SESSION-review-summary.md` and `~/.claude/plans/lead-SESSION-plan-final.md`
3. Write both (review summary first, then full plan) to the plan file provided by plan mode
4. Call `ExitPlanMode` — this presents the plan to the user for approval via the native plan UI

If the user modifies the plan: apply changes to `~/.claude/plans/lead-SESSION-plan-final.md`, rewrite the plan file, and call `ExitPlanMode` again.

If the user rejects: halt and print the artifact paths.

Once approved, proceed to Step 3.

## Step 3: Execute (Phase 6)

Spawn a Task with `subagent_type: "follower"`. The prompt must include:
- The full contents of `~/.claude/plans/lead-SESSION-plan-final.md`
- The task description
- Instructions to:
  - Decompose the plan into parallel workstreams
  - Use TaskCreate/TaskUpdate to maintain a master todo list tracking all workstreams
  - Spawn each workstream as a sub-Task with `subagent_type: "follower"` or `"explore"` as appropriate
  - Escalate only genuine blockers (missing credentials, ambiguous requirements, architectural decisions)
  - Report consolidated status as workstreams complete

Summarize what was done and any remaining manual steps when execution finishes.
