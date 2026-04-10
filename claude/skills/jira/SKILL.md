---
name: jira
description: Use jira CLI and MCP tools (mcp__jira__*) for Jira Cloud operations — issue management, project queries, JQL search, transitions, worklogs, plans, and more. Use when working with Jira issues, projects, sprints, filters, dashboards, or any Jira Cloud resource via CLI or MCP.
---
# Jira CLI & MCP Server

## Configuration

```bash
jira config init      # interactive setup → ~/.config/jira-cli/config.toml
jira config validate  # test connection
```

**No env vars.** `JIRA_URL` / `JIRA_EMAIL` / `JIRA_API_TOKEN` are intentionally ignored. Use CLI flags `--url`/`--email`/`--token` for one-off overrides.

## Output Formats

```
--format table    # default
--format json     # array
--format jsonl    # one object per line, auto-paginates all results
```

JSONL is preferred for scripting — pipe directly to `jq`.

## CLI Command Pattern

All resources follow: `jira <resource> <verb> [args] [flags]`

Resources: `issues`, `projects`, `comments`, `attachments`, `worklogs`, `versions`, `components`, `filters`, `dashboards`, `issuetypes`, `statuses`, `issuelinks`, `remotelinks`, `development`, `plans`, `users`

For full command reference: see `references/commands.md`.

## Critical Gotchas

**204 empty response ≠ error.** Mutating operations (assign, transition, delete) return HTTP 204. The MCP layer may surface this as an error. Always verify with a GET:

```
mcp__jira__jira_issues_assign(issue_key, account_id)
issue = mcp__jira__jira_issues_get(issue_key)   # verify assignee
```

**Users require account_id.** Display names don't work for assignment. Lookup pattern:

```
1. mcp__jira__jira_users_search(query="Name")
2. extract account_id
3. mcp__jira__jira_issues_assign(issue_key, account_id)
```

**Development API needs numeric ID.** `jira development *` and `mcp__jira__jira_development_summary` require the internal numeric issue ID, not the key:

```bash
ISSUE_ID=$(jira issues get PROJ-123 --format json | jq -r '.id')
jira development pull-requests $ISSUE_ID --application-type github
```

**MCP returns minimal fields by default** (~70% token reduction). Use `fields` param to request additional data.

## Linking Documents to Issues

**Always use remote links, never file attachments.** File attachments do not render correctly in Jira — they appear as raw downloads. Remote links render as clickable chips with the correct application icon.

```bash
# Link a Google Doc (renders with Docs icon)
jira remotelinks add PROJ-123 "https://docs.google.com/document/d/..." "Doc Title"

# Link a Google Sheet (renders with Sheets icon)
jira remotelinks add PROJ-123 "https://docs.google.com/spreadsheets/d/..." "Sheet Title"

# Link a Google Drive folder
jira remotelinks add PROJ-123 "https://drive.google.com/drive/folders/..." "Folder Title"

# List remote links on an issue
jira remotelinks list PROJ-123

# Delete a remote link
jira remotelinks delete PROJ-123 <linkId>
```

Google Drive URLs are auto-detected: Docs, Sheets, and Folders each get the correct icon and application type. Non-Google URLs are linked as generic web links.

**Never use `jira attachments upload` for documents** — use `jira remotelinks add` instead.

## Common Patterns

```bash
# Search + stream to jq
jira issues search "project = PROJ AND status = Open" --format jsonl | jq '.fields.status.name'

# Count by status
jira issues search "project = PROJ" --format jsonl \
  | jq -r '.fields.status.name' | sort | uniq -c | sort -rn

# Extract issue link edges (for dependency graphs)
jira issues search "issuelinktype is not EMPTY" --fields issuelinks --format jsonl \
  | jq -r '.key as $k | .fields.issuelinks[]? |
      if .outwardIssue then "\($k),\(.type.outward),\(.outwardIssue.key)"
      else "\(.inwardIssue.key),\(.type.inward),\($k)" end'
```

## JQL Quick Reference

```
assignee = currentUser() AND status != Done
updated >= -7d ORDER BY updated DESC
type = Bug AND priority in (Highest, High)
sprint in openSprints() AND project = PROJ
issuelinktype is not EMPTY AND project = PROJ
```

## Goals (jira goals CLI — not available via MCP)

Goals use a separate `jira goals` command group backed by the Atlassian GraphQL API.

```bash
jira goals list --format json                          # list all goals
jira goals get <goalARI>                               # get goal details
jira goals list-types --format json                    # show available goal types (workspace-specific ARIs)

# Create a top-level Goal
jira goals create --name "My Goal" \
  --goal-type-id <GOAL-type-ARI> \
  --target-date 2026-12-31 --confidence QUARTER

# Create a child Success Measure under a parent Goal
jira goals create --name "My Success Measure" \
  --goal-type-id <SUCCESS_MEASURE-type-ARI> \
  --parent-goal-id <parent-goal-ARI> \
  --target-date 2026-09-30

# Add a metric to a goal
jira goals add-metric <goalARI> \
  --name "Metric name" --type NUMERIC \
  --start 0 --value 0 --target 100

# Rename a goal
jira goals edit <goalARI> --name "New name"

# Archive a goal
jira goals archive <goalARI>
```

**Hierarchy rules:**
- Two levels only: `GOAL` → `SUCCESS_MEASURE`
- `SUCCESS_MEASURE` cannot have children
- Goal type ARIs are workspace-specific — use `jira goals list-types` to get them

**Linking goals to issues:**
- The Goals field on issues is `customfield_10025`
- Cannot be set via the Jira REST API — every attempt clears the field
- Link issues to goals through the **Jira UI** only

## Raw API Access

```bash
jira api GET  "/rest/api/3/issue/PROJ-123?fields=summary,status"
jira api POST "/rest/api/3/search/jql" --data '{"jql":"project=PROJ","fields":["summary"]}'
jira api PUT  "/rest/api/3/issue/PROJ-123" --data '{"fields":{"summary":"New title"}}'
```

**Gotcha:** `/rest/api/3/search` is removed — use `POST /rest/api/3/search/jql` with body `{"jql":"...","fields":[...],"maxResults":50}`.
