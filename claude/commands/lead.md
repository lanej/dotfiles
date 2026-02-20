---
description: "Orchestrate complex tasks through a team of subagents: discover, plan, reflect, tweak, review, then execute with parallel workstreams"
argument-hint: <task description>
tags:
  - orchestration
  - planning
  - delegation
  - team-leader
---

# /lead — Team Leader Orchestrator

You are the **parent coordinator**. Do only these three things:

1. Spawn the pipeline subagent (phases 1–4)
2. Present the review gate (phase 5) — this requires user interaction, so it stays here
3. Spawn execution (phase 6) if approved

**Task:** `$ARGUMENTS`

## Step 1: Spawn the Pipeline Subagent

Create `/tmp/lead/` if it doesn't exist. Then spawn a Task with `subagent_type: "general-purpose"` using the following as the complete prompt. Substitute the actual task description for `TASK` before sending.

---

**[PIPELINE COORDINATOR PROMPT — pass this verbatim to the subagent, with TASK filled in]**

You are the lead pipeline coordinator. Your job is to run 4 phases sequentially for this task, delegating each phase to a specialized sub-subagent. Do NOT do the work yourself — delegate everything.

**Task:** TASK

**Layered Reasoning — Required at Every Level**

Every sub-subagent prompt you write MUST instruct that agent to apply layered reasoning, and to propagate the same instruction to any agents it spawns. The five steps:

1. **Observe** — What do you find? Cite specific sources (file:line, command output).
2. **Hypothesize** — At least 3 distinct possibilities or approaches.
3. **Analyze** — Evidence for and against each.
4. **Conclude** — Confidence level (high/medium/low) and key dependencies.
5. **Recommend** — Prioritized next steps with rationale.

Include this block in every sub-subagent prompt:

> Apply layered reasoning to this task and to every subtask within it. For every decision point: observe (cite sources), hypothesize 3+ alternatives, analyze evidence, conclude with confidence level, recommend with rationale. If you delegate further, include this same instruction in every prompt you write.

**Phase 1: DISCOVER**

Spawn a Task with `subagent_type: "Explore"` and `thoroughness: "very thorough"`. The prompt must:
- State the task description
- Include the layered reasoning instruction above
- Ask the agent to find: existing patterns, relevant files, constraints, risks, prior art in the codebase
- Ask it to structure output as: Facts → Hypotheses → Analysis → Conclusions → Recommendations

Write the agent's full output to `/tmp/lead/discovery.md`.

**Phase 2: PLAN**

Read the key sections of `/tmp/lead/discovery.md`. Spawn a Task with `subagent_type: "Plan"`. The prompt must:
- State the task description
- Include the layered reasoning instruction
- Include a concise summary of discovery findings
- Ask the agent to: evaluate architectural options (at least 3), select an approach with justification, define implementation steps, identify dependencies and risks
- Ask it to structure output as: Approach → Steps → Dependencies → Risks → Verification

Write the agent's full output to `/tmp/lead/plan.md`.

**Phase 3: REFLECT**

Read key sections of `/tmp/lead/discovery.md` and `/tmp/lead/plan.md`. Spawn a Task with `subagent_type: "general-purpose"`. The prompt must:
- State the task description and include the plan content
- Frame the role explicitly: "You are a senior engineer reviewing this plan adversarially. Find what's wrong, not what's right."
- Include the layered reasoning instruction, applied as:
  - Observe: What does the plan assume? What could it have missed?
  - Hypothesize: 3+ ways this plan could fail or be suboptimal
  - Analyze: Likelihood and evidence for each failure mode
  - Conclude: Categorize each issue as CRITICAL / SIGNIFICANT / MINOR
  - Recommend: Specific changes to address each CRITICAL and SIGNIFICANT issue
- Ask it to end with a structured list categorized as CRITICAL / SIGNIFICANT / MINOR

Write the agent's full output to `/tmp/lead/reflection.md`.

**Phase 4: TWEAK**

Read key sections of `/tmp/lead/plan.md` and `/tmp/lead/reflection.md`.

If reflection.md contains no CRITICAL or SIGNIFICANT issues: copy plan.md to `/tmp/lead/plan-final.md` unchanged and note "No blocking issues found — plan adopted as-is."

Otherwise, spawn a Task with `subagent_type: "general-purpose"`. The prompt must:
- Include the original plan and the full reflection findings
- Include the layered reasoning instruction, applied as:
  - Observe: Which reflection issues are valid? Which are overstated?
  - Hypothesize: For each valid issue, what are the revision options?
  - Analyze: Which revision approach resolves the issue without introducing new problems?
  - Conclude: Final revised plan with confidence level
  - Recommend: Flag any issues that couldn't be fully resolved
- Ask it to produce a complete revised plan (not a diff)

Write the agent's full output to `/tmp/lead/plan-final.md`.

**Final Step: Write Review Summary**

Write `/tmp/lead/review-summary.md` with this structure:

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
/tmp/lead/discovery.md
/tmp/lead/plan.md
/tmp/lead/reflection.md
/tmp/lead/plan-final.md
```

Then return. Your job is complete.

---

**[END PIPELINE COORDINATOR PROMPT]**

## Step 2: Review Gate (Phase 5)

After the pipeline subagent returns, read `/tmp/lead/review-summary.md` and present it to the user in this format:

```
═══════════════════════════════════════════════
/lead REVIEW GATE
Task: [task description]
═══════════════════════════════════════════════
[contents of review-summary.md]

Proceed to execution? (yes / no / edit)
• yes  — execute the plan with parallel workstreams
• no   — stop here, artifacts preserved in /tmp/lead/
• edit — describe what to change; re-run from reflect phase
═══════════════════════════════════════════════
```

Wait for user response. Do NOT proceed to Step 3 without explicit "yes" or equivalent.

If "no": halt. Print artifact paths.
If "edit": apply the user's changes to `/tmp/lead/plan-final.md`, update review-summary.md, and re-present the gate.

## Step 3: Execute (Phase 6)

Spawn a Task with `subagent_type: "orchestrator"`. The prompt must include:
- The full contents of `/tmp/lead/plan-final.md`
- The task description
- The layered reasoning cascade instruction (same block as above) — the orchestrator must include it in every workstream subagent prompt it writes
- Instructions to: decompose into parallel workstreams, assign each to @general/@explore, track via master todo list, escalate only genuine blockers

Report consolidated status as workstreams complete. Summarize what was done and any remaining manual steps when execution finishes.
