---
description: "Draft a tight, verifiable condition string for the built-in /goal command"
argument-hint: [rough objective description]
allowed-tools: []
---

# /goal-prep — compile a /goal-ready condition

`/goal <condition>` registers a session-scoped Stop hook: Claude Code won't stop until `<condition>` holds, and the condition text itself becomes Claude's standing directive for the rest of the session — no re-prompting, no pausing to ask what to do next. That makes the condition string the only lever you have over scope and safety once it's set. Garbage in, unsupervised garbage out.

This command turns a rough objective into that string.

## What makes a bad /goal condition

- **Vague/unfalsifiable** — "make the code good", "improve reliability": nothing to check, so it never resolves cleanly and Claude loops or fakes completion.
- **No verifiable end-state** — no test/build/lint/PR/file signal to anchor "met".
- **No constraints** — /goal explicitly suppresses "ask before risky action." If the objective touches anything destructive, hard-to-reverse, or externally visible (push, force-push, delete, send, deploy, spend, merge), the condition must say what's off-limits, or Claude will do it unprompted.
- **Unbounded scope** — no non-goals stated, so autonomous continuation drifts into refactors/features nobody asked for.
- **Over 4000 characters** — hard limit; /goal rejects longer input outright.

## Process

1. Read `$ARGUMENTS` as the rough objective. If empty, ask for one before doing anything else.
2. Check the objective against the four failure modes above. Ask at most one or two terse clarifying questions, and only for what's genuinely ambiguous — a missing verifiable signal, or a risky action with no stated constraint. Don't interrogate an already-clear request.
3. Draft the condition as one dense paragraph, in this order, including only the sections that apply:
   - **Objective** — one sentence: the actual outcome wanted.
   - **Verifiable end-state** — the concrete, checkable signal(s) that make "met" true (tests pass, build green, PR opened, specific behavior/file exists, etc.). This is what gets checked every time Claude tries to stop.
   - **Constraints** — anything destructive, hard-to-reverse, or externally visible that must NOT happen without the user's explicit say-so, named specifically (no push/force-push, no deletion, no sending, no deploying/merging, ask before X). Carry over standing safety norms implied by the objective even if the user didn't restate them.
   - **Non-goals** — explicitly out of scope, to block autonomous scope creep.
4. Keep it as tight as the objective allows. This is a directive Claude re-reads every time it tries to stop, not a spec document — aim well under the 4000-character cap, not up to it.
5. Output exactly:

```
/goal <condition text>
```

followed by one line noting anything inferred or any risk flagged in Constraints, so the user can amend before running it.

This command cannot run `/goal` for you — slash-command dispatch happens in the CLI's input parser before a prompt ever reaches the model, and there is no tool surface (no `SlashCommand` tool, and `Skill` explicitly excludes built-ins) for a running turn to invoke another slash command, built-in or custom. The bare `/goal <condition>` line above is the hand-off point: paste it in to actually set the goal.

If the objective is inherently unfalsifiable even after clarification (pure taste/aesthetic judgment with no proxy signal), say so plainly instead of forcing a fake checkbox — recommend a narrower proxy, or recommend skipping /goal for this task.
