---
description: "Distill the current session into a dense continuation brief for a fresh agent. Writes .claude/handoff.md with everything a replacement needs to act — discoveries, decisions, current state, next action."
argument-hint: "[optional: focus area or remaining task description]"
allowed-tools:
  - Write
  - Read
tags:
  - workflow
  - context
  - handoff
---

# /handoff - Session Context Handoff

Write a continuation brief that a fresh agent can load to pick up exactly where this session left off.

## Instructions

Produce a dense, imperative briefing for your replacement. Not a summary for human reading — a bootstrap prompt for an agent starting cold. Every sentence must either change a decision, constrain an action, or describe current state. No narrative, no preamble, no "we explored X."

Write the brief to `.claude/handoff.md`.

## Brief Structure

```markdown
# Handoff: [task name — one line]

**Context**: [repo or project path, tech stack, 1-2 sentences max]

## Goal
[What we are building/fixing and why — one tight paragraph]

## Key discoveries
- [fact]: [why it matters — what it changes about the approach]
- [fact]: [why it matters]
- ...

## Decisions — do not revisit
- Use [X] over [Y]: [reason]
- [decision]: [reason]
- ...

## Current state
- `[file]`: [what it does now / what changed]
- `[file]`: [what it does now / what changed]
- ...

## Next action
[Exact first thing to do. Specific enough to act on without re-reading all files.]

## Constraints
- [hard limit — what NOT to do and why]
- [known unknown — what is still unresolved and what to do about it]
- ...
```

## Rules

- **Dense**: If a fact doesn't change a decision or constrain an action, omit it.
- **Imperative**: Write as instructions to the replacement, not as notes to self.
- **State-accurate**: Reflect actual current file state, not intended state.
- **No ambiguity in next action**: It must be specific enough to execute without additional context.
- **Flag unresolved blockers**: If something is unknown or risky, say so explicitly with the recommended resolution path.

## After writing

Print the path: `.claude/handoff.md`

Then print a one-line instruction the user can paste to bootstrap the fresh session:

```
> Read .claude/handoff.md then continue the handoff task.
```
