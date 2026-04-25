---
name: gspace/docs
description: "Load when creating a Google Doc from Markdown, reading or editing an existing doc, syncing a local .md file to Drive, doing find-replace in a doc, managing stylesheets, or any time working with .md files destined for Google Docs."
---

# Docs

## CLI

```bash
# Create new doc from Markdown file
gspace docs create <name> <markdown_file> [--folder-id <id>] [--style-sheet <path>]

# Download doc as Markdown (injects gspace: frontmatter with revision token)
gspace docs download <file_id_or_url> <output_path>

# Push using gspace: frontmatter — reads file, syncs, writes revision token back
gspace docs sync <markdown_file>

# Edit interactively in $EDITOR with optimistic locking
gspace docs edit <file_id_or_url> [--editor <binary>]

# Stylesheets
gspace docs stylesheets list
gspace docs stylesheets install <file.docx> [name]
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `docs_create` | Create a new Google Doc from Markdown content string (pandoc → DOCX → Google Doc) |
| `docs_download` | Download doc as Markdown and write to `local_path`; returns `{success, local_path, sizeBytes}` |
| `docs_sync` | Push a local Markdown file (`local_path`) to its Google Doc; writes updated revision token back to the file |
| `docs_stylesheets_list` | List `.docx` stylesheets in `~/.config/gspace/stylesheets/` |

## Sync Workflow

`docs_sync` is the primary write path for existing docs. The file is self-describing — all routing and state lives in its `gspace:` frontmatter.

```
# First push (no prior revision — auto-bootstraps revision from Drive):
docs_sync(local_path="/abs/path/to/doc.md")

# Subsequent pushes use the revision token already written back by the previous sync:
docs_sync(local_path="/abs/path/to/doc.md")
```

After each successful sync, `docs_sync` updates `revision:` and `downloaded_at:` in the file. No manual writeback required.

On conflict (`SyncConflictError`): call `docs_download` to get the latest remote content, merge your changes in, write the merged result to disk, then retry `docs_sync`.

CLI `gspace docs sync` performs this conflict-resolution automatically (auto-pull → merge → retry).

## YAML Frontmatter

Frontmatter serves two separate systems: pandoc (top-level keys) and gspace (all keys nested under `gspace:`). They are processed independently.

### Top-level keys (pandoc metadata)

These are consumed by pandoc during DOCX conversion and rendered as styled paragraphs in the document body.

| Key | Required | Description |
|-----|----------|-------------|
| `title:` | Recommended | Rendered as a Title-style paragraph at the top of the document body |
| `subtitle:` | Optional | Rendered as a Subtitle-style paragraph immediately below the title |

**Warning:** `author:` and `date:` are pandoc-reserved top-level keys. If placed at the top level, pandoc renders them as visible body text in the document. Always put `author` and `date` inside `gspace:` instead.

### gspace: subkeys

All gspace-specific configuration lives under the `gspace:` key. Subkeys fall into two categories.

#### Authoring fields (set by the user)

| Key | Required | Description |
|-----|----------|-------------|
| `url:` | REQUIRED | Google Docs web URL of the target doc. All sync operations route to this file. |
| `style_sheet:` | Optional | Named stylesheet (`easypost`, `blue-headers`) or path to a `.docx` reference file. Applied on every sync via pandoc `--reference-doc`. |
| `author:` | Optional | Injected into `{{author}}` placeholder in header/footer (easypost stylesheet). Example: `"Josh Lane · Chief Technology Officer"` |
| `date:` | Optional | Injected into `{{date}}` placeholder in header/footer. Example: `"April 2026"` |

**Legacy:** `file_id:` is still accepted as a backward-compatible fallback. `url:` is preferred — it's human-readable and self-linking.

#### Managed fields (set automatically by gspace)

Do not edit these manually. `docs_download` and `docs_sync` write and update them.

| Key | Description |
|-----|-------------|
| `revision:` | Drive version token for optimistic locking. Updated after every successful sync. |
| `downloaded_at:` | ISO 8601 timestamp of the last download or sync. |
| `file_name:` | Drive file display name. Set on download. |
| `media_dir:` | Path to extracted image files. Set on download when the doc contains inline images. |

### Managed vs Authoring Fields

**Authoring fields** (`url`, `style_sheet`, `author`, `date`) — you set these. `url` is required; the rest are optional and persist across syncs.

**Managed fields** (`revision`, `downloaded_at`, `file_name`, `media_dir`) — gspace owns these. Editing them manually will break optimistic locking or produce stale metadata.

### Example: well-formed doc with easypost stylesheet

```markdown
---
title: Problem Discovery
gspace:
  url: https://docs.google.com/document/d/1abc...xyz/edit
  file_name: problem-discovery
  revision: kDwGh3...
  downloaded_at: '2026-04-14T00:00:00Z'
  style_sheet: easypost
  author: "Josh Lane · Chief Technology Officer"
  date: "April 2026"
