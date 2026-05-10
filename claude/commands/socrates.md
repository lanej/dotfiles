---
description: "Interrogate a task through Socratic dialogue to produce an execution-ready specification, then enter plan mode"
argument-hint: ["Task Title" (init) or empty (continue)]
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(date:*)
  - Bash(mkdir:*)
tags:
  - specification
  - planning
  - socratic
---

# /socrates — Socratic Interrogation to Execution-Ready Plan

Three phases: **Interrogate** → **Validate** → **Plan**.

Purpose: convert ambiguous task intent into an execution-ready specification. The Socratic dialogue is the means, not the end. Interrogate until the problem, success criteria, and necessary context are sufficiently clear that an agent can execute the task without optimizing for the wrong outcome.

Optimize for semantic alignment:
- Avoid **false positives**: apparent clarity that hides a misunderstood, invalid, or under-specified task.
- Avoid **false negatives**: missed requirements, constraints, risks, or context that should have shaped execution.
- Strive for **true positives**: the task is understood correctly, bounded explicitly, and ready for successful execution.

Build a layered reasoning chain where each conclusion is grounded by the one below it. Enter plan mode once the chain holds.

## Commandments

Quality gates applied to the current state of the session file on each pass.
Use judgment — infer what's obvious, interrogate what's genuinely ambiguous or risky.
These are not a script; they are a checklist.

**On initialization, classify the task type from the title:**
- **Engineering** — APIs, systems, infrastructure, data pipelines, code, tooling
- **Research/Analysis** — competitive analysis, investigations, data studies, experiments
- **Writing** — docs, memos, proposals, strategy, communications
- **General** — anything that doesn't clearly fit the above

Apply the universal commandments to all task types. Add the domain-specific set on top.

**Universal (all tasks):**
1. **Problem First** — Is the problem defined before any solution is mentioned?
2. **Interpretation** — Is the current interpretation stated plainly enough that the user can reject it?
3. **Clarity** — Is the goal unambiguous? Two people must read it identically.
4. **Scope** — Is out-of-scope explicitly named? Silence implies inclusion.
5. **Context** — Is the necessary background, environment, history, and domain context available?
6. **Parsimony** — Minimum viable scope. Every element must justify its existence.
7. **Success** — Is "done" measurable and verifiable?
8. **Constraints** — Are time, team, resources, and compliance limits surfaced?
9. **Stakeholders** — Are beneficiaries, affected parties, and decision-makers named?
10. **Risk** — Is the riskiest assumption identified? What would invalidate this?
11. **Execution Readiness** — Are inputs, outputs, authority boundaries, and escalation conditions clear?

**Engineering (add when task is engineering):**
12. **Modularity** — Does this decompose into independent parts with clean interfaces?
13. **Separation** — Is policy (what) separated from mechanism (how)?
14. **Robustness** — Are failure modes named? Partial failure has a defined path.
15. **Repair** — Does it fail fast and noisily? Recovery paths are explicit.
16. **Least Surprise** — Does behavior match caller expectations? Deviations documented.

**Research/Analysis (add when task is research or analysis):**
12. **Falsifiability** — What evidence would prove the hypothesis wrong?
13. **Reproducibility** — Can another person reach the same conclusion from the same inputs?
14. **Bias** — What sampling, selection, or confirmation biases are present?
15. **Causation** — Is correlation being conflated with causation anywhere?

**Writing (add when task is writing):**
12. **Audience** — Is the reader explicitly defined? Assumed knowledge is stated.
13. **Argument** — Is there a single clear thesis? Does every section serve it?
14. **Evidence** — Are claims backed by sources or data, not assertion?
15. **Action** — Is the desired reader action or decision explicit?

## Phase 1 — Interrogation

### Plan Mode

This command manages its own phased execution. If plan mode is active at the start of
Phase 1 or Phase 2, exit it immediately using `ExitPlanMode` before proceeding — plan
mode is only entered intentionally at Phase 3. Do not let plan mode block session file
writes or interrogation.

### Session File Location

Files live in `.socrates/` within the current working directory. Named by timestamp at
creation: `YYYYMMDD-HHMMSS.md`. A pointer file at `.socrates/.current` contains the
filename of the active session. One active session per project — starting a new one
replaces the pointer. Add `.socrates/` to `.gitignore` if not already present.

### Initialization (`$ARGUMENTS` is a task title)

1. Generate a timestamp (use Bash: `date +%Y%m%d-%H%M%S`).
2. Create `.socrates/TIMESTAMP.md` with the title and scaffold below.
3. Write the filename (e.g. `20260414-101638.md`) to `.socrates/.current`.
4. Pre-fill every section you can infer from the title and domain. Leave `_[open]_` only
   where genuine ambiguity exists. Do not ask what you can answer yourself.
5. Score commandments using the alignment states: **stable** / **fragile** / **ambiguous** / **contradictory** / **open**.
6. Record the current interpretation of the task in one paragraph.
7. Ask 2–3 pointed interrogation questions — prioritize the gaps most likely to expose
   a false positive, false negative, flawed assumption, or under-scoped problem. Challenge, do not confirm.

