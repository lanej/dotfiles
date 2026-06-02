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
8. **Verification** — Is there a reliable way to determine whether the outcome is a true positive?
9. **Constraints** — Are time, team, resources, and compliance limits surfaced?
10. **Stakeholders** — Are beneficiaries, affected parties, and decision-makers named?
11. **Risk** — Is the riskiest assumption identified? What would invalidate this?
12. **Execution Readiness** — Are inputs, outputs, authority boundaries, and escalation conditions clear?

### Engineering (add when task is engineering)

13. **Modularity** — Does this decompose into independent parts with clean interfaces?
14. **Separation** — Is policy (what) separated from mechanism (how)?
15. **Robustness** — Are failure modes named? Partial failure has a defined path.
16. **Repair** — Does it fail fast and noisily? Recovery paths are explicit.
17. **Least Surprise** — Does behavior match caller expectations? Deviations documented.
18. **Regression Protection** — What prevents this task from silently failing again later?

### Research/Analysis (add when task is research or analysis)

13. **Falsifiability** — What evidence would prove the hypothesis wrong?
14. **Reproducibility** — Can another person reach the same conclusion from the same inputs?
15. **Bias** — What sampling, selection, or confirmation biases are present?
16. **Causation** — Is correlation being conflated with causation anywhere?

### Writing (add when task is writing)

13. **Audience** — Is the reader explicitly defined? Assumed knowledge is stated.
14. **Argument** — Is there a single clear thesis? Does every section serve it?
15. **Evidence** — Are claims backed by sources or data, not assertion?
16. **Action** — Is the desired reader action or decision explicit?

## Session File Location

Files live in `.socrates/` within the current working directory. Each session lives in a timestamped directory: `.socrates/YYYYMMDD-HHMMSS/`. There is no pointer file — on continuation, the most recent session is found by sorting the timestamped directories. Multiple concurrent sessions in the same project are supported. Timestamped sessions are preserved — historical reasoning, critique evolution, and validation history matter.

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
4. Set status to `Interrogating`.
6. Classify task type.
7. **Research** — before writing or asking anything, investigate the problem space. Read relevant files, grep for related code or config, check what already exists. The goal is to answer as many potential questions as possible from evidence before involving the user. For each candidate question, classify it:
   - **Self-answerable** (high confidence from evidence): answer it; record as **Assumed** with source citation. Do not ask.
   - **Probable** (medium confidence): answer it tentatively; mark as **Assumed**, flag it as fragile, and surface it to the user as a confirm-or-correct item rather than an open question.
   - **User-only** (requires intent, priority, or knowledge only the user holds): ask.
8. Pre-fill every section inferable from the title, domain, and research findings. Leave `_[open]_` only where genuine ambiguity remains after research. Cite evidence or mark claims as **Assumed**.
9. Score commandments using the alignment states: **stable** / **fragile** / **ambiguous** / **contradictory** / **open**.
10. Record the current interpretation of the task in one paragraph.
11. Use the `AskUserQuestion` tool to ask only user-only questions (those research couldn't resolve). For probable-answer questions being surfaced for confirmation, set the best-guess answer as the first (Recommended) option. Aim for 1–3 questions total — fewer if research was thorough. Use `multiSelect: true` only when multiple things can genuinely co-apply. Challenge, do not confirm.

### Continuation (no `$ARGUMENTS`)

1. Find all session directories: `find .socrates -maxdepth 1 -mindepth 1 -type d | sort -r` (newest first).
2. If none: tell the user no sessions exist and suggest `/socrates "Task Title"` to start one. Stop.
3. If exactly one: use it.
4. If multiple: use `AskUserQuestion` to let the user pick. For each session, read the title from the first line of its `spec.md` (label) and derive the timestamp from the directory name (description). Present in reverse-chronological order.
5. Load `SESSION_DIR/spec.md`.
3. If `critique.md` exists, enter `Reconciling` — adjudicate findings, revise spec, classify unresolved disagreements.
4. **Research** any remaining open questions before asking the user. Apply the same classification: self-answerable → answer and cite; probable → surface as confirm-or-correct with a recommended option; user-only → ask.
5. Print a one-line alignment summary per commandment (name + state only).
6. Restate the current interpretation before asking more questions when material ambiguity remains.
7. Prefer closing existing open questions over opening new ones.
8. Use the `AskUserQuestion` tool for user-only and probable-answer questions only. Frame 2–4 options per question; pre-populate best guesses as the Recommended option. "Other" is always available.
8. Update the session file: incorporate answers, resolve closed questions, add new ones.

### Alignment States

- **Stable** — likely understood correctly and backed by explicit spec content.
- **Fragile** — appears understood but depends on assumptions or missing context.
- **Ambiguous** — multiple plausible interpretations remain.
- **Contradictory** — goals, constraints, requirements, or success criteria conflict.
- **Open** — not yet addressed.

Do not mark a commandment **stable** unless the session file contains explicit content supporting it. A fragile item is not a blocker by default, but it must be named so the executor knows where interpretation risk remains.

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

**Research before asking**: Every potential question must be classified before it reaches the user. If it can be answered from the codebase, docs, memory, or domain knowledge — answer it. Only ask what genuinely requires user intent or context that can't be observed. A question asked when the answer was findable is a waste of the user's time and signals weak preparation.

**Question framing with `AskUserQuestion`**: Each question must have 2–4 options that represent the most distinct, plausible positions — not exhaustive, not false choices. A good option set forces the user to pick a side; a bad one presents overlapping or obvious alternatives. For probable-answer questions, set the best guess as the first (Recommended) option so the user can confirm with one click. Use `multiSelect` for constraint enumeration or capability checklists, not for interpretive questions.

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
- Ask "how would this fail silently?" to identify observability gaps.
- Challenge vague answers — sharpen them or classify them as ambiguous or fragile.
- Prefer one question that resolves multiple ambiguities.
- Prefer high-leverage clarification over exhaustive questioning.

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

Layer 7 — Execution Readiness
  [Inputs, outputs, authority boundaries, dependencies, and escalation conditions.]
```

If any layer does not hold under scrutiny, return to interrogation for that layer before proceeding.

### Specification Freeze

When:
- commandment states are stable or explicitly accepted as fragile
- validation semantics exist
- ambiguity is bounded
- execution readiness is explicit

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

### Execution Recommendation

After the dependency graph, recommend an execution strategy:

- **3+ independent tracks**: recommend `/lead` for orchestrated parallel execution.
- **Mostly sequential**: recommend working through tasks directly.
- **Mixed**: identify which phases benefit from `/lead` and which should be sequential.

Exit plan mode with `ExitPlanMode` for user approval.

## Spec Scaffold (`spec.md`)

```markdown
# [Title]

Status: Interrogating
Specification Version: v1
Frozen: false
Type: [Engineering | Research/Analysis | Writing | General]

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
- `/lead` → orchestrated parallel execution
- `/verify` → validation and regression verification

Do not suggest these at the end of Phase 2 or Phase 3. They are available to the user on demand.

## Usage

```
/socrates "Unified rate card API for carrier negotiation"   # init: creates .socrates/TIMESTAMP/spec.md
/socrates                                                   # continue: resumes most recent session
/socrates                                                   # continue until validated and planned
```
