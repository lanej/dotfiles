---
description: "Verify execution results against a Socrates validation contract"
argument-hint: "artifact path, task output, or empty"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(cat:*)
  - Bash(date:*)
  - Bash(mkdir:*)
  - Agent
  - Bash(find:*)
  - Bash(printenv:*)
  - Bash(sort:*)
tags:
  - verification
  - validation
  - regression
---

# /verify

Read `$HOME/.claude/skills/verify/SKILL.md` and apply that shared workflow to `$ARGUMENTS` and the current request. Use the resources it routes to; do not recreate the procedure here. If the skill is missing, report the missing path and restore it with `make claude-shared`.
