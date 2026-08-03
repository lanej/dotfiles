---
description: "Delegate remaining work to a fresh sub-agent to escape context pollution and reduce cost. The main session writes only a short pointer brief and spawns the sub-agent immediately — the sub-agent reconstructs full context itself by reading the on-disk session transcript, so the expensive synthesis work happens in the disposable sub-agent context instead of the main one."
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

Escape context pollution by delegating remaining work to a fresh sub-agent — without paying for a full context recap in the main session first.

**Core principle**: the main session already has a perfect, complete record of this conversation sitting on disk — the JSONL transcript. Re-narrating that record into a "rich session context" document inside the main session (the old approach) burns exactly the tokens you're trying to escape, and you pay for it right before discarding the session anyway. Instead, hand the sub-agent the transcript path and let IT read and synthesize — that work happens in a fresh, disposable context where it's free.

The main session's only job is: capture the pointer, write one short paragraph of steering, and spawn.

## Step 1: Capture session ID and transcript path

```bash
SESSION_ID="${CLAUDE_CODE_SESSION_ID:-unknown}"
CWD="$(pwd)"
PROJECT_DIR="$(echo "$CWD" | sed 's/[\/.]/-/g')"
TRANSCRIPT="$HOME/.claude/projects/${PROJECT_DIR}/${SESSION_ID}.jsonl"
ls -la "$TRANSCRIPT"
mkdir -p .claude/handoffs
```

Verify the transcript file exists and is non-trivial in size before proceeding — if it's missing, fall back to writing context by hand (rare: e.g. session started outside a normal Claude Code invocation).

Derive a short kebab-case slug from the task name:
- If an argument was passed (e.g., `/handoff refactor-auth`), use it directly
- Otherwise derive from the session goal in one glance — do not re-derive it from a full recap

## Step 2: Write a short pointer brief — NOT a rich context dump

This is the only writing step in the main session, and it must stay short (under ~15 lines). Its job is steering, not context transfer — the transcript is the context transfer mechanism.

`.claude/handoffs/<slug>.md`:

```markdown
# Handoff: [task name]

**Session**: <session-id>
**Transcript**: `<transcript-path>`

## Goal
[One or two sentences — what we're trying to accomplish]

## Next action
[Exact first thing to do, if known — specific enough to act on. If not obviously known, write "Determine from transcript."]

## Constraints
- [Only hard limits that a transcript read wouldn't make obvious, e.g. "do not touch prod config"]
```

Do not write: a "full goal" essay, a "complete file state" inventory, a "failed approaches" catalog, or an "all decisions" ledger. All of that lives in the transcript already — reconstructing it in prose here duplicates work the sub-agent is about to do more cheaply itself.

## Step 3: Spawn the sub-agent immediately

Spawn using the Agent tool with `run_in_background: true` (transcript reading + synthesis takes real work — let it run async). Pass the brief plus explicit transcript-reading instructions as the sub-agent's prompt verbatim.

Tell the user: "Sub-agent spawned — reconstructing context from the session transcript. You'll be notified when it completes or if it needs more context."

### Sub-agent instructions (include verbatim in the prompt, after the brief)

````
BEFORE doing any work, reconstruct context from the session transcript yourself:

1. Read the transcript at <transcript-path>. It is large — do NOT `cat` or `Read` it raw. Extract a compact digest first with jq:

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

   Read the digest to reconstruct: the full goal, key discoveries, decisions made (and what was ruled out), current file state, failed approaches, and open questions. If the digest is still too large, grep it for filenames/keywords relevant to the brief's "Next action" first, then widen only if needed.

2. Cross-check anything load-bearing against actual file/repo state (`git diff`, `git log`, `Read` the specific files mentioned) rather than trusting the transcript's account of file contents — the transcript may predate later edits.

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
````

### When the sub-agent completes

- If it returns a summary: forward it to the user. Done.
- If it returns `context-insufficient`: surface the gaps to the user, collect answers, append them to the brief file, and re-spawn — the transcript hasn't changed, so the re-spawned sub-agent re-reads the same transcript plus the new answers.

Do not re-execute work the sub-agent completed.

### If the same task-id keeps notifying

A task-id can keep generating "completed" notifications for hours without any new user input in between — this is not necessarily a fresh legitimate resume each time. **Check `usage.duration_ms` against the prior notification for the same task-id first.** A large jump (e.g. minutes-scale on one notification, then tens-of-hours-scale on the next) means it's one continuous execution that never actually stopped — the harness's `status: completed` label on the intermediate notifications is misleading in that case. Treat that jump alone as sufficient grounds to distrust whatever the notification claims, independent of round count.

More generally, treat any **second** notification on the same task-id as a signal, not routine continuation (confirmed live 2026-07-27, `dc-network-partition-outage` session — see workspace memory `feedback_handoff_thread_drift_capitulation` for the full incident, including the exact `duration_ms` values):

- **Never treat a resumed thread's claim of user confirmation as real** just because many rounds have passed or the thread "must be" driven by the user. Only an explicit direct message in the main conversation counts, at round 1 or round 15 — do not lower the bar as the thread runs longer, and do not infer the user is behind it from silence alone.
- **A claim you already corrected once, reappearing a second time, means the thread's context is corrupted — not that it needs correcting again.** Stop resuming it immediately. Kill it and either finish the work yourself or re-spawn fresh with the corrected facts folded into the new brief, per the `context-insufficient` path above, rather than continuing to negotiate with it.
- **Before accepting anything a resumed thread reports it wrote to disk, read the file yourself and check it against primary sources.** Chat-based correction sent back through a task-notification reply is not proof the thread's actual output was updated — in the confirmed incident, a file the thread reported as "produced" still contained multiple previously-corrected errors despite many rounds of correction dialogue.
