---
description: Analyze session behavior against CLAUDE.md and apply improvements. Spawned as a background sub-agent by plan mode with argument 'auto' to apply changes without user interaction. Also invoke manually after a session where Claude misunderstood requests, ignored instructions, or needed repeated correction.
argument-hint: [auto]
allowed-tools: Bash, Agent
---

Find the current session JSONL file and invoke the `reflection` agent with it.

1. Run `find ~/.claude/projects -name "${CLAUDE_CODE_SESSION_ID}.jsonl" 2>/dev/null | head -1` to get the session file path.
2. Invoke the `reflection` agent via the Agent tool, passing a briefing that includes:
   - The session file path from step 1
   - Whether to run autonomously: `auto` if `$ARGUMENTS` contains `auto`, otherwise interactive
