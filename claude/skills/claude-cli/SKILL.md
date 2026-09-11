---
name: claude-cli
description: Use claude CLI for interactive AI sessions, scripting with print mode, MCP server management, and plugin configuration. Master session management, tool control, and automation workflows.
---

# Claude CLI

`claude --help` and `claude mcp --help` are authoritative for the full flag surface. This file
covers the flags that matter for scripting and the configuration shapes that are easy to get wrong.

## Print mode is the scripting entry point

```bash
claude -p "summarize errors in app.log"
claude -p --output-format json "count TODO comments" | jq -r '.response'
claude -p --output-format stream-json "long task"      # incremental
claude -p --fallback-model haiku "analyze this"        # print mode only
```

`--fallback-model` exists only in print mode — an interactive session has no silent downgrade.

## Sessions

```bash
claude -c                      # continue most recent
claude -r <session-id>         # resume specific (bare -r for a picker)
claude -c --fork-session       # branch without mutating the original
claude --session-id <uuid>     # pin an ID, for scripted runs you need to find later
```

`--fork-session` is the safe way to try a different approach from a known-good point.

## Model selection

Use aliases (`--model sonnet|opus|haiku`) rather than dated full IDs — pinned version strings go
stale and silently fail or resolve to something unintended.

## Tool and permission control

```bash
claude --allowed-tools "Bash(git:*)" -p "show recent commits"
claude --disallowed-tools "Bash(rm:*)" "Bash(mv:*)" "clean project"
claude --permission-mode acceptEdits|plan|bypassPermissions|default
```

`--dangerously-skip-permissions` skips every check — sandboxes only.

## MCP configuration

**Project-scoped servers belong in `.mcp.json` at the project root**, not in user settings:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "package-name"],
      "env": { "API_KEY": "value" }
    }
  }
}
```

Management:

```bash
claude mcp list
claude mcp get <name>
claude mcp remove <name>
claude mcp add --transport stdio|sse|http <name> [--env K=V] -- <command...>
claude mcp add-json <name> '{"command":"node","args":["server.js"]}'
claude mcp add-from-claude-desktop [--name <server>]
claude mcp reset-project-choices        # clear approved/rejected project servers
```

For a run that must use *only* a given config, combine `--mcp-config <file>` with
`--strict-mcp-config` — without the strict flag, the file is merged with existing sources rather
than replacing them.

## Settings precedence

```bash
claude --setting-sources user,project,local
claude --settings /path/to/settings.json
claude --add-dir /data/ /logs/          # grant access outside cwd
```

## Maintenance

`claude doctor` (diagnose the auto-updater), `claude update`, `claude install stable|latest|<ver>`,
`claude setup-token` (long-lived auth for CI), `claude migrate-installer` (global npm → local).
