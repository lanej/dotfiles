---
description: "Interrogate a task through Socratic dialogue to produce a validated execution-ready specification, then enter plan mode"
argument-hint: '"Task Title" (init) or empty (continue)'
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
  - Agent
  - ExitPlanMode
  - EnterPlanMode
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
8. **Verification** — Is there a reliable way to determine whether the outcome is a true positive — both at completion (a validation contract) and *while work is in progress* (a fast, cheap signal invoked on a defined cadence, or a deliberately constructed fallback when no fast signal exists)? The in-progress signal must be the **cheapest** check that still localizes a fault to the task that caused it — not the broadest available check. Breadth belongs in the completion contract, which runs once.
9. **Constraints** — Are time, team, resources, and compliance limits surfaced?
10. **Stakeholders** — Are beneficiaries, affected parties, and decision-makers named?
11. **Risk** — Is the riskiest assumption identified? What would invalidate this?
12. **Execution Readiness** — Are inputs, outputs, authority boundaries, and escalation conditions clear?
13. **Harmony** — Does this specification avoid contradicting itself or creating inconsistency elsewhere? What would this change break somewhere else in the spec that nobody is currently discussing? Unlike every other commandment, Harmony gets a row on every interrogation pass, not only when touched — fully evaluated when the pass mutated spec content, carried forward when it did not. See Commandment Scoring below.

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

Files live in `.socrates/YYYYMMDD-HHMMSS/` within the current working directory (one directory per session). Each Claude session binds to its own session directory via a pointer file `.socrates/.current-<CLAUDE_CODE_SESSION_ID>` (content: `TIMESTAMP:PID`), so concurrent sessions in the same repo don't collide. Read `$CLAUDE_CODE_SESSION_ID`/`$CLAUDE_PID` via `printenv` — never `$$`, which inside a Bash tool call is the subshell's PID, not Claude's. Write the pointer on Initialization and refresh it on every Continuation. If a session's own pointer is missing or its target directory has been removed, Continuation falls back to the picker (below) and claims whatever session it resolves. Timestamped sessions and their pointers are never deleted, even once stale — historical reasoning, critique evolution, and validation history matter.

Session artifacts:
- `spec.md` — authoritative specification
- `critique.md` — critique findings (if `/critique` was run)
- `verification.md` — verification results (if `/verify` was run)
- `plan.md` — downstream execution plan

## Phase 1 — Interrogation

### Plan Mode

This command manages its own phased execution. If plan mode is active at the start of Phase 1 or Phase 2, exit it immediately with `ExitPlanMode` before proceeding — plan mode is only entered intentionally at Phase 3. Don't let plan mode block session file writes or interrogation.

### Companion Files

This command reads two files from `$HOME/.claude/commands/socrates/` — `spec-scaffold.tpl` (Initialization) and `phases-2-3.txt` (Phases 2–3) — which exist only once `make claude` has symlinked this repo's `claude/commands/` into `~/.claude/commands`. If either Read fails, stop and tell the user: the socrates command's companion files aren't linked — run `make claude` from the dotfiles repo, then retry. Never reconstruct either file's content from memory — a regenerated scaffold or phase procedure that quietly drifts from the real file is worse than stopping.

### Research & Question Classification

Before forming any question, research: relevant source files (Read, Glob, grep), existing configs/scripts, memory and prior session context, domain conventions. The point is to arm the question, not to gatekeep it — skip a question only when research settles a mechanical, non-interpretive fact outright; never skip one because research produced a plausible guess that touches goals, tradeoffs, risk, or scope. Classify each candidate question:

- **Self-answerable** (mechanical facts with no bearing on intent — language, file layout, existing syntax, established conventions): answer silently; record as **Assumed** with a source citation.
- **Probable** (a real finding exists, but it touches goals, tradeoffs, risk, or scope): open the question with the finding — state what you found, then ask whether it holds and why/why not. Never silently fold it into the spec as Assumed, and never reduce it to a one-click confirmation.
- **User-only** (unresolvable from evidence — requires intent, priorities, or institutional knowledge only the user holds): ask, and follow through per the Dialogue Loop — don't accept a vague, unexamined, or contradictory first answer at face value.

### Question Framing

