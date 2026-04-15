---
name: zendesk
description: Use zendesk CLI and MCP tools for Zendesk Support operations — ticket management, search, bulk export, users, organizations, knowledge base articles, and attachments. Use when working with Zendesk tickets, querying support data, exporting ticket history, or integrating Zendesk into AI workflows via MCP.
---
# Zendesk CLI Skill

You are a Zendesk workflow specialist using the `zendesk` CLI tool and MCP server. This skill covers ticket management, search, bulk export, users, organizations, knowledge base, and MCP integration.

## Configuration

Credential precedence: CLI flags > environment variables > config file (`~/.zendesk.json` or `.zendesk.json`)

```bash
# Environment variables
export ZENDESK_SUBDOMAIN="your-subdomain"
export ZENDESK_EMAIL="your@email.com"    # Defaults to git config user.email
export ZENDESK_TOKEN="your-api-token"    # Also accepts ZENDESK_API_KEY

# Config file (~/.zendesk.json)
{
  "subdomain": "your-subdomain",
  "email": "your@email.com",
  "token": "your-api-token"
}

# CLI flags (global, available on all subcommands)
zendesk --subdomain foo --email me@foo.com --token TOKEN <command>
```

## Output Formats

All collection commands support three output modes:

| Flag | Format | Best for |
|------|--------|---------|
| (default) | Markdown table | Human reading |
| `--json` | JSON array/object | One-shot programmatic use |
| `--jsonl` | JSONL (streaming) | Pipelines, large result sets |
| `--pretty` | Pretty-print JSON | Debugging |

Single-resource commands (view/get) default to markdown, support `--json`.

**JSONL is preferred** for pipelines and large datasets — it streams paginated results without buffering.

## Ticket Commands

### View a ticket

```bash
zendesk ticket view <id>
zendesk ticket view 12345 --json
```

### List tickets

```bash
# Default: markdown table, page 1, 25/page
zendesk ticket list

# Filters
zendesk ticket list --status open
zendesk ticket list --status open pending
zendesk ticket list --assignee-id 123
zendesk ticket list --requester-id 456
zendesk ticket list --sort-by updated_at --sort-order desc
zendesk ticket list --page 2 --per-page 50

# Streaming (all pages, no limit)
zendesk ticket list --jsonl | jq -c 'select(.status == "open")'

# Limit total results
zendesk ticket list --jsonl --limit 100
```

**Sort fields**: `created_at`, `updated_at`, `priority`, `status`

### Search tickets (Zendesk query syntax)

```bash
# Zendesk query syntax examples
zendesk ticket search "status:open"
zendesk ticket search "assignee:me type:ticket"
zendesk ticket search "created>2024-01-01 tags:escalated"
zendesk ticket search "requester:user@example.com status:pending"
zendesk ticket search "priority:urgent -status:solved"

# Stream all results (no pagination limit)
zendesk ticket search "status:open" --jsonl | wc -l

# Limit results
zendesk ticket search "status:open" --jsonl --limit 500
```

**Zendesk query syntax reference:**
- `field:value` — exact match
- `field>value` / `field<value` / `field>=value` — range (dates, numbers)
- `-field:value` — negation
- `"multi word"` — phrase match
- Fields: `status`, `priority`, `type`, `assignee`, `requester`, `group`, `tags`, `created`, `updated`, `solved`, `due_date`, `organization`

### Ticket comments

```bash
zendesk ticket comments <id>
zendesk ticket comments 12345 --json
zendesk ticket comments 12345 --jsonl
```

### Ticket attachments

```bash
zendesk ticket attachments <id>
zendesk ticket attachments 12345 --json
```

### Bulk export (incremental)

The `export` command uses Zendesk's incremental export API for full ticket history. Results are sorted newest-first.

