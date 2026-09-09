---
description: "Hand the REMAINING work of a spent session to a fresh sub-agent. Writes a short pointer brief (not a context dump) and spawns immediately — the sub-agent rebuilds context by reading this session's on-disk JSONL transcript, so synthesis happens in a disposable context instead of the polluted one. Use when the session itself is the problem; use /delegate when only a sub-task is."
argument-hint: "<task-name> (filename slug; derived from session goal if omitted)"
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

# /handoff — Session-Terminal Context Escape

## When to use this

Use `/handoff` when **the session is the problem**, not the task:

- Context is large enough that the next step is expensive or degraded
- Long debugging thread with many dead ends still occupying context
- You are about to `/clear` or `/compact` but the remaining work is well-defined
- The remaining work is a *continuation*, not a discrete side-quest

**Do NOT use `/handoff` when:**

| Situation | Use instead |
|---|---|
| One sub-task would pollute context (search, research, review) | plain `Agent` dispatch — see `/delegate` |
| You will keep driving the session afterward | plain `Agent` dispatch |
| Context is fine, task is just big | plain `Agent` dispatch, or `subagent-driven-development` |
| Remaining work is unclear even to you | resolve it with the user first — a handoff cannot invent a goal |
| No JSONL transcript exists (non-standard invocation) | write the brief by hand, then dispatch normally |

### `/handoff` vs `/delegate` in one line

- **`/delegate`** — shed a *sub-task*. You stay in the driver's seat. Context is protected going forward.
- **`/handoff`** — shed the *remaining task*. You stop driving. Context already spent; the transcript becomes the payload.

`/delegate` is a routing decision made dozens of times per session. `/handoff` is a session-terminal decision made once, if at all.

## Core principle

The complete record of this conversation is already on disk as JSONL. Re-narrating it into a "rich context document" inside the main session burns exactly the tokens you are trying to escape — and you pay right before discarding the session. Hand over the *transcript path*, not a prose recap. The main session's only job: capture the pointer, write one paragraph of steering, spawn.

## Step 1 — Capture transcript path

```bash
SESSION_ID="${CLAUDE_CODE_SESSION_ID:-unknown}"
PROJECT_DIR="$(pwd | sed 's/[\/.]/-/g')"
TRANSCRIPT="$HOME/.claude/projects/${PROJECT_DIR}/${SESSION_ID}.jsonl"
ls -la "$TRANSCRIPT" && mkdir -p .claude/handoffs
```

If the transcript is missing or trivially small, stop — fall back to writing context by hand. A handoff without a transcript is just a worse `Agent` dispatch.

Slug: use `$ARGUMENTS` if given; otherwise derive from the session goal in one glance. Do not re-derive it from a recap.

## Step 2 — Write a pointer brief, not a context dump

`.claude/handoffs/<slug>.md`, hard cap ~15 lines:

```markdown
# Handoff: [task name]

**Transcript**: `<transcript-path>`

## Goal
[One or two sentences]

## Next action
[Exact first thing to do. If not obvious, write "Determine from transcript."]

## Constraints
- [Only hard limits a transcript read would NOT make obvious]
```

Do not write a full-goal essay, a file-state inventory, a failed-approaches catalog, or a decisions ledger. All of it is in the transcript; prose-duplicating it is the exact cost `/handoff` exists to avoid.

## Step 3 — Spawn immediately

`Agent` with `run_in_background: true`. Prompt = the brief, then the block below verbatim.

Tell the user: "Sub-agent spawned — reconstructing context from the session transcript."

````
BEFORE any work, reconstruct context from the session transcript:

1. The transcript is large — do NOT cat or Read it raw. Extract a digest:

   jq -r '
     select(.type=="user" or .type=="assistant")
     | .message.content as $c
     | if ($c|type)=="string" then $c
       else
         [$c[] |
           if .type=="text" then .text
           elif .type=="thinking" then "[thinking] " + (.thinking // "")
           elif .type=="tool_use" then "[tool_use] " + .name + " " + ((.input | tostring)[0:150])
           elif .type=="tool_result" then "[tool_result] " + ((.content | tostring)[0:150])
           else empty end
         ] | join("\n")
       end
   ' <transcript-path>

   Reconstruct: goal, key discoveries, decisions and what was ruled out, current
   file state, failed approaches, open questions. If still too large, grep the
   digest for filenames/keywords from the brief's "Next action" first.

2. Cross-check anything load-bearing against actual state (git diff, git log,
   Read the specific files). The transcript may predate later edits.

3. Assess: can you execute the Next action without guessing?

If YES — proceed, then return:
  - completed: [what was done]
  - changed: [files modified and how]
  - blockers: [unresolved]

If NO — return this immediately and do nothing else:
  - status: context-insufficient
  - gaps: [what's missing and what decision each blocks]
  - assumptions-if-forced: [what you'd assume, and the risk]

Do not guess. Do not begin execution on insufficient context.
````

## Step 4 — On completion

- **Summary returned** → forward it to the user. Done.
- **`context-insufficient`** → surface the gaps, collect answers from the user, append them to the brief, re-spawn fresh. The transcript is unchanged; only the brief grows.

Do not re-execute work the sub-agent completed.

**Re-spawn, never resume.** If a handoff thread reports a claim you already corrected once, its context is corrupted — kill it and re-spawn with the correction folded into the brief. Verify claimed file writes by reading the file yourself. (Full failure mode: `operating-lessons` skill, "Resumed sub-agent thread drift"; `CLAUDE.md` Trust & Verification.)