### Continuation (no `$ARGUMENTS`)

1. Read `.socrates/.current` to get the active session filename.
2. Read `.socrates/FILENAME.md`.
3. Print a one-line alignment summary per commandment (name + state only).
4. Restate the current interpretation before asking more questions when material ambiguity remains.
5. Prefer closing existing open questions over opening new ones.
6. Ask 1–3 interrogation questions targeting the highest-risk false-positive or false-negative paths.
7. Update the session file: incorporate answers, resolve closed questions, add new ones.

### Alignment States

Use these states instead of optimistic coverage labels:
- **Stable** — likely understood correctly and backed by explicit spec content.
- **Fragile** — appears understood but depends on assumptions or missing context.
- **Ambiguous** — multiple plausible interpretations remain.
- **Contradictory** — goals, constraints, requirements, or success criteria conflict.
- **Open** — not yet addressed.

Do not mark a commandment **stable** unless the session file contains explicit content supporting it. A fragile item is not a blocker by default, but it must be named so the executor knows where interpretation risk remains.

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

### Interrogation Principles

- One topic per question.
- Ask "why" to surface unstated assumptions.
- Ask "what happens when X fails" to probe robustness.
- Ask "What happens if we don't do this?" for do-nothing risk — never embed a timeframe in the question; let the user name the consequence and the timeline.
- Ask "who decides" to surface missing stakeholders.
- Ask "what is explicitly excluded" to sharpen scope.
- Challenge vague answers — either sharpen them or record as ambiguous, fragile, or open.
- Ask "what would a successful but wrong execution look like?" to expose false positives.
- Ask "what would be missing from an apparently good answer?" to expose false negatives.
- Prefer one question that closes two commandments over two that close one each.

## Phase 2 — Validation and Layered Reasoning

Triggered when all applicable commandments are **stable** or explicitly accepted as **fragile**, and Open Questions is empty or contains only acknowledged non-blockers.

Before entering plan mode, validate that the current interpretation is execution-ready:
- The problem statement identifies what is broken or missing.
- Success criteria define how to recognize a true positive.
- Context is sufficient for an agent to avoid predictable false positives and false negatives.
- Scope, constraints, and authority boundaries are explicit.
- Remaining ambiguities are classified as blocking, non-blocking, or intentional.

Synthesize the spec into an explicit reasoning chain. Each layer is derived from the
one below it. Present this chain before entering plan mode so the grounding is visible
and challengeable.

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

Layer 6 — Execution Readiness
  [Inputs, outputs, authority boundaries, dependencies, and escalation conditions.]
```

If any layer does not hold up under scrutiny, return to interrogation for that layer
before proceeding.

## Phase 3 — Plan Mode

After presenting the layered reasoning chain, enter plan mode using the `EnterPlanMode`
tool. In plan mode, develop a concrete implementation plan grounded in the spec.
The plan must be traceable back to the reasoning chain — no work that does not serve
a requirement, no requirement that does not serve the problem.

### Dependency Graph

Decompose the plan into a dependency graph. For each task, identify:
- **Blocks**: tasks that cannot start until this one is complete
- **Parallel-safe**: tasks with no dependencies on each other

Present the graph explicitly:

```
[Task A] ──► [Task C] ──► [Task E]
[Task B] ──► [Task C]
[Task D] ──────────────► [Task E]   (parallel with A→C)
```

### Execution Recommendation

After the dependency graph, recommend an execution strategy:

- **3+ independent tracks**: recommend `/lead` for orchestrated parallel execution.
  `/lead` decomposes the plan into sub-agents running in parallel — use it when the
  critical path is shortened by parallelism and the tasks are well-scoped enough to
  delegate without ambiguity.
- **Mostly sequential**: recommend working through tasks directly.
- **Mixed**: identify which phases benefit from `/lead` and which should be sequential.

Exit plan mode with `ExitPlanMode` for user approval.

## Spec Scaffold (`socrates.md`)

```markdown
# [Title]

**Status**: Interrogating
**Type**: [Engineering | Research/Analysis | Writing | General]
**Owner**: _[open]_
**Last Updated**: YYYY-MM-DD

## Problem Statement

_[open]_

## Requirements

_[open]_

## Preferences

_[open]_

## Constraints

_[open]_

## Success Criteria

_[open]_

## Tasks

_[open]_

## Inputs

_[open]_

## Outputs

_[open]_

## Authority Boundaries

### Executor May Decide

_[open]_

### Executor Must Escalate

_[open]_

### Executor Must Not Change

_[open]_

## Out of Scope

_[open]_

## Open Questions

_[open]_

## Risks

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

## Stakeholders

_[open]_
```

## Usage

```
/socrates "Unified rate card API for carrier negotiation"   # init: creates .socrates/TIMESTAMP.md
/socrates                                                   # continue: reads .socrates/.current
/socrates                                                   # continue until all commandments covered
```

Each invocation interrogates, updates the session file, and converges toward an execution-ready specification before plan mode.
