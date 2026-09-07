---
description: "Interrogate a task through Socratic dialogue to produce a validated execution-ready specification, then enter plan mode"
argument-hint: ["Task Title" (init) or empty (continue)]
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
  - Bash(date:*)
  - Bash(mkdir:*)
  - Bash(grep:*)
  - Bash(find:*)
  - Bash(printenv:*)
  - Bash(sort:*)
tags:
  - specification
  - planning
  - socratic
---

# /socrates — Socratic Interrogation to Execution-Ready Plan

Three phases: **Interrogate** → **Validate** → **Plan**.

Purpose: convert ambiguous task intent into an execution-ready specification. The Socratic dialogue is the means, not the end. Interrogate until the problem, success criteria, validation strategy, and necessary context are sufficiently clear that an agent can execute the task without optimizing for the wrong outcome.

Optimize for semantic alignment:
- Avoid **false positives**: apparent clarity that hides a misunderstood, invalid, or under-specified task.
- Avoid **false negatives**: missed requirements, constraints, risks, or context that should have shaped execution.
- Strive for **true positives**: the task is understood correctly, bounded explicitly, validated against its intended outcome, and ready for successful execution.

Build a layered reasoning chain where each conclusion is grounded by the one below it. Enter plan mode once the chain holds.

## Lifecycle

```text
Interrogating → Critiquing → Reconciling → Validated → Planned → Executing → Verified
```

## Commandments

Quality gates applied to the current specification on each pass. Not a script — a checklist. Use judgment: infer what is obvious, interrogate what is genuinely ambiguous or risky.

**On initialization, classify the task type from the title:**
- **Engineering** — APIs, systems, infrastructure, data pipelines, code, tooling
- **Research/Analysis** — competitive analysis, investigations, data studies, experiments
- **Writing** — docs, memos, proposals, strategy, communications
- **General** — anything that doesn't clearly fit the above

Apply the universal commandments to all task types. Add the domain-specific set on top.

### Universal (all tasks)

1. **Problem First** — Is the problem defined before any solution is mentioned?
2. **Interpretation** — Is the current interpretation stated plainly enough that the user can reject it?
3. **Clarity** — Is the goal unambiguous? Two people must read it identically.
4. **Scope** — Is out-of-scope explicitly named? Silence implies inclusion.
5. **Context** — Is the necessary background, environment, history, and domain context available?
6. **Parsimony** — Minimum viable scope. Every element must justify its existence.
7. **Success** — Is "done" measurable and verifiable?
8. **Verification** — Is there a reliable way to determine whether the outcome is a true positive — both at completion (a validation contract) and *while work is in progress* (a fast, cheap signal on a defined cadence, or a deliberately constructed fallback when no fast signal exists)?
9. **Constraints** — Are time, team, resources, and compliance limits surfaced?
10. **Stakeholders** — Are beneficiaries, affected parties, and decision-makers named?
11. **Risk** — Is the riskiest assumption identified? What would invalidate this?
12. **Execution Readiness** — Are inputs, outputs, authority boundaries, and escalation conditions clear?
13. **Harmony** — Does this specification avoid contradicting itself or creating inconsistency elsewhere? Unlike every other commandment, Harmony is scored on *every* pass, not only when touched (see Commandment Scoring).

### Engineering (add when task is engineering)

14. **Modularity** — Does this decompose into independent parts with clean interfaces?
15. **Separation** — Is policy (what) separated from mechanism (how)?
16. **Robustness** — Are failure modes named? Partial failure has a defined path.
17. **Repair** — Does it fail fast and noisily? Recovery paths are explicit.
18. **Least Surprise** — Does behavior match caller expectations? Deviations documented.
19. **Regression Protection** — What prevents this task from silently failing again later?

### Research/Analysis (add when task is research or analysis)

14. **Falsifiability** — What evidence would prove the hypothesis wrong?
15. **Reproducibility** — Can another person reach the same conclusion from the same inputs?
16. **Bias** — What sampling, selection, or confirmation biases are present?
17. **Causation** — Is correlation being conflated with causation anywhere?

### Writing (add when task is writing)

14. **Audience** — Is the reader explicitly defined? Assumed knowledge is stated.
15. **Argument** — Is there a single clear thesis? Does every section serve it?
16. **Evidence** — Are claims backed by sources or data, not assertion?
17. **Action** — Is the desired reader action or decision explicit?

