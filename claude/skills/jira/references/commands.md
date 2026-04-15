# Jira CLI Command Reference

## Issues

```bash
jira issues search "<jql>" [--max-results N] [--fields f1,f2]
jira issues get PROJ-123
jira issues create --project PROJ --type Bug --summary "Title"
jira issues update PROJ-123 --summary "New title"
jira issues delete PROJ-123
jira issues get-transitions PROJ-123
jira issues transition PROJ-123 --transition-id 21
jira issues assign PROJ-123 --account-id <id>
jira issues bulk-create --file issues.json
```

## Projects

```bash
jira projects list
jira projects get PROJ
jira projects search --query "name"
jira projects create --name "Name" --key PROJ --type software
jira projects update PROJ --name "New Name"
jira projects delete PROJ
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

## Users

```bash
jira users list [--max-results N]
jira users get <account-id>
jira users search --query "name"
jira users create --email user@example.com --display-name "Name"
jira users delete <account-id>
```

## Raw API

```bash
jira api GET /rest/api/3/issue/PROJ-123
jira api POST /rest/api/3/issue --body '{"fields":{"summary":"Test"}}'
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
