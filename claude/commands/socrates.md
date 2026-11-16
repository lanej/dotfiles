---
description: "Interrogate consequential decisions into an evidence-backed specification, then enter plan mode"
argument-hint: '"Task Title" (init) or empty (continue)'
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
  - Agent
  - ExitPlanMode
  - EnterPlanMode
  - Bash(date:*)
  - Bash(mkdir:*)
  - Bash(grep:*)
  - Bash(find:*)
  - Bash(printenv:*)
  - Bash(sort:*)
tags:
  - specification
  - dialogue
---

# /socrates

Read `$HOME/.claude/skills/socrates/SKILL.md` and apply that shared workflow to `$ARGUMENTS` and the current request. Use the resources it routes to; do not recreate the procedure here. If the skill is missing, report the missing path and restore it with `make claude-shared`.