## Session File Location

Files live in `.socrates/YYYYMMDD-HHMMSS/` within the current working directory (one directory per session). Each Claude session binds to its own session directory via a pointer file `.socrates/.current-<CLAUDE_CODE_SESSION_ID>` (content: `TIMESTAMP:PID`), so concurrent sessions in the same repo don't collide. Read `$CLAUDE_CODE_SESSION_ID`/`$CLAUDE_PID` via `printenv` — never `$$`, which inside a Bash tool call is the subshell's PID, not Claude's. Write the pointer on Initialization and refresh it on every Continuation. If a session's own pointer is missing or its target directory has been removed, Continuation falls back to the picker (below) and claims whatever session it resolves. Timestamped sessions and their pointers are never deleted, even once stale — historical reasoning, critique evolution, and validation history matter.

Session artifacts:
- `spec.md` — authoritative specification
- `critique.md` — critique findings (if `/critique` was run)
- `verification.md` — verification results (if `/verify` was run)
- `plan.md` — downstream execution plan

## Phase 1 — Interrogation

### Plan Mode

This command manages its own phased execution. If plan mode is active at the start of Phase 1 or Phase 2, exit it immediately with `ExitPlanMode` before proceeding — plan mode is only entered intentionally at Phase 3. Don't let plan mode block session file writes or interrogation.

### Research & Question Classification

Before forming any question, research: relevant source files (Read, Glob, grep), existing configs/scripts, memory and prior session context, domain conventions. The point is to arm the question, not to gatekeep it — skip a question only when research settles a mechanical, non-interpretive fact outright; never skip one because research produced a plausible guess that touches goals, tradeoffs, risk, or scope. Classify each candidate question:

- **Self-answerable** (mechanical facts with no bearing on intent — language, file layout, existing syntax, established conventions): answer silently; record as **Assumed** with a source citation.
- **Probable** (a real finding exists, but it touches goals, tradeoffs, risk, or scope): open the question with the finding — state what you found, then ask whether it holds and why/why not. Never silently fold it into the spec as Assumed, and never reduce it to a one-click confirmation.
- **User-only** (unresolvable from evidence — requires intent, priorities, or institutional knowledge only the user holds): ask, and follow through per the Dialogue Loop — don't accept a vague, unexamined, or contradictory first answer at face value.

### Question Framing

Default to a plain, open-ended prose question — Socratic dialogue is not a multiple-choice form. Reach for `AskUserQuestion` only for a small, genuinely enumerable set of known options where forcing a choice sharpens the answer: 2–4 distinct, plausible positions, not exhaustive and not false choices. For a probable-answer question with a research-backed lean, set that guess as the first (Recommended) option, but still explain the finding, not just present it as a checkbox. Use `multiSelect` for constraint enumeration or capability checklists, never for interpretive questions.

### Initialization (`$ARGUMENTS` is a task title)

1. Generate a timestamp (`date +%Y%m%d-%H%M%S`) and create `.socrates/TIMESTAMP/`.
2. Create `.socrates/TIMESTAMP/spec.md` with the title and scaffold below.
3. Write `.socrates/.current-$CLAUDE_CODE_SESSION_ID` containing `TIMESTAMP:PID` (via `printenv`).
4. Set status to `Interrogating`, `Current Pass: 1`, and classify task type.
5. Research and classify candidate questions (see Research & Question Classification, above).
6. Pre-fill every section inferable from the title, domain, and research findings. Leave `_[open]_` only where genuine ambiguity remains. Cite evidence or mark claims **Assumed**.
7. Score commandments using the alignment states: **stable** / **fragile** / **ambiguous** / **contradictory** / **open**. For each commandment touched this pass, append a Pass 1 row to spec.md's `## Commandment Scores` table (see Commandment Scoring). Harmony always gets a Pass 1 row.
8. Record the current interpretation of the task in one paragraph.
9. Begin the Dialogue Loop (below) on the highest-leverage open commandment first. No target question count: continue, topic by topic, until the commandments relevant to this task are stable or explicitly accepted as fragile — a single well-researched question that cleanly resolves a topic is success, not a shortfall.

### Continuation (no `$ARGUMENTS`)

