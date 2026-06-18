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

## Step 4: Present for approval

Print the full brief to the user. Then ask:

> "Does this brief accurately capture the context? Approve to spawn the sub-agent, or tell me what to correct."

Do not spawn until the user explicitly approves. Accept corrections, update both files, re-present.

## Step 5: On approval — spawn the sub-agent

Spawn a sub-agent using the Agent tool. Pass the full brief as the sub-agent's prompt verbatim.

The sub-agent should:
1. Read the brief
2. If it hits a gap the brief doesn't cover, read `.claude/sessions/<session-id>.md` — do not ask the parent first
3. Execute the **Next action** and continue until done or genuinely blocked
4. Return a structured summary: what was completed, what changed, any blockers

The parent receives that summary and forwards it to the user. Do not re-execute work the sub-agent completed.
