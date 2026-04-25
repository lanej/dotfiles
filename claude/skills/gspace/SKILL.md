---
name: gspace
description: "Load for any Google Workspace operation — Drive, Docs, Gmail, Calendar, Sheets, or other Google services — or when a Google URL or file ID is present."
---

# gspace — Google Workspace CLI and MCP

Every MCP tool has a matching CLI command. Use CLI for interactive/scripted work; use MCP tools when operating as an agent.

## Authentication

```bash
gspace auth check        # verify auth state and scopes
gcloud auth login --enable-gdrive-access
```

Required scopes: `cloud-platform`, `drive` (full, not readonly).

## Domain References

For detailed CLI/MCP reference and gotchas, read the relevant file with the Read tool:

| Domain | File | Covers |
|--------|------|--------|
| Docs | `~/.claude/skills/gspace/references/docs.md` | Create/update/download Docs from Markdown, stylesheets, frontmatter |
| Drive | `~/.claude/skills/gspace/references/drive.md` | Files, folders, revisions, upload/download, export formats, comments |
| Gmail | `~/.claude/skills/gspace/references/gmail.md` | Search, send, draft, thread, labels, filters, Drive chips |
| Calendar | `~/.claude/skills/gspace/references/calendar.md` | Events, availability, free/busy |
| Sheets | `~/.claude/skills/gspace/references/sheets.md` | Read/write spreadsheet data |
| People | `~/.claude/skills/gspace/references/people.md` | Personal contacts CRUD and photo update |
| Groups | `~/.claude/skills/gspace/references/groups.md` | Org-wide Cloud Identity Groups and membership |
| Permissions | `~/.claude/skills/gspace/references/permissions.md` | Drive file/folder sharing |
| Chat | `~/.claude/skills/gspace/references/chat.md` | Spaces, members, messages |
| Tasks | `~/.claude/skills/gspace/references/tasks.md` | Task lists and tasks |
| Forms | `~/.claude/skills/gspace/references/forms.md` | Form structure and responses |
| Meet | `~/.claude/skills/gspace/references/meet.md` | Conferences, recordings, transcripts |
| Slides | `~/.claude/skills/gspace/references/slides.md` | Presentation and slide metadata |

## Global Patterns

**URL transparency** — all commands accepting a file ID also accept full Google URLs.

**MCP write gate** — when `GSPACE_NTFY_TOPIC` is set, write operations block for ntfy approval.

**Service filtering** — `gspace mcp stdio --only <service>` or `--without <service>`.

**Output format** — all CLI commands accept `--format json`.

## Key Rules

- **Markdown → Google Doc**: use `docs_create` / `gspace docs create`, never `drive_files_upload --convert`
- **Edit a doc**: always `docs_download` first (writes to `local_path`), then edit, then `docs_sync` — never blind-write
- **Gmail subjects**: ASCII only — em dashes and smart quotes get mangled
- **Drive export**: `xlsx` preserves multiple sheets; `csv` exports first sheet only
- **Gmail HTML body**: pass `--html` flag to `send` and `draft` commands to use HTML body (required for embedded Drive chips)
- **Gmail compose from markdown**: `gspace gmail compose <file.md>` reads frontmatter for headers, renders body to HTML, sends as multipart; `gmail_send` accepts `body_markdown` for server-side render
