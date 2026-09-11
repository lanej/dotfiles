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

Specifications move through explicit states:

```text
Interrogating
→ Critiquing
→ Reconciling
→ Validated
→ Planned
→ Executing
→ Verified
```

## Commandments

Quality gates applied to the current specification on each pass. These are not a script — they are a checklist. Use judgment: infer what is obvious, interrogate what is genuinely ambiguous or risky.

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
8. **Verification** — Is there a reliable way to determine whether the outcome is a true positive — both at completion (a validation contract) and *while work is in progress* (a fast, cheap signal invoked on a defined cadence, or a deliberately constructed fallback when no fast signal exists)? The in-progress signal must be the **cheapest** check that still localizes a fault to the task that caused it — not the broadest available check. Breadth belongs in the completion contract, which runs once.
9. **Constraints** — Are time, team, resources, and compliance limits surfaced?
10. **Stakeholders** — Are beneficiaries, affected parties, and decision-makers named?
11. **Risk** — Is the riskiest assumption identified? What would invalidate this?
12. **Execution Readiness** — Are inputs, outputs, authority boundaries, and escalation conditions clear?
13. **Harmony** — Does this specification avoid contradicting itself or creating inconsistency elsewhere? What would this change break somewhere else in the spec that nobody is currently discussing? Unlike every other commandment, Harmony is evaluated on every interrogation pass, not only when touched — see Commandment Scoring below.

### Engineering (add when task is engineering)

14. **Modularity** — Does this decompose into independent parts with clean interfaces?
15. **Separation** — Is policy (what) separated from mechanism (how)?
16. **Robustness** — Are failure modes named? Partial failure has a defined path.
17. **Repair** — Does it fail fast and noisily? Recovery paths are explicit.
18. **Least Surprise** — Does behavior match caller expectations? Deviations documented.
19. **Regression Protection** — What prevents this task from silently failing again later? This is a branch-level and CI-level concern — do not satisfy it by widening the in-progress signal in Commandment 8.

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

Files live in `.socrates/` within the current working directory. Each session lives in a timestamped directory: `.socrates/YYYYMMDD-HHMMSS/`. Each running Claude session is bound to its own session directory via a per-session pointer file, `.socrates/.current-<CLAUDE_CODE_SESSION_ID>` (content: `TIMESTAMP:PID`) — this replaces an earlier single global pointer, which broke when two Claude sessions worked in the same repo concurrently. `$CLAUDE_CODE_SESSION_ID` and `$CLAUDE_PID` are read via `printenv` (never `$$`, which inside a Bash tool call is the spawned subshell's PID, not the running Claude process's). The pointer is written on Initialization and refreshed on every Continuation. If a Claude session's own pointer doesn't exist yet (or its target directory has been removed), Continuation falls back to the picker below, then claims whichever session gets resolved. Timestamped sessions are preserved — historical reasoning, critique evolution, and validation history matter — and so are their pointer files, even once stale.

Session artifacts:
- `spec.md` — authoritative specification
- `critique.md` — critique findings (if `/critique` was run)
- `verification.md` — verification results (if `/verify` was run)
- `plan.md` — downstream execution plan

## Phase 1 — Interrogation

### Plan Mode

This command manages its own phased execution. If plan mode is active at the start of Phase 1 or Phase 2, exit it immediately using `ExitPlanMode` before proceeding — plan mode is only entered intentionally at Phase 3. Do not let plan mode block session file writes or interrogation.

### Initialization (`$ARGUMENTS` is a task title)

