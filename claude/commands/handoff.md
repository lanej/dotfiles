---
description: "Delegate remaining work to a fresh sub-agent to escape context pollution and reduce cost. Writes a rich session context file and a minimal brief, presents the brief for user approval, then spawns a sub-agent. The sub-agent reads the brief to start and can pull the full session context on demand if it needs more."
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

Escape context pollution by delegating remaining work to a fresh sub-agent. Write a rich session context file and a minimal brief, get user approval, then spawn — the sub-agent starts lean and can self-serve more context if it hits a gap.

## Step 1: Capture session ID and set paths

```bash
echo "${CLAUDE_CODE_SESSION_ID:-unknown}"
```

Derive a short kebab-case slug from the task name:
- If an argument was passed (e.g., `/handoff refactor-auth`), use it directly
- Otherwise derive from the session goal: e.g., "migrate DORA tables to BQ" → `dora-bq-migration`

```bash
mkdir -p .claude/sessions .claude/handoffs
```

Paths:
- Session context file: `.claude/sessions/<session-id>.md`
- Brief: `.claude/handoffs/<slug>.md`

## Step 2: Write the session context file

This is the comprehensive record — everything you know. The sub-agent reads this only if the brief doesn't cover something. Write it first because the brief is derived from it.

```markdown
# Session context: <session-id>

**Task**: [task name]
**Date**: [date]

## Full goal
[Complete description of what we are trying to accomplish]

## Everything discovered
[All findings, research results, failed approaches, gotchas — with why each matters]

## All decisions made
[Every decision, with the reasoning and what was ruled out]

## Complete file state
[Every file touched: what it contains now, what changed, what was removed]

## Open questions
[Anything unresolved, with current best guess and confidence]

## Failed approaches
[What was tried and why it didn't work — so the sub-agent doesn't repeat them]
```

## Step 3: Write the brief

The brief is the minimal fast-start. Every sentence must change a decision, constrain an action, or describe current state. No narrative.

```markdown
# Handoff: [task name]

**Session**: <session-id>
**Session context**: `.claude/sessions/<session-id>.md`
**Brief**: `.claude/handoffs/<slug>.md`

> If this brief doesn't cover something you need, read the session context file at the path above before asking or assuming.

## Goal
[One tight paragraph]

## Key discoveries
- [fact]: [why it matters]

## Decisions — do not revisit
- [decision]: [reason]

## Current state
- `[file]`: [what it does now]

## Next action
[Exact first thing to do — specific enough to act on without reading anything else]

## Constraints
- [hard limit or known unknown with resolution path]
```

## Step 4: Spawn the sub-agent immediately in the background

Spawn using the Agent tool with `run_in_background: true`. Pass the full brief as the sub-agent's prompt verbatim. Do not wait for user approval first — the sub-agent performs its own context check.

Tell the user: "Sub-agent spawned. You'll be notified when it completes or if it needs more context."

### Sub-agent instructions (include verbatim in the prompt)

```
BEFORE doing any work:

1. Read this brief.
2. Read the session context file at the path listed in the brief.
3. Assess: can you execute the Next action without making assumptions that could be wrong?

If YES: proceed. Return a structured summary when done:
  - completed: [what was done]
  - changed: [files modified and how]
  - blockers: [anything you couldn't resolve]

If NO: return this immediately and do nothing else:
  - status: context-insufficient
  - gaps: [what's missing and what decision each blocks]
  - assumptions-if-forced: [what you'd assume if told to proceed anyway, and the risk]

Do not guess. Do not begin execution if the context is insufficient.
```

### When the sub-agent completes

- If it returns a summary: forward it to the user. Done.
- If it returns `context-insufficient`: surface the gaps to the user, collect answers, update the session file with the new information, and re-spawn.

Do not re-execute work the sub-agent completed.
