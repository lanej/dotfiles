# Debugging and monitoring workflows

## Common Workflows

### Debug a Session

```bash
# Show all errors in a session
claude-tail --errors-only --no-follow session.jsonl

# Show tool usage with errors
claude-tail --tools-only --errors-only session.jsonl

# Verbose output for debugging
claude-tail --verbose --errors-only session.jsonl
```

### Monitor Tool Usage

```bash
# Watch what tools are being called
claude-tail --tools-only -f session.jsonl

# Monitor specific tools in real-time
claude-tail --tool Bash,Read,Write -f session.jsonl

# Get tool usage statistics
claude-tail --stats --tools-only session.jsonl
```

### Analyze Session Activity

```bash
# Review activity in a time window
claude-tail --after 10:00:00 --before 11:00:00 --no-follow session.jsonl

# See compact summary of a session
claude-tail --compact --no-follow session.jsonl

# Get detailed statistics
claude-tail --stats session.jsonl
```

### Watch Live Sessions

```bash
# Follow the most recent session
claude-tail -f ~/.claude/sessions/$(ls -t ~/.claude/sessions/*.jsonl | head -1)

# Watch all new session files
claude-tail --pattern "~/.claude/sessions/*.jsonl"

# Monitor errors in real-time
claude-tail --errors-only -f current-session.jsonl
```

## Advanced Usage

### Combining Filters

```bash
# Show Read/Write operations with errors after 2pm
claude-tail --tool Read,Write \
           --errors-only \
           --after 14:00:00 \
           session.jsonl

# Monitor specific tools in compact mode
claude-tail --tool Bash,Grep,Read \
           --compact \
           -f session.jsonl
```

### Session Log Analysis

```bash
# Quick session overview
claude-tail --stats --no-follow session.jsonl

# Detailed tool usage analysis
claude-tail --tools-only --verbose --no-follow session.jsonl

# Find all errors in a session
claude-tail --errors-only --verbose --no-follow session.jsonl
```

### Debugging Workflows

```bash
# Debug a specific time period with full detail
claude-tail --verbose \
           --after 14:30:00 \
           --before 14:35:00 \
           --no-follow \
           session.jsonl

# Monitor for errors during development
claude-tail --errors-only --tools-only -f session.jsonl

# Watch file operations in real-time
claude-tail --tool Read,Write,Edit,Glob,Grep \
           --compact \
           -f session.jsonl
```