1. Generate a timestamp (use Bash: `date +%Y%m%d-%H%M%S`).
2. Create `.socrates/TIMESTAMP/` directory.
3. Create `.socrates/TIMESTAMP/spec.md` with the title and scaffold below.
4. `printenv CLAUDE_CODE_SESSION_ID` and `printenv CLAUDE_PID`; write `.socrates/.current-$CLAUDE_CODE_SESSION_ID` containing `TIMESTAMP:PID`.
5. Set status to `Interrogating` and `Current Pass: 1`.
6. Classify task type.
7. **Research** — before forming any question, investigate: relevant source files (Read, Glob, grep), existing configs and scripts, memory and prior session context, domain conventions and patterns. The point of this research isn't to avoid asking — it's to arm the question. A question backed by "here's what I found, and here's why it might matter" gives the user something real to decide against; that's what makes it informed rather than a blind ask. Classify each post-research question:
   - **Self-answerable** (mechanical, non-interpretive facts with no bearing on intent — language, file layout, existing syntax, established conventions): answer it silently; record as **Assumed** with source citation. Asking these wastes the user's time.
   - **Probable** (a real finding exists, but it touches goals, tradeoffs, risk, or scope): bring it into the dialogue as the opening move of a question — state the finding, then ask whether it holds and why/why not. Do not silently fold it into the spec as Assumed, and do not reduce it to a one-click confirmation; the user reasoning about your finding is the point, not just their approval of it.
   - **User-only** (genuinely unresolvable from evidence — requires intent, priorities, or institutional knowledge only the user holds): ask, and follow through per the Dialogue Loop below — don't accept the first answer at face value if it's vague, unexamined, or contradicts something already established.
8. Pre-fill every section inferable from the title, domain, and research findings. Leave `_[open]_` only where genuine ambiguity remains after research. Cite evidence or mark claims as **Assumed**.
9. Score commandments using the alignment states: **stable** / **fragile** / **ambiguous** / **contradictory** / **open**. For each commandment touched this pass, also append a Pass 1 row to spec.md's `## Commandment Scores` table — state, confidence score (0-100%), Why, Why not 100%, Escalated, Resolution (see Commandment Scoring below). Harmony always gets a Pass 1 row, whether or not it was otherwise discussed.
10. Record the current interpretation of the task in one paragraph.
11. Begin the Dialogue Loop (below) on the highest-leverage open commandment first. Default to a plain, open-ended prose question — reach for `AskUserQuestion` only when the answer space is a small, genuinely enumerable set of known options. There is no target question count: continue, topic by topic, until the commandments relevant to this task are stable or explicitly accepted as fragile. A single well-researched question that resolves a topic cleanly is success, not a shortfall — depth is earned by real ambiguity, not manufactured by a quota.

### Continuation (no `$ARGUMENTS`)

**Fast-path principle**: if this Claude session already has its own pointer, resolve directly and run every step that follows session-resolution in its normal, unmodified order — the fast path only ever replaces the discovery/picker steps (2-5 below), never anything after.

1. `printenv CLAUDE_CODE_SESSION_ID`. If `.socrates/.current-$CLAUDE_CODE_SESSION_ID` exists and `find .socrates/<its TIMESTAMP> -maxdepth 0 -type d` confirms that directory still exists, resolve SESSION_DIR directly from the pointer and skip to step 6. Otherwise (no pointer, or its target directory is gone — treat identically), continue to step 2.
2. Find all session directories: `find .socrates -maxdepth 1 -mindepth 1 -type d | sort -r` (newest first).
3. If none: tell the user no sessions exist and suggest `/socrates "Task Title"` to start one. Stop.
4. If exactly one: use it as SESSION_DIR.
5. If multiple: use `AskUserQuestion` to let the user pick SESSION_DIR. For each candidate, read the title from the first line of its `spec.md` (label) and derive the timestamp from the directory name (description); annotate a candidate "active in another session right now" if `find .socrates -maxdepth 1 -name '.current-*'` turns up another pointer, `Read`ing it shows it targets this candidate, and `find /tmp/cc-socks -maxdepth 1 -name '<that pointer's PID>.sock'` returns output. Present in reverse-chronological order.
6. Load `SESSION_DIR/spec.md`. `printenv CLAUDE_PID`; write `.socrates/.current-$CLAUDE_CODE_SESSION_ID` containing `TIMESTAMP:PID` for SESSION_DIR — refreshing the pointer whether it was resolved directly (step 1) or via the fallback (steps 2-5).
7. Increment `Current Pass` by 1, regardless of whether anything gets a Commandment Scores row this pass.
8. If `critique.md` exists, enter `Reconciling` — adjudicate findings, revise spec, classify unresolved disagreements.
9. **Research** any remaining open questions before resuming the dialogue. Apply the same classification: self-answerable → answer and cite; probable → bring the finding into the next question rather than silently assuming it; user-only → ask, with follow-through.
10. Print a one-line alignment summary per commandment touched this pass (name, state, and score — full rationale lives in the Commandment Scores table). Harmony always gets a new row this pass, whether or not it was otherwise discussed.
11. Restate the current interpretation before asking more questions when material ambiguity remains.
12. Prefer closing existing open questions over opening new ones.
13. Resume the Dialogue Loop (below) on the most valuable open commandment. Default to prose; reach for `AskUserQuestion` only for genuinely bounded option sets, pre-populating the best guess as Recommended. No fixed question count — continue until remaining open commandments are stable or explicitly accepted as fragile.
14. Update the session file: incorporate answers, resolve closed questions, add new ones.