---

## Problem Statement

...
```

## Stylesheet System

Named pandoc reference `.docx` files live in `~/.config/gspace/stylesheets/`. Pass by bare name or full path anywhere `style_sheet` is accepted.

| Stylesheet | Description |
|------------|-------------|
| `blue-headers` | Uniform blue (#1155CC) on Title + all headings |
| `easypost` | Presentation brand: navy title, logo-blue H1–H2, EasyPost icon header, author/date footer |

Heading colors are re-applied post-upload via the Docs API automatically — Google's DOCX import strips style-level heading colors.

Install a custom stylesheet:
```bash
gspace docs stylesheets install ~/my-style.docx my-style
```

## Supported Markdown Elements

All elements round-trip cleanly through pandoc → DOCX → Google Doc:

- Headings `#` through `######` → Heading 1–6 styles
- **Bold**, *italic*, ***bold italic***, `inline code`
- Bullet lists (`-`) and numbered lists (`1.`) including nested
- Fenced code blocks — Courier New, gray background
- Blockquotes (`>`)
- Tables with borders
- [Hyperlinks](url)
- Math: inline `$...$` and display `$$...$$` — rendered as Google Docs equation objects via OMML

**Math support:** pandoc's `tex_math_dollars` extension is enabled by default. Write LaTeX math directly in Markdown; pandoc converts it to OMML on upload and Google Docs renders it as native equation objects. Round-trip note: on download, both inline and display math come back as `$...$` (pandoc normalizes OMML to inline form); the `$$` display delimiter is not preserved.

**Page breaks:** Use a horizontal rule (`---`, `***`, or `___`) — converted to a DOCX page break by the Lua filter. Do NOT use `\newpage` or raw OpenXML — they are not preserved through the Google Docs round-trip.

## Patterns and Gotchas

**`docs_sync` is the only safe write path for existing docs.** All content changes must go through `docs_sync`. It reads the local file, checks the remote revision token before writing, uploads, and writes the updated token back. This prevents agents or scripts from silently clobbering concurrent edits.

**Never use `drive_files_upload` or `drive_files_upsert` for Markdown.** Both commands detect `.md` files and throw an error. They bypass pandoc and produce stock Google styles without the reference stylesheet. Use `docs_create` for new docs, `docs_sync` for existing.

**`docs_sync` uses optimistic locking.** Reads the Drive `version` field before uploading. If the remote version doesn't match the local `revision:` token, throws `SyncConflictError`. On first sync (no `revision:` in frontmatter), auto-bootstraps the current remote version as the baseline.

**`docs_edit` optimistic locking.** Aborts the upload if the doc was modified remotely while the editor was open. Preserves your changes to `/tmp/gspace-edit-{id}.md` on conflict.

**`docs_find_replace` with revision.** Pass `--revision` (CLI) or `revision` (MCP) to enable server-enforced locking via `writeControl.requiredRevisionId`. The Docs API returns 409 if the doc has changed — no extra round-trip needed.

**`docs_download` writes to disk.** Both MCP and CLI write the downloaded Markdown to `local_path`. Extracted image files are left alongside the output file (referenced by absolute path in the Markdown).

**Pageless mode is unsupported.** The Google Docs API v1 does not support creating documents in pageless mode (returns HTTP 400). Users must enable it manually via File → Page setup → Pageless after creation. Tracked in [Google Issue #227875469](https://issuetracker.google.com/issues/227875469).

**Tab-scoped find-replace.** Pass `tab_id` to limit replacements to a specific tab in multi-tab documents. Without it, replacements apply across all tabs.
