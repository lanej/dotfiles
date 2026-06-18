---
description: "Delegate remaining work to a fresh sub-agent to escape context pollution and reduce cost. Distills current session into a dense brief, writes it to .claude/handoffs/<task-slug>.md, then immediately spawns a sub-agent with that brief as its prompt. Sub-agent does the work in clean context; parent receives the result."
argument-hint: "<task-name> (used as filename slug; derived from session goal if omitted)"
allowed-tools:
  - Write
  - Read
  - Bash
  - Agent
tags:
  - workflow
  - context
  - handoff
---

# /handoff - Context Delegation to Sub-Agent

Escape context pollution by delegating remaining work to a fresh sub-agent. Write a dense brief, then spawn the sub-agent with it — work continues in clean context immediately.

## Filename

Derive a short kebab-case slug from the task name:
- If an argument was passed (e.g., `/handoff refactor-auth`), use it directly: `refactor-auth`
- Otherwise derive from the session goal: e.g., "migrate DORA tables to BQ" → `dora-bq-migration`

Write to: `.claude/handoffs/<slug>.md`

Create the directory if it doesn't exist: `mkdir -p .claude/handoffs`

## Session ID

Before writing, capture the originating session ID:

```bash
echo "${CLAUDE_CODE_SESSION_ID:-unknown}"
```

Use whatever value that produces. If empty, use `unknown`.

## Instructions

Produce a dense, imperative briefing for your replacement. Not a summary for human reading — a bootstrap prompt for an agent starting cold. Every sentence must either change a decision, constrain an action, or describe current state. No narrative, no preamble, no "we explored X."

## Brief Structure

```markdown
# Handoff: [task name — one line]

**Handed off from session**: [session ID captured above]
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

## After writing the file

Print the full brief to the user. Then ask:

> "Does this brief accurately capture the context? Approve to spawn the sub-agent, or tell me what to correct."

Do not spawn the sub-agent until the user explicitly approves. Accept corrections and update the brief (and file) before re-presenting.

## On approval

Spawn a sub-agent using the Agent tool. Pass the full brief content as the sub-agent's prompt verbatim — do not summarize or truncate it. The sub-agent should treat the brief as its complete starting context and begin executing the **Next action** immediately.

The parent session receives the sub-agent's result and surfaces it to the user. Do not re-derive or re-execute work the sub-agent already completed — just forward the result.

If the sub-agent cannot complete the task (blocked on a genuine blocker), surface the blocker directly. Do not spawn another sub-agent without user instruction.
