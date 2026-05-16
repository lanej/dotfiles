---
name: jira
description: Use jira CLI and MCP tools (mcp__jira__*) for Jira Cloud operations — issue management, project queries, JQL search, transitions, worklogs, plans, and more. Use when working with Jira issues, projects, sprints, boards, filters, dashboards, or any Jira Cloud resource via CLI or MCP.
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

## CLI vs MCP

**The CLI is the full interface. MCP tools are a subset.**

Most resources and verbs are only available via CLI. MCP exposes the most common read/write operations but does not cover: bulk operations, boards, sprints, development info, goals, screens, automations, audit log, or raw API access.

**Default to CLI** (`jira <resource> <verb>`) for any operation not explicitly listed in an MCP tool. Use MCP when an agent needs structured tool call semantics or is already in an MCP session.

All resources follow: `jira <resource> <verb> [args] [flags]`

Resources: `issues`, `projects`, `comments`, `attachments`, `worklogs`, `versions`, `components`, `filters`, `dashboards`, `issuetypes`, `statuses`, `issuelinks`, `remotelinks`, `development`, `plans`, `users`, `boards`, `sprints`, `fields`, `goals`, `screens`, `automations`, `auditlog`

Read `references/commands.md` for exact flags and syntax for every resource.

## Name Resolution

All parameters that previously required opaque IDs now accept human-readable names. Resolution is case-insensitive exact match; IDs pass through unchanged.

| Parameter | Accepts |
|---|---|
| `transition` (issues transition) | transition name or ID |
| `user` / `accountId` / `assigneeAccountId` / `leadAccountId` | email, display name, or account ID |
| `fieldId` (fields commands) | field name (e.g. `"Story Points"`) or ID (e.g. `customfield_12497`) |
| `--field "Name=Value"` / `customFields` on create & update | field name as key; value resolved by type (see below) |

**Custom field value resolution** (`--field` on CLI, `customFields` on MCP):
Keys are resolved from field name → `customfield_*`. Values are resolved by field type:
option names → `{value}`, user names/emails → accountId, sprint names → sprint ID (all boards searched), numbers parsed from strings. Unknown types pass through; Jira surfaces errors.

**Sprint name lookup** searches all boards — may be slow on large instances. Error on non-unique sprint names across boards.

**Non-unique match errors.** If a name matches 2+ candidates, the call fails with a list of all matches and their IDs. Use an ID to be precise.

**User resolution fallback.** If `searchUsers(query)` returns no results, the value is treated as a raw account ID. Empty string always passes through (used to unassign).

## Critical Gotchas

**204 empty response ≠ error.** Mutating operations (assign, transition, delete) return HTTP 204. The MCP layer may surface this as an error. Always verify with a GET:

```
mcp__jira__jira_issues_assign(key="PROJ-1", user="alice@example.com")
issue = mcp__jira__jira_issues_get(key="PROJ-1")   # verify assignee
```

**Development API needs numeric ID.** `jira development *` and `mcp__jira__jira_development_summary` require the internal numeric issue ID, not the key:

```bash
ISSUE_ID=$(jira issues get PROJ-123 --format json | jq -r '.id')
jira development pull-requests $ISSUE_ID --application-type github
```

**MCP returns minimal fields by default** (~70% token reduction). Use `fields` param to request additional data.

**Goals field cannot be set via REST API.** `customfield_10025` returns `204 No Content` but the field is never updated — `/editmeta` exposes `allowedValues: []`. Known bug: [JRACLOUD-97866](https://jira.atlassian.com/browse/JRACLOUD-97866). Link issues to goals through the Jira UI only.

## Issue Sync (Markdown ↔ Jira)

Keep a local `.md` file in sync with a Jira issue description — same pattern as `gspace docs sync`.

```bash
jira issues pull PROJ-123 [file.md]   # download description → local file (default: PROJ-123.md)
jira issues sync file.md              # push local file → Jira description
```

**File format** — YAML frontmatter + markdown body:
```markdown
---
jira:
  key: PROJ-123
  url: https://yourorg.atlassian.net/browse/PROJ-123
  updated: "2026-05-13T08:00:00.000+0000"
---

Description body goes here.
```

**Conflict detection**: `sync` compares `jira.updated` against the remote timestamp. If remote is more than 60s newer, aborts with a message and suggests `pull` to refresh. **Any Jira API operation that touches a ticket** (MCP link create/delete, `jira_issues_update`, `jira_issues_transition`) updates the remote `updated` timestamp — triggering a conflict on the next sync. Resolution: `jira issues pull <KEY> <file.md>` to refresh the local timestamp, then re-render and sync.

**File locking**: both commands acquire `file.md.lock` before any I/O. Stale locks (>60s) are overridden with a warning.

**Local images**: `![alt](./local.png)` in the markdown body is base64-encoded and embedded in the ADF on sync. On pull, base64 data URLs are decoded to `./images/{KEY}-img-{n}.png` and referenced as relative paths.

**What syncs**: description only. Summary, status, assignee, labels are Jira-managed and not written to the file.

**Known limitations**:
- `code` mark cannot be combined with other marks (bold/italic) — ADF spec constraint, Jira rejects it
- Round-trip introduces minor whitespace differences in tables and blockquotes
- Nested bold+italic (`**bold _italic_**`) emits redundant `**` on pull — cosmetic, content preserved

## Issue Links vs. Inline Hyperlinks

These are distinct operations — do not conflate them:

- **Inline hyperlink in prose**: `[EP-23](https://simplerpostage.atlassian.net/browse/EP-23)` in a description body. Use when the text *references* another ticket. This is what "link to a Jira ticket" means in the context of writing or editing a description.
- **Issue link edge**: a structural relationship (Blocks, Relates, Cloners) created via `jira issuelinks create` or `mcp__jira__jira_issuelinks_create`. Use only when explicitly asked to set a dependency or relationship between tickets.

When asked to "link to EP-XX" or "reference EP-XX" while working on a description, use the inline hyperlink. Only create an issue link edge when the request is explicitly about ticket relationships.

## Linking Documents to Issues

**Always use remote links, never file attachments.** File attachments do not render correctly in Jira — they appear as raw downloads. Remote links render as clickable chips with the correct application icon.

Google Drive URLs are auto-detected: Docs, Sheets, and Folders each get the correct icon. Non-Google URLs are linked as generic web links.

**Never use `jira attachments upload` for documents** — use `jira remotelinks add` instead. See `references/commands.md` for syntax.

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

# List active sprint issues on a board
BOARD_ID=$(jira boards list --format jsonl | jq -r 'select(.name=="My Board") | .id')
jira sprints list --board $BOARD_ID --state active --format jsonl \
  | jq -r '.id' \
  | xargs -I{} jira issues search "sprint = {}" --format jsonl
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

Goals use a separate `jira goals` command group backed by the Atlassian GraphQL API — not Jira REST. Goal type ARIs are workspace-specific; run `jira goals list-types` to get them.

**Hierarchy:** Two levels only: `GOAL` → `SUCCESS_MEASURE`. A `SUCCESS_MEASURE` cannot have children.

See `references/commands.md` for full goal command syntax.

## Raw API Access

```bash
jira api GET  "/rest/api/3/issue/PROJ-123?fields=summary,status"
jira api POST "/rest/api/3/search/jql" --data '{"jql":"project=PROJ","fields":["summary"]}'
jira api PUT  "/rest/api/3/issue/PROJ-123" --data '{"fields":{"summary":"New title"}}'
```

**Gotcha:** `/rest/api/3/search` is removed — use `POST /rest/api/3/search/jql` with body `{"jql":"...","fields":[...],"maxResults":50}`.