Default to a plain, open-ended prose question — Socratic dialogue is not a multiple-choice form. Reach for `AskUserQuestion` only for a small, genuinely enumerable set of known options where forcing a choice sharpens the answer: 2–4 distinct, plausible positions, not exhaustive and not false choices. For a probable-answer question with a research-backed lean, set that guess as the first (Recommended) option, but still explain the finding, not just present it as a checkbox. Use `multiSelect` for constraint enumeration or capability checklists, never for interpretive questions.

### Initialization (`$ARGUMENTS` is a task title)

1. Generate a timestamp (`date +%Y%m%d-%H%M%S`) and create `.socrates/TIMESTAMP/`.
2. Resolve `$HOME` via `printenv`, Read `$HOME/.claude/commands/socrates/spec-scaffold.tpl` (see Companion Files if this fails), substitute the title for `[Title]`, and write the result to `.socrates/TIMESTAMP/spec.md`.
3. Write `.socrates/.current-$CLAUDE_CODE_SESSION_ID` containing `TIMESTAMP:PID` (via `printenv`).
4. Set status to `Interrogating`, `Current Pass: 1`, and classify task type.
5. Research and classify candidate questions (see Research & Question Classification, above).
6. Pre-fill every section inferable from the title, domain, and research findings. Leave `_[open]_` only where genuine ambiguity remains. Cite evidence or mark claims **Assumed**.
7. Score commandments using the Alignment States (below). For each commandment touched this pass, append a Pass 1 row to spec.md's `## Commandment Scores` table (see Commandment Scoring). Harmony always gets a Pass 1 row. Pass 1 is always a full evaluation because initialization creates the spec.
8. Record the current interpretation of the task in one paragraph.
9. Begin the Dialogue Loop (below) on the highest-leverage open commandment first, running it to its stop condition (Dialogue Loop step 5).

### Continuation (no `$ARGUMENTS`)

**Fast path**: if this session already has its own pointer, resolve directly and run every step below in order — the fast path only replaces the discovery/picker steps (2–5), never anything after.

1. `printenv CLAUDE_CODE_SESSION_ID`. If `.socrates/.current-$CLAUDE_CODE_SESSION_ID` exists and its target directory still exists (`find .socrates/<TIMESTAMP> -maxdepth 0 -type d`), resolve SESSION_DIR from the pointer and skip to step 6. Otherwise continue to step 2.
2. Find all session directories: `find .socrates -maxdepth 1 -mindepth 1 -type d | sort -r` (newest first).
3. If none: tell the user no sessions exist and suggest `/socrates "Task Title"`. Stop.
4. If exactly one: use it as SESSION_DIR.
5. If multiple: use `AskUserQuestion` to let the user pick. For each candidate, show the title (first line of its `spec.md`) and the timestamp from the directory name; if another `.socrates/.current-*` pointer targets it, check liveness with `find /tmp/cc-socks -maxdepth 1 -name '<that pointer's PID>.sock'` — annotate "active in another session right now" if it returns output, "activity unknown" if `/tmp/cc-socks` itself doesn't exist on this machine, and nothing if it exists but the socket doesn't. Present newest first.
6. Load `SESSION_DIR/spec.md`. Refresh `.socrates/.current-$CLAUDE_CODE_SESSION_ID` to `TIMESTAMP:PID` for SESSION_DIR.
7. Increment `Current Pass` by 1, regardless of whether anything gets a Commandment Scores row this pass.
8. If `critique.md` exists, enter `Reconciling` — adjudicate findings, revise spec, classify unresolved disagreements.
9. Research any remaining open questions and classify them (see Research & Question Classification) before resuming the dialogue.
10. Print a one-line alignment summary per commandment touched this pass (name, state, score). Harmony always gets a new row: evaluate fully if this pass changed spec content; otherwise carry the prior assessment forward (see Commandment Scoring).
11. Restate the current interpretation before asking more questions if material ambiguity remains.
12. Prefer closing existing open questions over opening new ones.
13. Resume the Dialogue Loop on the most valuable open commandment, to its stop condition (Dialogue Loop step 5).
14. Update the session file: incorporate answers, resolve closed questions, add new ones.

### Alignment States

- **Stable** — likely understood correctly and backed by explicit spec content.
- **Fragile** — appears understood but depends on assumptions or missing context.
- **Ambiguous** — multiple plausible interpretations remain.
- **Contradictory** — goals, constraints, requirements, or success criteria conflict.
- **Open** — not yet addressed.

