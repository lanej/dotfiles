# Jira CLI Command Reference

## Issues

```bash
jira issues search "<jql>" [--max-results N] [--fields f1,f2]
jira issues get PROJ-123
jira issues create --project PROJ --type Bug --summary "Title" \
  [--assignee <user>] [--description <md>] [--priority High] [--labels a,b] [--parent KEY] \
  [--field "Story Points=5"] [--field "Sprint=Sprint 42"]   # repeatable, custom fields by name
jira issues update PROJ-123 [--summary "New title"] [--assignee <user>] \
  [--description <md>] [--priority High] [--labels a,b] \
  [--field "Story Points=8"] [--field "Priority Reason=Blocking"]
jira issues delete PROJ-123
jira issues transitions PROJ-123                       # list available transitions (ID + name)
jira issues transition PROJ-123 "In Progress"         # by name (case-insensitive)
jira issues transition PROJ-123 21                     # by ID
jira issues assign PROJ-123 alice@example.com          # by email
jira issues assign PROJ-123 "Alice Smith"              # by display name
jira issues assign PROJ-123 5b10ac8d82e05b22cc7d4ef5  # by account ID
jira issues assign PROJ-123 ""                         # unassign
jira issues bulk-create --file issues.json
jira issues pull PROJ-123 [file.md]                    # download description to local markdown
jira issues sync file.md                               # push local markdown to Jira description
```

`<user>` accepts email address, display name, or account ID — resolved at call time. Non-unique display names error with a candidate list; use email or account ID for precision.

`--field "Name=Value"` sets custom fields by name. Values are resolved by field type:
- **Number fields**: `"Story Points=5"` → numeric
- **Option/select**: `"Priority Reason=Blocking"` → `{value: "Blocking"}`
- **Multi-select**: `"Tags=bug"` → `[{value: "bug"}]`
- **User fields**: `"Dev Lead=alice@example.com"` → accountId (resolved)
- **Sprint**: `"Sprint=Sprint 42"` → sprint ID (searches all boards; error on non-unique)
- **Unknown types**: passed through as-is, Jira surfaces errors

## Projects

```bash
jira projects list
jira projects get PROJ
jira projects search --query "name"
jira projects create --name "Name" --key PROJ --type software
jira projects update PROJ --name "New Name"
jira projects delete PROJ
```

## Boards

```bash
jira boards list [--max-results N] [--type scrum|kanban]
jira boards get <id>
jira boards get-config <id>
jira boards backlog <id> [--max-results N]
jira boards issues <id> [--max-results N]
jira boards epics <id> [--max-results N]
```

## Sprints

```bash
jira sprints list --board <id> [--state future|active|closed] [--max-results N]
jira sprints get <id>
jira sprints create --board <id> --name "Sprint 1" [--goal "..."] [--start-date ISO] [--end-date ISO]
jira sprints update <id> [--name "..."] [--goal "..."] [--start-date ISO] [--end-date ISO]
jira sprints start <id>
jira sprints complete <id>
```

## Comments

```bash
jira comments list PROJ-123
jira comments get <comment-id>
jira comments create PROJ-123 --body "text"
jira comments update <comment-id> --body "updated"
jira comments delete <comment-id>
```

## Attachments

```bash
jira attachments list PROJ-123
jira attachments get <attachment-id>
jira attachments upload PROJ-123 --file document.pdf
jira attachments download <attachment-id> --output file.pdf
jira attachments delete <attachment-id>
```

## Remote Links

Prefer remote links over attachments for documents — they render as clickable chips with application icons.

```bash
jira remotelinks list PROJ-123
jira remotelinks add PROJ-123 <url> [title]
jira remotelinks delete PROJ-123 <linkId>
```

Google Drive URLs (Docs, Sheets, Folders) are auto-detected and get the correct icon.

## Worklogs

```bash
jira worklogs list PROJ-123
jira worklogs get PROJ-123 <worklog-id>
jira worklogs create PROJ-123 --time-spent "2h" --comment "Work done"
jira worklogs update PROJ-123 <worklog-id> --time-spent "3h"
jira worklogs delete PROJ-123 <worklog-id>
```

