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

Always include `title:` in YAML frontmatter. **Do not use `drive_files_upload` with `convert_to_google_format` for Markdown files** — it bypasses pandoc and produces stock Google styles without the reference stylesheet.

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

**MCP:** `docs_update` — accepts Markdown string. Replaces the entire document via DOCX intermediary (pandoc → DOCX → Drive). Optional `style_sheet` param overrides the default stylesheet.

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

## Stylesheet Library

Named pandoc reference `.docx` files live in `~/.config/gspace/stylesheets/`. Reference them by bare name anywhere a stylesheet is accepted.

```bash
gspace docs stylesheets list                       # list installed stylesheets
gspace docs stylesheets install <file.docx> [name] # add to library
```

MCP: `docs_stylesheets_list`

**Installed stylesheets:**

| Name | Description |
|------|-------------|
| `blue-headers` | Uniform blue (#1155CC) on Title + all headings |
| `easypost` | Presentation brand: navy title, logo-blue H1–H2, EasyPost icon header, author/date footer |

**Heading color application:** Google Docs' DOCX import strips style-level heading colors. gspace re-applies them post-upload via the Docs API automatically — no user action needed.

**Creating a custom stylesheet:**
```bash
# Copy the base reference doc and modify styles (python-docx or LibreOffice)
cp ~/.local/share/gspace/google-reference.docx ~/my-style.docx
# Then install it
gspace docs stylesheets install ~/my-style.docx my-style
```

## YAML Frontmatter

All downloaded Markdown includes a YAML frontmatter block. **Always preserve and pass it through when writing back.**

### gspace: metadata block

Injected automatically on download. Stripped automatically before upload — do not remove it manually.

```yaml
---
title: My Document Title
gspace:
  file_id: 1abc...xyz
  file_name: filename-in-drive
  url: https://docs.google.com/document/d/1abc...xyz/edit
  revision: kDwGh3...
  downloaded_at: '2026-04-10T17:00:00Z'
---
```

**Extended `gspace:` fields** (all nested under `gspace:`, not top-level):

| Field | Effect |
|-------|--------|
| `style_sheet: <name-or-path>` | Persists the stylesheet; applied automatically on every update |
| `author: "Name · Role"` | Injected into `{{author}}` placeholder in header/footer (easypost stylesheet) |
| `date: "Month Year"` | Injected into `{{date}}` placeholder in header/footer |

**Critical:** `author:` and `date:` must be **nested under `gspace:`**, never at the top level. Pandoc treats top-level `author:` and `date:` as reserved metadata and renders them as body content paragraphs. Same applies to any config that should stay invisible to pandoc.

### Title vs file name

| Field | What it controls |
|-------|-----------------|
| `title:` | The **Title-style paragraph** rendered in the document body. Always set this. |
| `subtitle:` | Optional **Subtitle-style paragraph** below the title. Use only for visible subtitle text — not for bylines or author info. |
| `gspace.file_name` | The **Drive file name**. Metadata only, never rendered in the document. |

### Example: well-formed document with easypost stylesheet

```markdown
---
title: Problem Discovery
gspace:
  file_id: 1abc...xyz
  file_name: problem-discovery
  url: https://docs.google.com/document/d/1abc...xyz/edit
  revision: kDwGh3...
  downloaded_at: '2026-04-14T00:00:00Z'
  style_sheet: easypost
  author: "Josh Lane · Chief Technology Officer"
  date: "April 2026"
---

## Problem Statement

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

**Page breaks:** Use a horizontal rule (`---`, `***`, or `___`) — converted to a DOCX page break by the Lua filter. Do not use `\newpage` or raw OpenXML.

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
| `docs_stylesheets_list` | List stylesheets available in the local XDG library. |

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
2. Edit the Markdown (preserve `gspace:` block and `title:` field)
3. `docs_update` → write back

```
docs_download(file_id="1abc...") → markdown with gspace: block
# edit content
docs_update(file_id="1abc...", new_content=edited_markdown)
```

Never call `docs_update` without first reading the doc — you need the current content to make targeted edits, and the `gspace:` block for context.
