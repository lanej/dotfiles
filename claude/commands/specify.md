---
description: "Develop an evidence-backed specification through consequential dialogue; stop before planning"
argument-hint: '"Task Title" (init) or empty (continue)'
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
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

# /specify

Read `$HOME/.claude/skills/specify/SKILL.md` and apply that shared workflow to `$ARGUMENTS` and the current request. Use the resources it routes to; do not recreate the procedure here. If the skill is missing, report the missing path and restore it with `make claude-shared`.