```bash
# Export all tickets to stdout (JSONL)
zendesk ticket export

# Export to file
zendesk ticket export --output tickets.jsonl

# Export with comments (slower — ~600 req/min due to rate limits)
zendesk ticket export --output tickets.jsonl --include-comments

# Export with progress bar
zendesk ticket export --output tickets.jsonl --progress

# Verbose progress (shows rate, ETA, stats)
zendesk ticket export --output tickets.jsonl --verbose

# Export from timestamp (Unix epoch)
zendesk ticket export --start-time 1704067200  # 2024-01-01

# Exclude deleted tickets
zendesk ticket export --exclude-deleted

# Resume interrupted export (appends to file, skips already-exported IDs)
zendesk ticket export --output tickets.jsonl --resume

# Limit export size (useful for sampling)
zendesk ticket export --limit 10000 --output sample.jsonl

# Control concurrency for comment fetches
zendesk ticket export --include-comments --concurrency 10

# Adjust API page size (max 1000)
zendesk ticket export --per-page 1000
```

**Export + DuckDB workflow:**

```bash
zendesk ticket export --output tickets.jsonl --progress
duckdb -c "SELECT status, COUNT(*) FROM read_json_auto('tickets.jsonl') GROUP BY status"
duckdb -c "SELECT * FROM read_json_auto('tickets.jsonl') WHERE priority = 'urgent'"
```

## User Commands

```bash
# Get a single user
zendesk user get <id>
zendesk user get 123 --json

# Get multiple users by ID
zendesk user list 123 456 789
zendesk user list 123 456 --json
zendesk user list 123 456 --jsonl
```

## Organization Commands

```bash
# Get a single organization
zendesk org get <id>
zendesk org get 456 --json

# Get multiple organizations by ID
zendesk org list 456 789
zendesk org list 456 789 --json
zendesk org list 456 789 --jsonl
```

## Ticket Field Commands

```bash
# List all ticket fields
zendesk field list
zendesk field list --json
zendesk field list --jsonl

# Get a specific ticket field
zendesk field get <id>
zendesk field get 12345 --json
```

## Tag Commands

```bash
# List all tags
zendesk tag list
zendesk tag list --json
zendesk tag list --jsonl
```

## Article (Knowledge Base) Commands

```bash
# Search articles
zendesk article search "password reset"
zendesk article search "shipping policy" --json

# View a specific article
zendesk article view <id>
zendesk article view 360001234567 --json
```

## Attachment Commands

```bash
# Get attachment metadata
zendesk attachment get <id>
zendesk attachment get 789 --json

# Download an attachment to file
zendesk attachment download <url> --output ./downloads/file.pdf
```

## MCP Server

Start the Zendesk MCP server for AI integration:

```bash
zendesk mcp stdio
```

### Claude Code configuration (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "zendesk": {
      "command": "zendesk",
      "args": ["mcp", "stdio"],
      "env": {
        "ZENDESK_SUBDOMAIN": "your-subdomain",
        "ZENDESK_EMAIL": "your@email.com",
        "ZENDESK_TOKEN": "your-api-token"
      }
    }
  }
}
```

### MCP Tools Available

**Ticket tools:**
- `get_ticket` — retrieve a ticket by ID
- `get_tickets` — list tickets with pagination and filters
- `create_ticket` — create a new ticket (supports custom fields)
- `update_ticket` — update an existing ticket (supports custom fields)
- `search_tickets` — search using Zendesk query syntax
- `get_ticket_comments` — get all comments for a ticket
- `create_ticket_comment` — add a comment to a ticket
- `get_ticket_attachments` — get attachments for a ticket
- `download_attachment` — download an attachment by URL
- `get_ticket_fields` — list all ticket field definitions
- `get_ticket_field` — get a specific ticket field

**User/org tools:**
- `get_user` — get a user by ID
- `get_users` — get multiple users by IDs
- `get_organization` — get an organization by ID
- `get_organizations` — get multiple organizations by IDs

**Knowledge base tools:**
- `search_articles` — search knowledge base articles
- `get_article` — get a specific article by ID
- `get_articles_by_section` — list articles in a section

**Other tools:**
- `list_tags` — list all tags

### Custom Fields (create/update)

```json
{
  "ticket_id": 123,
  "custom_fields": {
    "12345678": "Production",
    "87654321": "Critical"
  }
}
```

Custom field IDs are numeric strings matching Zendesk ticket field IDs. Use `zendesk field list` to discover available fields and their IDs.

## Common Workflows

### Workflow 1: Investigate a ticket

```bash
# Get full ticket details
zendesk ticket view 12345

