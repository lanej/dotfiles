---
name: gspace
description: Use gspace CLI and MCP tools for Google Workspace operations (Drive, Gmail, Docs, Sheets, Calendar, Tasks). Use when working with Google Workspace URLs (docs.google.com, drive.google.com, sheets.google.com, slides.google.com, mail.google.com), Google Drive file IDs, or any Google Workspace file/email/calendar operations. Supports both CLI commands (via Bash) and MCP tools (mcp__gspace__*).
---
# gspace

CLI (`gspace`) and MCP tools (`mcp__gspace__*`) for Google Workspace. Both interfaces call the same service layer — use whichever fits the task.

## MCP vs CLI

Prefer **MCP tools** (`mcp__gspace__*`) for direct operations in conversation — no subprocess overhead, structured JSON responses.

Use **CLI** (`gspace` via Bash) for shell pipelines, batch loops, or when MCP isn't available.

## Authentication

```bash
gspace auth check          # verify scopes
gspace auth login          # interactive (browser)
```

Requires `gcloud auth login --enable-gdrive-access`. Full `drive` scope needed (not `drive.readonly`) — readonly causes 403 on downloads.

## Key Gotchas

**Gmail web URLs are not API IDs.** URLs like `https://mail.google.com/mail/u/0/#inbox/FMfcgzQ...` use Gmail's internal web format, incompatible with the Gmail API. Use search instead:
```bash
gspace gmail thread --search "from:sender@example.com subject:topic"
# MCP: mcp__gspace__gmail_thread(search_query="from:sender@example.com subject:topic")
```
Only `#search/` Gmail URLs work directly (those fragments are API message IDs).

**Non-ASCII in email subjects gets mangled.** Use ASCII only: hyphens not em dashes, straight quotes not smart quotes.

**Excel exports:** `xlsx` preserves all sheets; `csv` exports only the first sheet.

## URL Parsing

CLI commands and MCP tools accept full Google URLs or raw IDs interchangeably:
- Drive/Docs/Sheets/Slides: `https://docs.google.com/document/d/FILE_ID/edit`
- Gmail `#search/` only: `https://mail.google.com/mail/u/0/#search/query/MESSAGE_ID`

## Reference Files

Load these when working with a specific service:

- **[references/gmail.md](references/gmail.md)** — search, thread lookup, send, labels, filters, attachments
- **[references/drive.md](references/drive.md)** — files, folders, docs, sheets, permissions, revisions, exports
- **[references/calendar.md](references/calendar.md)** — events, search, availability, reminders
- **[references/other-services.md](references/other-services.md)** — Tasks, People/Contacts, Slides, Forms, Meet, Chat, Groups
