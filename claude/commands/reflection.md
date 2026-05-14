---
description: Analyze and improve Claude Code instructions
argument-hint: [auto]
allowed-tools: Read, Edit, Skill, TodoWrite, Bash(git:*)
---

Analyze the chat history in your context window. Identify patterns that suggest missing, inconsistent, or incorrect instructions in CLAUDE.md:

- Misunderstandings of user requests
- Behaviors the user had to correct
- Tool preferences or workflows invoked repeatedly without being in CLAUDE.md
- Edge cases that caused wrong behavior

Then invoke the `claude-md-management:claude-md-improver` skill to audit and apply improvements to all CLAUDE.md files.

If `$ARGUMENTS` contains `auto` (unattended/background mode):
- Pass your findings from the chat history analysis as context to the skill
- Apply all improvements without interactive approval
- The skill runs autonomously and applies changes directly

Otherwise (interactive mode):
- Present your chat history findings first
- Then invoke the skill and let it guide the interactive improvement flow