**Fast path**: if this session already has its own pointer, resolve directly and run every step below in order — the fast path only replaces the discovery/picker steps (2–5), never anything after.

1. `printenv CLAUDE_CODE_SESSION_ID`. If `.socrates/.current-$CLAUDE_CODE_SESSION_ID` exists and its target directory still exists (`find .socrates/<TIMESTAMP> -maxdepth 0 -type d`), resolve SESSION_DIR from the pointer and skip to step 6. Otherwise continue to step 2.
2. Find all session directories: `find .socrates -maxdepth 1 -mindepth 1 -type d | sort -r` (newest first).
3. If none: tell the user no sessions exist and suggest `/socrates "Task Title"`. Stop.
4. If exactly one: use it as SESSION_DIR.
5. If multiple: use `AskUserQuestion` to let the user pick. For each candidate, show the title (first line of its `spec.md`) and the timestamp from the directory name; annotate "active in another session right now" if another `.socrates/.current-*` pointer targets it and `find /tmp/cc-socks -maxdepth 1 -name '<that pointer's PID>.sock'` returns output. Present newest first.
6. Load `SESSION_DIR/spec.md`. Refresh `.socrates/.current-$CLAUDE_CODE_SESSION_ID` to `TIMESTAMP:PID` for SESSION_DIR.
7. Increment `Current Pass` by 1, regardless of whether anything gets a Commandment Scores row this pass.
8. If `critique.md` exists, enter `Reconciling` — adjudicate findings, revise spec, classify unresolved disagreements.
9. Research any remaining open questions and classify them (see Research & Question Classification) before resuming the dialogue.
10. Print a one-line alignment summary per commandment touched this pass (name, state, score). Harmony always gets a new row.
11. Restate the current interpretation before asking more questions if material ambiguity remains.
12. Prefer closing existing open questions over opening new ones.
13. Resume the Dialogue Loop on the most valuable open commandment. No fixed question count — continue until remaining open commandments are stable or explicitly accepted as fragile.
14. Update the session file: incorporate answers, resolve closed questions, add new ones.

### Alignment States

- **Stable** — likely understood correctly and backed by explicit spec content.
- **Fragile** — appears understood but depends on assumptions or missing context.
- **Ambiguous** — multiple plausible interpretations remain.
- **Contradictory** — goals, constraints, requirements, or success criteria conflict.
- **Open** — not yet addressed.

Don't mark a commandment **stable** unless the session file contains explicit content supporting it. A fragile item isn't a blocker by default, but it must be named so the executor knows where interpretation risk remains.

### Commandment Scoring

Every commandment touched in a pass gets an appended row (never overwritten) in spec.md's `## Commandment Scores` table (see Spec Scaffold):

