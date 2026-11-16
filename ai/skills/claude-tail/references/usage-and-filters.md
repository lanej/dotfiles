# Session log usage, display, and filters

## Core Concepts

`claude-tail` reads Claude Code session logs (JSONL format) and displays them with:
- Syntax highlighting and colors
- Real-time following (like `tail -f`)
- Filtering by event type, tool, time range, or errors
- Multiple display modes (compact, verbose, stats, tools-only)

## Basic Usage

### View a Session Log

```bash
# View a specific log file (follows by default)
claude-tail ~/.claude/sessions/2024-01-15-session.jsonl

# View without following (read once and exit)
claude-tail --no-follow ~/.claude/sessions/2024-01-15-session.jsonl

# Read from stdin
cat session.jsonl | claude-tail
```

### Follow Logs in Real-Time

```bash
# Follow mode is enabled by default
claude-tail session.jsonl

# Explicitly enable follow mode
claude-tail -f session.jsonl

# Follow multiple files
claude-tail session1.jsonl session2.jsonl
```

### Watch for New Logs

```bash
# Watch all JSONL files in current directory
claude-tail --pattern "*.jsonl"

# Watch all session logs
claude-tail --pattern "~/.claude/sessions/*.jsonl"
```

## Display Modes

### Compact Mode

```bash
# Minimal output, one-line per event
claude-tail --compact session.jsonl
```

### Verbose Mode

```bash
# Detailed output with full event information
claude-tail --verbose session.jsonl
```

### Statistics Mode

```bash
# Show statistics about the session
claude-tail --stats session.jsonl
```

### Tools-Only Mode

```bash
# Show only tool usage events
claude-tail --tools-only session.jsonl
```

## Filtering

### Filter by Event Type

```bash
# Show only specific event types (comma-separated)
claude-tail --type tool_use,error session.jsonl

# Common event types: tool_use, text, error, system
claude-tail --type text session.jsonl
```

### Filter by Tool Name

```bash
# Show only specific tools (comma-separated)
claude-tail --tool Read,Write session.jsonl

# Show only bash commands
claude-tail --tool Bash session.jsonl

# Show only file operations
claude-tail --tool Read,Write,Edit session.jsonl
```

### Filter by Time Range

```bash
# Show events after a specific time (HH:MM:SS)
claude-tail --after 14:30:00 session.jsonl

# Show events before a specific time
claude-tail --before 15:45:00 session.jsonl

# Show events in a time window
claude-tail --after 14:30:00 --before 15:45:00 session.jsonl
```

### Show Only Errors

```bash
# Display only error events
claude-tail --errors-only session.jsonl
```

## Display Options

### Terminal Width and Wrapping

```bash
# Set custom terminal width
claude-tail --width 120 session.jsonl

# Disable line wrapping
claude-tail --no-wrap session.jsonl

# Combine options
claude-tail --width 80 --no-wrap session.jsonl
```
