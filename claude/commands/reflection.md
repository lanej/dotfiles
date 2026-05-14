---
description: Analyze session behavior against CLAUDE.md and apply improvements. Spawned as a background sub-agent by plan mode with argument 'auto' to apply changes without user interaction. Also invoke manually after a session where Claude misunderstood requests, ignored instructions, or needed repeated correction.
argument-hint: [auto]
allowed-tools: Read, Edit, Skill, TodoWrite, Bash(git:*)
---

## Step 1 — Analyze Chat History

Review the conversation history in your context window. Identify patterns indicating missing, incomplete, or incorrect CLAUDE.md instructions:

- Requests Claude misunderstood
- Behaviors the user had to correct more than once
- Tool preferences or workflows used repeatedly that are absent from CLAUDE.md
- Instructions that exist but were ignored or applied inconsistently
- Edge cases that produced wrong behavior

Structure your findings as a brief:

```
Missing instructions: <list or "none">
Incorrect instructions: <list or "none">
Ignored instructions: <list or "none">
```

## Step 2 — Invoke the CLAUDE.md Improver

Invoke the `claude-md-management:claude-md-improver` skill, passing your findings brief as the `args` so the skill has session signal beyond just reading the current CLAUDE.md.

If `$ARGUMENTS` contains `auto`:
- Run the skill autonomously — apply all improvements without interactive approval

Otherwise:
- Present your findings to the user first, then invoke the skill interactively