- **Score** — confidence percentage (0–100%) in the current alignment-state assessment.
- **Why** — the causal/historical reason the underlying requirement, constraint, or behavior is the way it is, sourced from research.
- **Why not 100%** — what's driving the confidence gap in the score itself.
- **Escalated** — Yes/No: was a sub-70% score surfaced to the user as a dialogue question this pass?
- **Resolution** — if Escalated is Yes, how it was resolved (or a pointer to where it's recorded elsewhere).

**Harmony always runs** — scored on every pass whether or not it came up in discussion, because consistency can break silently in parts of the spec nobody is actively discussing.

**Deferral rule.** Any commandment scoring below 70% must be surfaced as a dialogue question — framed as sharpening understanding, not just closing a spec gap — never silently recorded as Assumed. Record `Escalated: Yes` and the `Resolution` once answered.

**Pass counter.** `Current Pass` is set to 1 on Initialization and incremented on every Continuation, regardless of whether anything gets a row that pass — this makes Harmony's cadence auditable later (verification checks that every integer from 1 to `Current Pass` has a Harmony row).

A specification may not transition to `Validated`/`Frozen: true` while any row has `Score < 70%` and `Escalated: No` (see Specification Freeze).

### Contradiction Detection

Actively identify conflicting goals, conflicting constraints, requirements that invalidate each other, success criteria that undermine requirements, and validation semantics that can be gamed. Don't normalize contradictions into the specification — resolve, bound, or classify them explicitly.

### Interpretation Check

On each pass, maintain:

```markdown
## Current Interpretation

[The task as currently understood, stated in executable terms.]

## Misclassification Risks

### Potential False Positives
- [What might appear clear but be wrong?]

### Potential False Negatives
- [What important requirement, constraint, or context might still be missing?]
```

Goal: eliminate the most dangerous ways the agent could execute the wrong task — not to ask endless questions.

### Assumptions

State assumptions explicitly rather than embedding them silently:

```markdown
**Assumed**: [X], because [reason]. Correct if wrong.
```

Assumptions (inference, domain knowledge, pattern-matching) are distinct from findings (stated user input or observable facts). Both must be visible and challengeable — an unstated assumption is a latent false positive.

### Source Citations

Cite sources inline for claims about external systems, domain behavior, tooling, standards, or prior decisions — documentation URLs, codebase references (`file:line`), or prior session/memory notes:

```markdown
[source text](URL or file:line reference)
```

Never assert domain facts as established without grounding. If no linkable source exists, label the claim **Assumed** instead.

### Dialogue Loop

Interrogation proceeds one open commandment at a time, in order of leverage:

1. Research the topic first (unconditional).
2. Ask **one** question, per Question Framing above.
3. If research surfaced a finding, lead with it and ask whether it holds, per the "Probable" case in Research & Question Classification.
4. Judge the answer before moving on:
   - Vague or hedged → ask them to make it concrete.
   - Confident but unexamined → probe it ("what would prove that wrong?" / "what's broken this assumption before?").
   - Contradicts something already established → surface the contradiction and ask which one holds.
   - Clear and load-bearing → record it, close the topic, move to the next.
5. No fixed question budget. Continue until the commandments relevant to this task are stable or explicitly accepted as fragile — a follow-up is earned by the answer being vague, unexamined, or contradictory, not by a target exchange count.

This doesn't license over-interrogating trivial tasks — "use judgment, infer what is obvious" (Commandments, above) still applies, so a task with few genuinely open or risky commandments produces a short dialogue on its own.

Other prompts worth reaching for:
- Ask "why" to surface unstated assumptions.
- Ask "what happens when X fails" to probe robustness.
- Ask "what happens if we don't do this?" to expose necessity and timing assumptions — let the user name the consequence and timeline, don't embed one.
- Ask "who decides?" to surface ownership and escalation boundaries.
- Ask "what is explicitly excluded?" to sharpen scope.
- Ask "how would we know this worked?" to expose weak validation semantics.
- Ask "what could appear successful while actually being wrong?" to expose false positives.
- Ask "what would be missing from an apparently good result?" to expose false negatives.
- Ask "what must not break?" to surface regression boundaries.
- Ask "what tells you mid-flight that you're still on track, and what does that check cost?" to expose a missing Feedback Loop Design.
- Ask "how would this fail silently?" to identify observability gaps.
- Ask "why is this the way it is" before scoring a commandment — the rationale, not just the state, is the point.
- Challenge vague answers — sharpen them or classify them as ambiguous or fragile.
- Prefer one question that resolves multiple ambiguities, and the most consequential ambiguity first.

## Phase 2 — Validation and Layered Reasoning

Triggered when all applicable commandments are **stable** or explicitly accepted as **fragile**, and Open Questions is empty or contains only acknowledged non-blockers.

A specification is not execution-ready until success conditions exist, there's a defined method to verify them, there's a strategy to detect regressions or silent failure, scope/constraints/authority boundaries are explicit, and remaining ambiguities are classified as blocking, non-blocking, or intentional.

Synthesize the spec into an explicit reasoning chain, each layer derived from the one below it. Present this chain before entering plan mode so the grounding is visible and challengeable.

```
Layer 1 — Problem
  [One-sentence statement of what is broken or missing, and why it matters now.]

Layer 2 — Requirements
  [What must be true. Derived from Layer 1. Each prefixed with "shall".]
  Challenged by: [what would make these requirements wrong]

Layer 3 — Constraints
  [What limits the solution space. Bounds Layers 2 and 4.]

Layer 4 — Risks
  [Top assumptions whose failure would invalidate Layers 1–3.]

Layer 5 — Success
  [Measurable criteria that confirm Layer 1 is resolved within Layer 3.]
  False positive guard: [what would look successful but be wrong]
  False negative guard: [what missing work/context would make the result incomplete]

Layer 6 — Validation
  Acceptance tests: [how success will be verified]
  Regression checks: [what must continue working after completion]
  Failure signals: [what indicates incomplete or incorrect execution]
  Verification method: [automated | manual | observational | comparative | statistical]
  Feedback Loop Design: [signal, cost/cadence, fallback if no fast signal exists]

Layer 7 — Execution Readiness
  [Inputs, outputs, authority boundaries, dependencies, and escalation conditions.]
```

If any layer doesn't hold under scrutiny, return to interrogation for that layer before proceeding.

### Specification Freeze

When commandment states are stable or explicitly accepted as fragile, validation semantics exist, Feedback Loop Design is populated for at least the load-bearing requirements (not `_[open]_`), ambiguity is bounded, execution readiness is explicit, and no Commandment Scores row has `Score < 70%` and `Escalated: No`:

- set status to `Validated`, freeze the specification, assign a specification version:

```markdown
Status: Validated
Specification Version: v3
Frozen: true
```

A frozen specification may not be silently mutated by planners, executors, verifiers, or critics.

### Reopen Semantics

If critique exposes unresolved ambiguity, execution changes assumptions, or validation fails: reopen the specification, transition back to `Interrogating` or `Reconciling`, and don't destroy prior validation or critique artifacts.

## Phase 3 — Plan Mode

After presenting the layered reasoning chain, immediately enter plan mode with `EnterPlanMode` — don't pause, suggest downstream commands, or ask the user to invoke `/critique` first. Develop a concrete implementation plan grounded in the spec; every task must trace back to a requirement, every requirement back to the problem.

### Dependency Graph

Decompose the plan into a dependency graph. For each task, identify blocks and parallel-safe work:

```
[Task A] ──► [Task C] ──► [Task E]
[Task B] ──► [Task C]
[Task D] ──────────────► [Task E]   (parallel with A→C)
```

### Execution Recommendation

- **3+ independent tracks**: recommend invoking `Workflow` directly for orchestrated parallel execution.
- **Mostly sequential**: recommend working through tasks directly.
- **Mixed**: identify which phases benefit from a `Workflow` script and which should be sequential.

### Write the Plan

Write the dependency graph and execution recommendation to `.socrates/TIMESTAMP/plan.md` (same session directory as `spec.md`/`critique.md`) using the `Write` tool. Presenting the plan in conversation only does not satisfy this — it must exist on disk at this path.

### Plan Critique

Immediately after writing `plan.md`, before any other tool call, dispatch `Agent(model="opus")` to critique it — give it the `plan.md` path plus enough spec context (or a pointer to `spec.md`) to judge whether the dependency graph and execution recommendation are sound. Mandatory every pass through Phase 3, not conditional on suspecting a weak plan.

Exit plan mode with `ExitPlanMode` for user approval.

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

_[open]_

## Requirements

_[open]_

## Constraints

_[open]_

## Success Criteria

_[open]_

## Validation Contract

### Acceptance Tests

_[open]_

### Regression Checks

_[open]_

### Failure Signals

_[open]_

### Verification Methods

_[open]_

### Feedback Loop Design

_[open]_

### Known Blind Spots

_[open]_

## Inputs

_[open]_

## Outputs

_[open]_

## Out of Scope

_[open]_

## Authority Boundaries

### Executor May Decide

_[open]_

### Executor Must Escalate

_[open]_

### Executor Must Not Change

_[open]_

## Current Interpretation

_[open]_

## Misclassification Risks

### Potential False Positives

_[open]_

### Potential False Negatives

_[open]_

## Ambiguities

### Blocking

_[open]_

### Non-Blocking

_[open]_

### Intentional

_[open]_

## Risks

_[open]_

## Stakeholders

_[open]_
```

## Downstream Commands (optional, user-invoked)

After the plan is approved:
- `/critique` → adversarial specification review
- `Workflow` → orchestrated parallel execution (author a script directly)
- `/verify` → validation and regression verification

Do not suggest these at the end of Phase 2 or Phase 3. They are available to the user on demand.

## Usage

```
/socrates "Unified rate card API for carrier negotiation"   # init: creates .socrates/TIMESTAMP/spec.md
/socrates                                                   # continue: resumes most recent session
/socrates                                                   # continue until validated and planned
```
