# Log locations, events, and command reference

## Session Log Location

Claude Code session logs are typically stored in:

```bash
~/.claude/sessions/*.jsonl
```

### Find Recent Sessions

```bash
# List sessions by most recent
ls -lt ~/.claude/sessions/*.jsonl | head -5

# View the most recent session
claude-tail ~/.claude/sessions/$(ls -t ~/.claude/sessions/*.jsonl | head -1)
```

## Common Event Types

- **tool_use** - Claude called a tool (Read, Write, Bash, etc.)
- **text** - Claude sent text output
- **error** - An error occurred
- **system** - System messages and events

## Common Tools to Filter

- **Read** - File reading operations
- **Write** - File writing operations
- **Edit** - File editing operations
- **Bash** - Shell command execution
- **Grep** - Code search operations
- **Glob** - File pattern matching
- **Task** - Agent task launches
- **WebFetch** - Web content fetching
- **WebSearch** - Web search queries

## Best Practices

1. **Use follow mode for active sessions**: Monitor live sessions with `-f`
2. **Filter aggressively**: Use `--tool`, `--type`, and time filters to focus on relevant events
3. **Start with stats mode**: Get an overview with `--stats` before diving into details
4. **Use compact mode for overviews**: Quickly scan many events with `--compact`
5. **Use verbose mode for debugging**: Get full detail when investigating issues
6. **Watch for errors**: Regular `--errors-only` checks help catch issues early
7. **Analyze tool patterns**: Use `--tools-only` to understand workflow patterns

## Tips

- Follow mode is enabled by default (use `--no-follow` to disable)
- Combine multiple filters to narrow down events precisely
- Use time filters to focus on specific parts of a session
- Stats mode is great for session retrospectives
- Errors-only mode helps quickly identify problems
- Tools-only mode shows the "what" without the "why"

## Quick Reference

```bash
# View and follow
claude-tail session.jsonl

# View once
claude-tail --no-follow session.jsonl

# Show stats
claude-tail --stats session.jsonl

# Only errors
claude-tail --errors-only session.jsonl

# Only tools
claude-tail --tools-only session.jsonl

# Filter by tool
claude-tail --tool Read,Write session.jsonl

# Filter by time
claude-tail --after 14:00:00 --before 15:00:00 session.jsonl

# Compact output
claude-tail --compact session.jsonl

# Verbose output
claude-tail --verbose session.jsonl

# Watch pattern
claude-tail --pattern "*.jsonl"
```
