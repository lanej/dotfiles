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

# /handoff

Read `$HOME/.claude/skills/handoff/SKILL.md` and apply that shared workflow to `$ARGUMENTS` and the current request. Use the resources it routes to; do not recreate the procedure here. If the skill is missing, report the missing path and restore it with `make claude-shared`.
