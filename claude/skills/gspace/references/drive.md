---
name: gspace/drive
description: "Use when working with Google Drive files or folders — uploading, downloading, searching, copying, renaming, or deleting files; listing or navigating Drive; managing shared drives; adding or resolving comments; viewing revision history; querying file activity; or any Drive operation via gspace CLI or MCP."
---

# Drive

## CLI

```bash
# Files
gspace drive files list [--folder <id>] [--drive-id <id>] [-l <n>]
gspace drive files list-drives
gspace drive files search "query" [--search-mode name|content|both] [--type <mime>] [--owner <email>] [--folder <id>] [--drive-id <id>] [--shared-with-me] [--modified-after <iso>] [--modified-before <iso>] [--created-after <iso>] [--created-before <iso>] [--limit <n>]
gspace drive files download <id_or_url> <local_path> [--export <format>] [--tab-id <id>] [--split-tabs] [--download-images]
gspace drive files upload <local_path> <name> [--parent <id>] [--convert] [--mime-type <type>]
gspace drive files upsert <local_path> <name> [--parent <id>] [--convert] [--mime-type <type>]
gspace drive files update <file_id> <local_path> [--name <newName>] [--mime-type <type>]
gspace drive files copy <id_or_url> <name> [--parent <id>]
gspace drive files rename <id_or_url> <new_name>
gspace drive files delete <id_or_url> [--permanently]
gspace drive files metadata <id_or_url>
gspace drive files list-tabs <id_or_url>

# Folders
gspace drive folders create <name> [--parent <id>]
gspace drive folders move <file_id> <new_parent_id>

# Comments
gspace drive comments list <file_id> [--include-deleted] [--page-size <n>] [--page-token <token>] [--start-modified-time <rfc3339>]
gspace drive comments get <file_id> <comment_id> [--include-deleted]
gspace drive comments create <file_id> <content> [--anchor <json>]
gspace drive comments reply <file_id> <comment_id> <content> [--action resolve|reopen]
gspace drive comments resolve <file_id> <comment_id>

# Revisions
gspace drive revisions list <file_id> [--page-token <token>]
gspace drive revisions get <file_id> <revision_id>

# Activity (requires --enable-drive-activity or config flag)
gspace drive activity query <file_id> [--ancestor] [--page-token <token>] [--page-size <n>] [--filter <expr>] [--no-consolidation]
```

## MCP Tools

### Files

| Tool | Description |
|------|-------------|
| `drive_files_search` | Search with advanced filters (name/content/both, owner, dates, shared drive) |
| `drive_files_download` | Download to local path; accepts file ID or any Drive/Workspace URL |
| `drive_files_upload` | Upload file, optionally convert to Google format. **Not for Markdown** |
| `drive_files_upsert` | Upload replacing existing file by name (preserves file ID, revision history, sharing). **Not for Markdown** |
| `drive_files_copy` | Copy a file |
| `drive_files_rename` | Rename a file |
| `drive_files_delete` | Delete (trash or permanent) |
| `drive_files_metadata` | Full metadata including `headRevisionId` |
| `drive_files_list` | List files in a folder or shared drive root |
| `drive_files_list_drives` | List all shared drives |
| `drive_files_list_tabs` | List tabs in a Google Doc (routes through Docs API, not Drive API) |

### Folders

| Tool | Description |
|------|-------------|
| `drive_folders_create` | Create a folder |
| `drive_folders_move` | Move file or folder to a different parent |

### Comments

| Tool | Description |
|------|-------------|
| `drive_comments_list` | List comments on a file |
| `drive_comments_get` | Get a specific comment with replies |
| `drive_comments_create` | Add a comment (optional anchor for text selection) |
| `drive_comments_reply` | Reply to a comment; can also resolve/reopen |
| `drive_comments_resolve` | Resolve a comment |

### Revisions

| Tool | Description |
|------|-------------|
| `drive_revisions_list` | List all revisions of a file |
| `drive_revisions_get` | Get metadata for a specific revision |

### Activity

| Tool | Description |
|------|-------------|
| `drive_activity_query` | Query edit/view/share/comment activity; requires `enableDriveActivity` config |

## Export Format Table

| Format | Works with | Notes |
|--------|-----------|-------|
| `text` | Docs, Sheets | Plain text |
| `markdown` | Docs | HTML export converted to Markdown |
| `html` | Docs | Raw HTML |
| `pdf` | Docs, Sheets, Slides | |
| `docx` | Docs | Word format |
| `odt` | Docs | OpenDocument |
| `csv` | Sheets | First sheet only |
| `xlsx` | Sheets | All sheets preserved |
| `zip` | Sheets | HTML zip archive |
| `pptx` | Slides | PowerPoint |

## Patterns and Gotchas

**upsert vs upload:** `upsert` finds an existing file by name (optionally scoped to a folder) and updates it in-place, preserving file ID, revision history, and sharing settings. `upload` always creates a new file. Use `upsert` for recurring exports or idempotent pushes; use `upload` when you intentionally want a new file.

**Never use upload/upsert for Markdown.** Both `drive_files_upload --convert` and `drive_files_upsert --convert` will throw an error if given a `.md` file — they bypass pandoc and produce stock Google styles. Use `docs_create` (new doc) or `docs_update` (existing doc) instead.

**`list-tabs` routes through Docs API.** `drive_files_list_tabs` calls the Docs API internally, not the Drive API. The Drive API returns incorrect tab data for multi-tab documents.

**IDs and URLs are interchangeable.** All CLI commands and MCP tools that accept a file ID also accept full Drive/Docs/Sheets URLs. The `resolveFileId()` utility strips them transparently.

**`drive-read` MCP filter.** When the MCP server is started with `--only drive-read`, write tools (`upload`, `upsert`, `copy`, `rename`, `delete`, `folders_create`, `folders_move`, `comments_create`, `comments_reply`, `comments_resolve`) are omitted entirely — not just gated.

**Write gate.** All write tools go through the ntfy write gate when `GSPACE_NTFY_TOPIC` is set. Approval is cached per tool for `GSPACE_WRITE_GATE_CACHE_TTL_SECS` (default 300s).

**`sharedWithMe` date filters** are applied client-side (Drive API v3 does not support them in query filters). All other date filters (`modifiedAfter`, `createdAfter`, `viewedByMeAfter`) are server-side.

**Activity tool is opt-in.** `drive_activity_query` is only registered when `enableDriveActivity` is true in config (or `--enable-drive-activity` flag). It is off by default to avoid requiring the Drive Activity API scope.