Don't mark a commandment **stable** unless the session file contains explicit content supporting it. A fragile item isn't a blocker by default, but it must be named so the executor knows where interpretation risk remains. **Ambiguous**, **contradictory**, and **open** never block the current pass from ending — the Dialogue Loop keeps running passes regardless — but they always block Phase 2 (the trigger in `phases-2-3.txt` requires every applicable commandment stable-or-fragile).

### Commandment Scoring

Every commandment touched in a pass gets an appended row (never overwritten) in spec.md's `## Commandment Scores` table:

- **Score** — confidence percentage (0–100%) in the current alignment-state assessment.
- **Why** — the causal/historical reason the underlying requirement, constraint, or behavior is the way it is, sourced from research.
- **Why not 100%** — what's driving the confidence gap in the score itself.
- **Escalated** — Yes/No: was a sub-70% score surfaced to the user as a dialogue question this pass?
- **Resolution** — `—` while unescalated. Once escalated: `Pending — <where the open question is recorded, e.g. Ambiguities → Blocking>` until answered. The pass that answers it appends a fresh row for the same commandment (per the append-only rule above) with `Resolution` stating how it was resolved.

**Harmony always gets a row; it does not always get re-derived.** Unlike every other commandment — scored only when touched, preserving the open-ended dialogue-loop design — Harmony gets a new row every single pass, because consistency can break silently in parts of the spec nobody is actively discussing. But the *evaluation* is conditional on there being something that could have broken:

- **Pass changed spec content or its grounding** (a requirement/constraint/criterion changed, an answer changed its interpretation, or new evidence invalidated an assumption): evaluate Harmony fully and write a complete row after incorporating the change.
- **Pass changed neither spec content nor its grounding**: append a row carrying the prior State, Score, Why not 100%, Escalated, and Resolution forward, with `Why: no spec mutation this pass; carried from pass N`. Keep the actual alignment state (for example Stable), so the stable-or-fragile phase gate still works. Pass 1 cannot carry forward. Updating only the pass counter or audit rows is not a substantive mutation.

A pass with no substantive change and no new conflicting evidence can reuse the prior assessment, so re-deriving Harmony there is the specification-side version of running the full test suite after a no-op — cost with no detection. The carry-forward row preserves the audit invariant (`/verify` Step 5 still finds a Harmony row for every integer from 1 to `Current Pass`) without paying for the evaluation. A carried-forward score below 70% that was already escalated stays escalated; it does not re-trigger the Deferral rule.

**Deferral rule.** A commandment scoring below 70% must be surfaced as a dialogue question, not silently recorded as Assumed — framed as sharpening understanding, not just closing a spec gap. Dialogue Loop step 2 still asks one question at a time: surface the highest-leverage sub-70% commandment this pass, and roll any other sub-70% commandment sharing the same root cause into that same question rather than asking a second one. A sub-70% score that doesn't share the pass's question stays open for a later pass — the Specification Freeze gate (not this rule) is what actually blocks the spec from validating while it's unresolved.

**Pass counter.** `Current Pass` is set to 1 on Initialization and incremented on every Continuation, regardless of whether anything gets a row that pass — this makes Harmony's cadence auditable later (verification checks that every integer from 1 to `Current Pass` has a Harmony row).

A specification may not transition to `Validated`/`Frozen: true` while the most recent row for any commandment has `Score < 70%` and `Resolution` unresolved (`—` or `Pending — …`) — escalating a question is not the same as answering it (Specification Freeze, in `phases-2-3.txt`).

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

## Phases 2–3 — Validation and Plan Mode

Read `$HOME/.claude/commands/socrates/phases-2-3.txt` (see Companion Files if this fails) and follow it when Phase 1 reaches its stop condition — all applicable commandments **stable** or explicitly accepted as **fragile** (Dialogue Loop step 5) *and* the spec's `Ambiguities → Blocking` empty — or on a Continuation pass whose spec Status is already `Validated` or later. It holds the layered reasoning chain, Specification Freeze criteria, Reopen Semantics, the plan-mode procedure, and the downstream commands. Don't run either phase from memory — Read the file first.

## Usage

```
/socrates "Unified rate card API for carrier negotiation"   # init: creates .socrates/TIMESTAMP/spec.md
/socrates                                                   # continue: resumes most recent session
/socrates                                                   # continue until validated and planned
```