# Get all comments
zendesk ticket comments 12345

# Get attachments
zendesk ticket attachments 12345

# Download an attachment
zendesk attachment download <url> --output ./attachment.pdf
```

### Workflow 2: Find tickets matching criteria

```bash
# Search with query syntax
zendesk ticket search "status:open assignee:me priority:urgent"

# Stream all open tickets for analysis
zendesk ticket search "status:open" --jsonl > open_tickets.jsonl
duckdb -c "SELECT assignee_id, COUNT(*) FROM read_json_auto('open_tickets.jsonl') GROUP BY assignee_id ORDER BY COUNT(*) DESC"
```

### Workflow 3: Bulk export for analysis

```bash
# Full export with progress
zendesk ticket export --output all_tickets.jsonl --progress

# Export last 30 days
SINCE=$(date -d '30 days ago' +%s 2>/dev/null || date -v-30d +%s)
zendesk ticket export --start-time $SINCE --output recent.jsonl --progress

# Export with comments for full context
zendesk ticket export --output full.jsonl --include-comments --verbose

# Resume if interrupted
zendesk ticket export --output all_tickets.jsonl --resume --progress
```

### Workflow 4: Resolve user/org context

```bash
# Get user details from a ticket's requester_id
zendesk user get 987654

# Look up org for multiple users
zendesk user list 111 222 333 --json | jq '.[].organization_id'
zendesk org list 444 --json
```

### Workflow 5: Discover custom fields

```bash
# List all ticket fields to find IDs
zendesk field list --json | jq '.[] | {id: .id, title: .title, type: .type}'

# Find a specific field
zendesk field list --jsonl | jq -c 'select(.title | test("product"; "i"))'
```

### Workflow 6: Knowledge base lookup

```bash
# Search for articles on a topic
zendesk article search "API rate limits" --json | jq '.[].title'

# View a specific article
zendesk article view 360001234567
```

## Quick Reference

```bash
# Tickets
zendesk ticket view <id>
zendesk ticket list [--status open] [--assignee-id N] [--jsonl]
zendesk ticket search "<query>" [--jsonl] [--limit N]
zendesk ticket comments <id>
zendesk ticket attachments <id>
zendesk ticket export [--output file.jsonl] [--include-comments] [--resume] [--progress]

# Users / Orgs
zendesk user get <id>
zendesk user list <id1> <id2> ...
zendesk org get <id>
zendesk org list <id1> <id2> ...

# Fields / Tags
zendesk field list [--json]
zendesk field get <id>
zendesk tag list [--json]

# Articles
zendesk article search "<query>"
zendesk article view <id>

# Attachments
zendesk attachment get <id>
zendesk attachment download <url> --output <file>

# MCP
zendesk mcp stdio
```

## Output Format Selection

- **Default (markdown)**: terminal inspection, human reading
- **`--json`**: structured output; pipe to `jq` for transformation
- **`--jsonl`**: streaming; preferred for large result sets, DuckDB ingestion, pipelines

```bash
# jq on JSON output
zendesk ticket list --json | jq '.tickets[] | select(.priority == "urgent") | .id'

# Stream to DuckDB
zendesk ticket search "status:open" --jsonl | \
  duckdb -c "SELECT group_id, COUNT(*) as n FROM read_json_auto('/dev/stdin') GROUP BY group_id ORDER BY n DESC"
```