### Alignment States

- **Stable** — likely understood correctly and backed by explicit spec content.
- **Fragile** — appears understood but depends on assumptions or missing context.
- **Ambiguous** — multiple plausible interpretations remain.
- **Contradictory** — goals, constraints, requirements, or success criteria conflict.
- **Open** — not yet addressed.

Do not mark a commandment **stable** unless the session file contains explicit content supporting it. A fragile item is not a blocker by default, but it must be named so the executor knows where interpretation risk remains.

### Commandment Scoring

In addition to its alignment state, every commandment touched in a pass gets a row in spec.md's `## Commandment Scores` table (see Spec Scaffold) — never overwrite a prior row, always append:

- **Score** — a confidence percentage (0-100%) in the current alignment-state assessment.
- **Why** — the causal/historical reason the underlying requirement, constraint, or existing behavior is the way it is. Sourced from research, not from uncertainty about the score.
- **Why not 100%** — what's driving the confidence gap in the score itself.
- **Escalated** — Yes/No: was a sub-70% score surfaced to the user as a dialogue question this pass?
- **Resolution** — if Escalated is Yes, a one-line note of how it was resolved, or a pointer to where the resolution is recorded elsewhere in the spec.

**Harmony always runs.** Unlike every other commandment — scored only when touched, preserving the open-ended dialogue-loop design — Harmony is evaluated and given a new row every single pass, whether or not it came up in discussion, because consistency can break silently in parts of the spec nobody is actively discussing.

**Deferral rule.** Any commandment (including Harmony) scoring below 70% must be surfaced to the user as a dialogue question — framed as sharpening the user's own thinking and the assistant's understanding, not just closing a spec gap — never silently recorded as Assumed. Record `Escalated: Yes` and the `Resolution` once answered.

**Pass counter.** `Current Pass` (see Spec Scaffold) is an independent counter: set to 1 on Initialization, incremented by 1 on every Continuation invocation, regardless of whether anything gets a row that pass. This is what makes Harmony's cadence auditable later — verification checks that every integer from 1 to `Current Pass` has a corresponding Harmony row.

A specification may not transition to `Validated`/`Frozen: true` while any row in the Commandment Scores table has `Score < 70%` and `Escalated: No` (see Specification Freeze below).

### Contradiction Detection

Actively identify:
- conflicting goals
- conflicting constraints
- requirements that invalidate each other
- success criteria that undermine requirements
- validation semantics that can be gamed

Do not normalize contradictions into the specification. Resolve them, bound them, or classify them explicitly.

### Interpretation Check

On each pass, maintain a short interpretation check:

```markdown
## Current Interpretation

[The task as currently understood, stated in executable terms.]

## Misclassification Risks

### Potential False Positives
- [What might appear clear but be wrong?]

### Potential False Negatives
- [What important requirement, constraint, or context might still be missing?]
```

Use this to validate semantic alignment. The goal is not to ask endless questions; the goal is to eliminate the most dangerous ways the agent could execute the wrong task.

### Assumptions

When pre-filling spec sections or making claims about the problem domain, state assumptions explicitly rather than silently embedding them. Format:

```markdown
**Assumed**: [X], because [reason]. Correct if wrong.
```

Assumptions are distinct from findings. Findings come from stated user input or observable facts. Assumptions come from inference, domain knowledge, or pattern-matching. Both must be visible and challengeable. An unstated assumption is a latent false positive.