## Versions

```bash
jira versions list PROJ
jira versions get <id>
jira versions create --project PROJ --name "v1.0.0"
jira versions update <id> --name "v1.0.1"
jira versions delete <id>
```

## Components

```bash
jira components list PROJ
jira components get <id>
jira components create --project PROJ --name "Backend"
jira components update <id> --name "Frontend"
jira components delete <id>
```

## Fields

```bash
jira fields list
jira fields contexts <field>                           # field name or ID
jira fields options <field> <contextId>
jira fields options-add <field> <contextId> --value "Option A" [--value "Option B"]
jira fields options-update <field> <contextId> --id <optionId> --value "New Value" [--disabled]
```

`<field>` accepts field name (e.g. `"Story Points"`) or field ID (e.g. `customfield_12497`).

## Filters / Dashboards

```bash
jira filters list
jira filters get <id>
jira filters create --name "My Filter" --jql "project = PROJ"
jira filters update <id> --name "Updated"
jira filters delete <id>

jira dashboards list
jira dashboards get <id>
```

## Issue Types / Statuses

```bash
jira issuetypes list
jira issuetypes get <id>
jira issuetypes create --name "Custom Type"
jira issuetypes update <id> --name "Updated"
jira issuetypes delete <id>

jira statuses list
jira statuses get <id>
```

## Issue Links

```bash
jira issuelinks list-types
jira issuelinks get <link-id>
jira issuelinks create --inward-issue PROJ-1 --outward-issue OTHER-2 --link-type "Blocks"
jira issuelinks delete <link-id>
```

## Development Info (GitHub/Bitbucket/GitLab)

Requires numeric issue ID (not key) — see gotchas in SKILL.md.

```bash
jira development summary $ISSUE_ID
jira development commits $ISSUE_ID --application-type github
jira development pull-requests $ISSUE_ID --application-type github
jira development branches $ISSUE_ID --application-type github
```

Supported types: `github`, `bitbucket`, `stash`, `gitlab`

## Plans (Advanced Roadmaps)

```bash
jira plans list
jira plans get <id>
jira plans create --name "My Plan"
jira plans update <id> --name "Updated"
jira plans archive <id>
jira plans delete <id>
jira plans duplicate <id>
jira plans teams-list <id>
```

## Screens

```bash
jira screens list [--max-results N]
jira screens get <id>
jira screens create --name "Screen Name" [--description "..."]
jira screens update <id> [--name "..."] [--description "..."]
jira screens delete <id>
jira screens tabs <id>
jira screens fields <id> <tabId>
```

## Automations

```bash
jira automations list
jira automations get <uuid>
jira automations enable <uuid>
jira automations disable <uuid>
```

## Audit Log

```bash
jira auditlog list [--from ISO] [--to ISO] [--category <category>] [--max-results N]
```

## Users

```bash
jira users list [--max-results N]
jira users get <account-id>
jira users search --query "name"
jira users create --email user@example.com --display-name "Name"
jira users delete <account-id>
```

## Goals

Goals use the Atlassian GraphQL API — not available via MCP.

```bash
jira goals list [--format json]
jira goals get <goalARI>
jira goals list-types [--format json]
jira goals create --name "..." --goal-type-id <ARI> --target-date YYYY-MM-DD [--confidence QUARTER] [--parent-goal-id <ARI>]
jira goals edit <goalARI> --name "New name"
jira goals add-metric <goalARI> --name "Metric" --type NUMERIC --start 0 --value 0 --target 100
jira goals archive <goalARI>
```

## Raw API

```bash
jira api GET /rest/api/3/issue/PROJ-123
jira api POST /rest/api/3/search/jql --data '{"jql":"project=PROJ","fields":["summary"]}'
jira api PUT /rest/api/3/issue/PROJ-123 --data '{"fields":{"summary":"New title"}}'
```

## MCP Server

```bash
jira mcp stdio   # start on stdio for Claude Desktop / MCP clients
```

Claude Desktop config:
```json
{
  "mcpServers": {
    "jira": { "command": "/path/to/jira", "args": ["mcp"] }
  }
}
```
