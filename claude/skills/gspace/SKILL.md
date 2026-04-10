---
name: gspace
description: "Google Workspace via CLI and MCP tools. Use for Drive, Docs, Gmail, Calendar, Sheets, Slides, Forms, Meet, Chat, Groups, People, and Permissions. Auto-loads for Google URLs/file IDs."
license: Proprietary
---

# gspace — Google Workspace CLI and MCP

## Overview

`gspace` is a CLI and MCP server for Google Workspace. Every MCP tool has a matching CLI command. Use CLI for interactive/scripted work; use MCP tools when operating as an agent.

## Authentication

```bash
gspace auth check        # verify auth state and scopes
gcloud auth login --enable-gdrive-access
```

## Docs Commands

### Creating a new doc

**CLI:**
```bash
gspace docs create "Document Name" /tmp/doc.md
gspace docs create "Document Name" /tmp/doc.md --folder-id <folder_id>
```

**MCP:** `docs_create` — pass `name` and `content` (Markdown string). Returns `{ id, name, url }`.

Always include `title:` and `subtitle:` in YAML frontmatter. **Do not use `drive_files_upload` with `convert_to_google_format` for Markdown files** — it bypasses pandoc and produces stock Google styles without the reference stylesheet.

### Reading a doc

**CLI:**
```bash
gspace docs download <file_id_or_url> /tmp/doc.md
```

**MCP:** `docs_download` — returns Markdown content inline. Always call this before `docs_update` so you have the current content and `gspace:` frontmatter.

### Writing a doc

**CLI:**
```bash
gspace docs update <file_id_or_url> /tmp/doc.md
```

**MCP:** `docs_update` — accepts Markdown string. Replaces the entire document via DOCX intermediary (pandoc → DOCX → Drive). Preserves Google Docs native styles.

### Editing interactively

```bash
gspace docs edit <file_id_or_url>           # opens $EDITOR
gspace docs edit <file_id_or_url> --editor nvim
```

Includes optimistic locking: aborts upload if the doc was modified remotely while you were editing. Your changes are preserved to `/tmp/gspace-edit-{id}.md` on conflict.

### Find and replace

```bash
gspace docs find-replace <file_id> "old" "new"
gspace docs find-replace <file_id> "Old" "New" --match-case
```

MCP: `docs_find_replace`

## YAML Frontmatter

All downloaded Markdown includes a YAML frontmatter block. **Always preserve and pass it through when writing back.**

### gspace: metadata block

Injected automatically on download. Used for optimistic locking and editor context. **Stripped automatically before upload — do not remove it manually.**

```yaml
---
title: My Document Title
subtitle: Optional subtitle
gspace:
  file_id: 1abc...xyz
  name: filename-in-drive
  url: https://docs.google.com/document/d/1abc...xyz/edit
  revision: kDwGh3...
  downloaded_at: '2026-04-10T17:00:00Z'
---
```

### Document metadata fields

These map to Google Docs paragraph styles and should be set explicitly:

| Field | Google Docs style | Notes |
|-------|-------------------|-------|
| `title:` | Title | Always set. Renders as the document title style (large, top of doc) |
| `subtitle:` | Subtitle | Set when the doc has a subtitle. Renders below the title |

**Always encourage setting `title:` and `subtitle:` when creating or updating docs.** A doc without a title uses whatever the first heading is, which often looks wrong.

### Example: well-formed document

```markdown
---
title: Q1 Shipping Performance Report
subtitle: EasyPost Analytics · April 2026
gspace:
  file_id: 1abc...xyz
  name: q1-shipping-report
  url: https://docs.google.com/document/d/1abc...xyz/edit
  revision: kDwGh3...
  downloaded_at: '2026-04-10T17:00:00Z'
---

## Executive Summary

...
```

## Supported Markdown Elements

All elements round-trip cleanly through DOCX:

- Headings (`#` → `######`) — map to Heading 1–6 styles
- **Bold**, *italic*, ***bold italic***, `inline code`
- Bullet lists (`-`) and numbered lists (`1.`) including nested
- Fenced code blocks (``` ``` ```) — rendered with Courier New, gray background
- Blockquotes (`>`)
- Tables with borders
- [Hyperlinks](url)

**Not supported:** Google Docs native code blocks (Insert → Building blocks), pageless mode (Google API limitation tracked in [Issue #26](https://issuetracker.google.com/issues/227875469)).

## Drive Commands

```bash
# Files
gspace drive files list
gspace drive files search "query"
gspace drive files download <id> /tmp/out.md --export markdown
gspace drive files upload /tmp/file.docx "Name" --convert   # NOT for .md files — use docs create
gspace drive files upsert /tmp/file.docx "Name"             # NOT for .md files — use docs update
gspace drive files metadata <id>
gspace drive files copy <id> "New Name"
gspace drive files rename <id> "New Name"
gspace drive files delete <id>

# Folders
gspace drive folders create "Name"
gspace drive folders move <file_id> <folder_id>

# Revisions
gspace drive revisions list <id>
gspace drive revisions get <id> <revision_id>
```

Export formats: `markdown`, `text`, `html`, `pdf`, `docx`, `xlsx`, `csv`

## Gmail Commands

```bash
gspace gmail search "from:user@example.com subject:report"
gspace gmail get <message_id>
gspace gmail thread <thread_id>
gspace gmail send --to user@example.com --subject "Subject" --body "Body"
gspace gmail archive <id>
gspace gmail labels list
```

**Subject line note:** Use ASCII only in subjects — em dashes and smart quotes get mangled.

## Calendar Commands

```bash
gspace calendar list
gspace calendar search "meeting"
gspace calendar today
gspace calendar create --summary "Meeting" --start "2026-04-10T10:00:00" --end "2026-04-10T11:00:00"
gspace calendar find-availability --calendars user@example.com --duration 60
```

## MCP Tool Reference

### Docs

| Tool | Description |
|------|-------------|
| `docs_create` | Create a new Google Doc from Markdown. Use instead of `drive_files_upload` for Markdown. |
| `docs_download` | Download doc as Markdown (inline, no file path). Read before writing. |
| `docs_update` | Replace doc content with Markdown. Strips gspace: block automatically. |
| `docs_find_replace` | Find and replace text. Use for surgical edits. |

### Drive

| Tool | Description |
|------|-------------|
| `drive_files_list` | List files in a folder |
| `drive_files_search` | Search by name or content |
| `drive_files_download` | Download to local path with export format |
| `drive_files_upload` | Upload file, optionally converting to Google format. **Not for Markdown** — use `docs_create`. |
| `drive_files_upsert` | Upload, replacing existing file by name (preserves ID). **Not for Markdown** — use `docs_update`. |
| `drive_files_metadata` | Get file metadata including headRevisionId |
| `drive_files_copy` | Copy a file |
| `drive_files_rename` | Rename a file |
| `drive_files_delete` | Delete a file |
| `drive_folders_create` | Create a folder |
| `drive_folders_move` | Move file to folder |
| `drive_revisions_list` | List file revisions |
| `drive_revisions_get` | Get a specific revision |

## Agent Workflow: Read → Edit → Write

When asked to update a Google Doc:

1. `docs_download` → read current content and frontmatter
2. Edit the Markdown (preserve `gspace:` block and `title:`/`subtitle:` fields)
3. `docs_update` → write back

```
docs_download(file_id="1abc...") → markdown with gspace: block
# edit content
docs_update(file_id="1abc...", new_content=edited_markdown)
```

Never call `docs_update` without first reading the doc — you need the current content to make targeted edits, and the `gspace:` block for context.