### Source Citations

When making claims about external systems, domain behavior, tooling, standards, or prior decisions, cite the source inline using markdown links. Acceptable sources: documentation URLs, codebase references (`file:line`), or prior session/memory notes. Format:

```markdown
[source text](URL or file:line reference)
```

Do not assert domain facts as if they are established without grounding. If no linkable source exists, label the claim as an assumption using the **Assumed** format above.

### Interrogation Principles

**Research to arm the question, not to gatekeep it**: Research just as thoroughly as ever — check the codebase, configs, memory, and domain conventions before forming any question. But the point of that research is to make the question worth asking, not to earn the right to ask it. A question backed by a real finding ("I found X, which suggests Y") gives the user something concrete to decide against; that's what "informed" means here. Skip a question only when research settles a mechanical, non-interpretive fact outright — never skip one because research produced a plausible guess, if that guess touches goals, tradeoffs, risk, or scope.

### Dialogue Loop

Interrogation proceeds one open commandment at a time, in order of leverage:

1. Research the topic first — unconditional, not optional-if-thorough.
2. Ask **one** question. Default to a plain, open-ended prose question — Socratic dialogue is not a multiple-choice form. Reach for `AskUserQuestion` only when the answer space is a small, genuinely enumerable set of known options (see "Question framing with `AskUserQuestion`" below).
3. If research surfaced a relevant finding, lead with it: state what you found and why it might matter, then ask whether it holds, why/why not, or what's different this time. Don't silently fold a finding into the spec as Assumed when it touches anything the user should weigh in on.
4. Judge the answer before moving on:
   - Vague or hedged → ask them to make it concrete.
   - Confident but unexamined → probe it ("what would prove that wrong?" / "what's broken this assumption before?").
   - Contradicts something already established → surface the contradiction directly and ask which one holds.
   - Clear and load-bearing → record it, close the topic, move to the next.
5. No fixed question budget in either direction. Continue until the commandments relevant to this task are stable or explicitly accepted as fragile — that's the stop condition, not a round count. A well-researched question that resolves a topic in one exchange is a success; a follow-up is earned by the answer actually being vague, unexamined, or contradictory, not by a target exchange count.

This doesn't license over-interrogating trivial tasks — "use judgment, infer what is obvious" (Commandments, above) still applies, so a task with few genuinely open or risky commandments produces a short dialogue on its own. What changes is quality — research-backed, decision-ready questions — and removing the artificial ceiling that used to cut a topic off before it was actually resolved.

**Question framing with `AskUserQuestion`**: Reserve this tool for genuinely bounded questions — a small, enumerable set of known options where forcing a choice sharpens the answer. Each question must have 2–4 options that represent the most distinct, plausible positions — not exhaustive, not false choices. A good option set forces the user to pick a side; a bad one presents overlapping or obvious alternatives. For probable-answer questions carrying a research-backed lean, set the best guess as the first (Recommended) option — but the question still has to explain the finding behind it, not just present it as a checkbox. Use `multiSelect` for constraint enumeration or capability checklists, not for interpretive questions. For anything interpretive — open-ended by nature, no natural enumerable option set — ask in plain prose instead.

- One topic per question.
- Ask "why" to surface unstated assumptions.
- Ask "what happens when X fails" to probe robustness.
- Ask "what happens if we don't do this?" to expose necessity and timing assumptions — never embed a timeframe; let the user name the consequence and the timeline.
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
- Prefer one question that resolves multiple ambiguities.
- Prefer resolving the most consequential ambiguity first.

## Phase 2 — Validation and Layered Reasoning

Triggered when all applicable commandments are **stable** or explicitly accepted as **fragile**, and Open Questions is empty or contains only acknowledged non-blockers.

A specification is not execution-ready until:
- success conditions exist
- there is a defined method to verify them
- there is a strategy to detect regressions or silent failure
- scope, constraints, and authority boundaries are explicit
- remaining ambiguities are classified as blocking, non-blocking, or intentional

