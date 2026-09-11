---
description: "Routing reference for shedding a SUB-TASK to a sub-agent while you keep driving the session. Covers which agent type to dispatch and the borderline cases; the always-on trigger rule lives in CLAUDE.md. Use /handoff instead when the whole remaining task is being pushed out of a spent session."
tags:
  - context-management
  - agents
  - delegation
---

# /delegate — Sub-Task Routing Reference

The **trigger** is already a standing rule (`CLAUDE.md` → Execution & Delegation): delegate anything touching 2+ files, needing 2+ tool calls to gather context, all research, and off-topic side tasks. This file is not that rule restated — it's the *routing* table for when you've decided to delegate and need to pick a target, plus the cases where the trigger is genuinely ambiguous.

## `/delegate` vs `/handoff`

- **Delegation** — shed a *sub-task*. You stay in the driver's seat, receive a summary, act on it. Many per session.
- **`/handoff`** — shed the *remaining task* because context is already spent. You stop driving; the session's JSONL transcript is the payload. Once per session, if at all.

If you'll still be working after the agent returns, it's delegation. If you're leaving, it's a handoff.

## Agent routing

| Need | `subagent_type` |
|---|---|
| Find where something lives; open-ended "how does X work" | `Explore` |
| Multi-step research, unfamiliar library, 3+ tool calls | `general-purpose` |
| Implementation approach, step-by-step plan, trade-offs | `Plan` |
| Long docs → key points | `document-summarizer` |
| Review a PR / large diff | `code-reviewer`, `pull-request-commentor` |
| Commit message | `git-commit-message-writer` |

Dispatch with the `Agent` tool. Every call needs the six briefing fields from `CLAUDE.md`: Context, Domain, Sub-problem, Success, Constraints, Output format. Search breadth for `Explore` goes in the prompt prose ("medium", "very thorough") — there is no `thoroughness` parameter.

**Never dispatch `fork` when the brief depends on it not writing** — see `CLAUDE.md`. The attempted `PreToolUse` gate was removed; verify the output independently.

## Borderline calls

Delegate when the trigger is arguable but any of these hold:

- You're about to run a **second** grep/glob toward the same goal
- The thing could be named several ways (`login` / `signin` / `authenticate` / `auth`)
- You don't know where to look, so you can't bound the result size
- Results would be large and mostly discarded

Do it yourself when:

- The user named the exact file or asked *you* to make the edit
- It's a needle query — one exact class/function name
- It's already in context from earlier in this session

Note the asymmetry: a wasted delegation costs one round-trip; a wasted search costs context permanently. When genuinely torn, delegate.

## Verify what comes back

Sub-agent output is untrusted input (`CLAUDE.md` → Trust & Verification). Before relaying anything load-bearing — metrics, "deployed", "tests pass", "file written" — check it against primary state yourself. Full checklist in the `operating-lessons` skill.

Always summarize a completed delegated or background task before continuing, even on a bare "continue."
