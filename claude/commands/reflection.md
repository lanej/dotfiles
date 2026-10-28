---
description: Review the current session for repeated corrections and propose focused improvements without changing files
allowed-tools: Bash, Agent
---

Locate the current session JSONL under `~/.claude/projects/` using
`CLAUDE_CODE_SESSION_ID`, then invoke the `reflection` agent with the exact transcript path.
Ask for evidence-backed findings and proposed corrections inline. Do not authorize file,
memory, commit, messaging, or implementation changes through this command. Treat a legacy
`auto` argument as a request to return findings without interactive questions.
