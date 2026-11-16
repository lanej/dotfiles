---
description: "Run the semantic alignment workflow from specification through validation-ready execution planning"
argument-hint: "task description"
allowed-tools:
  - Read
  - Write
  - Edit
  - Agent
  - Bash(cat:*)
  - ExitPlanMode
  - EnterPlanMode
tags:
  - workflow
  - shaping
  - orchestration
---

# /shape

Read `$HOME/.claude/skills/shape/SKILL.md` and apply that shared workflow to `$ARGUMENTS` and the current request. Use the resources it routes to; do not recreate the procedure here. If the skill is missing, report the missing path and restore it with `make claude-shared`.