Synthesize the spec into an explicit reasoning chain. Each layer is derived from the one below it. Present this chain before entering plan mode so the grounding is visible and challengeable.

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
  Feedback Loop Design: [cheapest fault-localizing signal, its cost/cadence, fallback if no fast signal exists, and the escalation trigger that widens it]

Layer 7 — Execution Readiness
  [Inputs, outputs, authority boundaries, dependencies, and escalation conditions.]
```

If any layer does not hold under scrutiny, return to interrogation for that layer before proceeding.

### Specification Freeze

When:
- commandment states are stable or explicitly accepted as fragile
- validation semantics exist
- Feedback Loop Design is populated for at least the load-bearing requirements (not left `_[open]_`)
- ambiguity is bounded
- execution readiness is explicit
- no row in the Commandment Scores table has `Score < 70%` and `Escalated: No`

then:
- set status to `Validated`
- freeze the specification
- assign a specification version

```markdown
Status: Validated
Specification Version: v3
Frozen: true
```

A frozen specification may not be silently mutated by planners, executors, verifiers, or critics.

### Reopen Semantics

If critique exposes unresolved ambiguity, execution changes assumptions, or validation fails:
- reopen the specification
- transition back to `Interrogating` or `Reconciling`
- do not destroy prior validation or critique artifacts

## Phase 3 — Plan Mode

After presenting the layered reasoning chain, immediately enter plan mode using the `EnterPlanMode` tool — do not pause, do not suggest downstream commands, do not ask the user to invoke `/critique` or anything else. Proceed automatically. Develop a concrete implementation plan grounded in the spec. Every task must trace back to a requirement; every requirement must trace back to the problem.

### Dependency Graph

Decompose the plan into a dependency graph. For each task, identify blocks and parallel-safe work. Present the graph explicitly:

```
[Task A] ──► [Task C] ──► [Task E]
[Task B] ──► [Task C]
[Task D] ──────────────► [Task E]   (parallel with A→C)
```

### Per-Task Verification Budget

Each task in the plan carries:
- **Feedback signal** — the narrowest check that would catch a fault in that task's own deliverable (tier V1: changed-file/package tests, type-check on the diff, a targeted grep). Never the full suite; never a pointer to the final review.
- **Commit** — every task ends in its own commit. This, not suite breadth, is what preserves attribution when the branch-level gate later surfaces a fault.

The full suite, full lint/type-check, and the whole-branch review run **once**, after the last task — not between tasks. A *bounded* review of the diff since the last checkpoint does run at each wave boundary (V3a): review is the only thing that reliably detects the faults this codebase actually produces, so review cadence — not test breadth — is what keeps a fault from compounding across the plan. See the `methodology` skill's Verification Rigor Tiers and `CLAUDE.md`'s Proportional Verification, including the trip-wire that promotes remaining tasks to full-suite checks when evidence justifies it.

### Execution Recommendation

After the dependency graph, recommend an execution strategy:

- **3+ independent tracks**: recommend invoking `Workflow` directly for orchestrated parallel execution.
- **Mostly sequential**: recommend working through tasks directly.
- **Mixed**: identify which phases benefit from a `Workflow` script and which should be sequential.

### Write the Plan

Write the dependency graph and execution recommendation above to `.socrates/TIMESTAMP/plan.md` — the same session timestamp directory already used for `spec.md`/`critique.md` — as a real file, using the `Write` tool. This is not optional and not satisfied by presenting the plan in conversation only: the plan is not complete until it exists on disk at this path.

### Plan Critique

After writing `plan.md`, dispatch `Agent(model="opus")` to critique the plan file when the plan is complex or high-stakes — a dependency graph with parallel waves, irreversible or shared-state changes, or a spec with fragile load-bearing commandments. Give the sub-agent the `plan.md` path plus enough spec context (or a pointer to `spec.md`) to judge whether the dependency graph and execution recommendation are sound. Skip it for small, sequential, low-risk plans; the critique is a real dispatch with real latency and it does not earn its cost on every pass. This matches `CLAUDE.md`'s "Plan Mode" rule, which governs — an earlier version of this file made the dispatch mandatory on every pass and contradicted it. When dispatched, the critique must be scored independently by the critique agent, not self-assessed by the plan's author.

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
