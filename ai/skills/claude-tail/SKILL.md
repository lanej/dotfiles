---
name: claude-tail
description: Analyzes Claude Code session logs (JSONL format) with syntax highlighting, filtering by event type/tool/time/errors, and real-time following. Use when debugging a session, monitoring tool usage, understanding workflows, or tracking errors. Don't use for reading general Claude Code documentation or for non-session-log files.
---

# Claude session logs

Use `claude-tail` to inspect Claude Code JSONL session logs. For a bounded analysis, use `--no-follow`; the default follows the file and stays running. Start with an overview, then narrow to the relevant tools, errors, or time window.

```bash
claude-tail --stats --no-follow session.jsonl
claude-tail --errors-only --no-follow session.jsonl
claude-tail --tool Read,Write --no-follow session.jsonl
```

Read the relevant reference for additional options and examples:

| Task | Read |
| --- | --- |
| Opening files/stdin, following, display modes, filters, width and wrapping | [Usage and filters](references/usage-and-filters.md) |
| Debugging, monitoring tool use, activity windows, combined filters | [Analysis workflows](references/analysis-workflows.md) |
| Finding logs, event/tool names, tips, command lookup | [Log reference](references/log-reference.md) |
