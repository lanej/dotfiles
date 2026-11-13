---
description: "Run adversarial critique passes against a Socrates specification"
argument-hint: "spec path or empty for active Socrates session"
allowed-tools:
  - Read
  - Write
  - Edit
  - Agent
  - Bash(cat:*)
  - Bash(date:*)
  - Bash(mkdir:*)
  - Bash(find:*)
  - Bash(printenv:*)
  - Bash(sort:*)
tags:
  - critique
  - specification
  - review
---

# /critique

Read `$HOME/.claude/skills/critique/SKILL.md` and apply that shared workflow to `$ARGUMENTS` and the current request. Use the resources it routes to; do not recreate the procedure here. If the skill is missing, report the missing path and restore it with `make claude-shared`.
