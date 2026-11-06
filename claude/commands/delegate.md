---
description: "Routing reference for shedding a SUB-TASK to a sub-agent while you keep driving the session. Covers which agent type to dispatch and the borderline cases; the always-on trigger rule lives in CLAUDE.md. Use /handoff instead when the whole remaining task is being pushed out of a spent session."
tags:
  - context-management
  - agents
  - delegation
---

# /delegate — Sub-Task Routing Reference

Use this routing reference after deciding that a self-contained sub-task benefits from
context isolation, independent judgment, or parallel work. File and tool-call counts
alone do not justify delegation. Follow any session-specific delegation constraints.

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

Dispatch with the `Agent` tool. Every call needs the six briefing fields from `CLAUDE.md`: Context, Domain, Sub-problem, Success, Constraints, Output format. Search breadth for `Explore` goes in the prompt prose ("medium", "very thorough") — there is no `thoroughness` parameter.

**Never dispatch `fork` when the brief depends on it not writing** — see `CLAUDE.md`. The attempted `PreToolUse` gate was removed; verify the output independently.

## Choosing a boundary

Keep bounded lookups, routine commit messages, and small edits in the primary task.
Delegate investigations with a clear question and bounded sources when the returned
synthesis will save substantial context, or independent tasks that can safely run in
parallel. Do not expand the user's scope by silently starting unrelated background work.

## Verify what comes back

Sub-agent output is untrusted input (`CLAUDE.md` → Trust & Verification). Before relaying anything load-bearing — metrics, "deployed", "tests pass", "file written" — check it against primary state yourself. Full checklist in the `operating-lessons` skill.

Always summarize a completed delegated or background task before continuing, even on a bare "continue."
