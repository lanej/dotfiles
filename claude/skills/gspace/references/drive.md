# Drive, Docs, Sheets, Permissions Reference

## Export Formats

| Format | MIME / notes |
|--------|-------------|
| `markdown` | Google Docs → clean markdown (recommended) |
| `text` | Plain text |
| `pdf` | Preserves layout |
| `docx` | Word format |
| `xlsx` | Excel — **preserves all sheets** |
| `csv` | First sheet only |
| `html` | Docs only |

## Drive Files — MCP

```python
mcp__gspace__drive_files_list(folder_id="folder123", limit=20)
mcp__gspace__drive_files_search(query="Q4 report", type="application/vnd.google-apps.document", limit=10)
mcp__gspace__drive_files_metadata(file_id="abc123")

mcp__gspace__drive_files_download(file_id="abc123", local_path="/tmp/doc.md", export_format="markdown")
mcp__gspace__drive_files_download(file_id="sheet123", local_path="/tmp/data.xlsx", export_format="xlsx")

mcp__gspace__drive_files_upload(local_path="/tmp/data.csv", name="Sales Data", convert_to_google_format=True)
mcp__gspace__drive_files_upsert(local_path="/tmp/report.csv", name="Monthly Report.csv", parent_folder_id="folder123")

mcp__gspace__drive_files_copy(file_id="abc123", name="Backup Copy")
mcp__gspace__drive_files_rename(file_id="abc123", new_name="Updated Name")
mcp__gspace__drive_files_delete(file_id="abc123")           # trash
mcp__gspace__drive_files_delete(file_id="abc123", permanently=True)

mcp__gspace__drive_files_list_tabs(file_id="doc123")         # multi-tab Docs
mcp__gspace__drive_revisions_list(file_id="abc123")
mcp__gspace__drive_revisions_get(file_id="abc123", revision_id="rev1")
```

## Drive Folders — MCP

```python
mcp__gspace__drive_folders_create(name="Project Documents", parent_folder_id="parent123")
mcp__gspace__drive_folders_move(file_id="abc123", new_parent_folder_id="folder456")
```

## Drive Comments — MCP

```python
mcp__gspace__drive_comments_list(file_id="doc123", page_size=50)
mcp__gspace__drive_comments_get(file_id="doc123", comment_id="comment456")
mcp__gspace__drive_comments_create(file_id="doc123", content="Needs review")
mcp__gspace__drive_comments_reply(file_id="doc123", comment_id="comment456", content="Fixed!", action="resolve")
mcp__gspace__drive_comments_resolve(file_id="doc123", comment_id="comment456")
```

## Permissions — MCP

```python
mcp__gspace__drive_files_search(query="name contains 'report'")  # find before granting

# Grant
mcp__gspace__permissions_grant(file_id="abc123", role="writer", type="user", email="user@example.com")
mcp__gspace__permissions_grant(file_id="abc123", role="reader", type="domain", domain="easypost.com")
mcp__gspace__permissions_list(file_id="abc123")
mcp__gspace__permissions_update(file_id="abc123", permission_id="perm456", role="commenter")
mcp__gspace__permissions_revoke(file_id="abc123", permission_id="perm456")
```

## Google Docs — MCP

```python
mcp__gspace__docs_download(file_id="doc123", output_path="/tmp/doc.md")          # markdown
mcp__gspace__docs_apply_text_diff(file_id="doc123", new_content="Updated text...")
mcp__gspace__docs_find_replace(file_id="doc123", find_text="TODO", replace_text="DONE")
mcp__gspace__docs_find_replace(file_id="doc123", find_text="Error", replace_text="Warning", match_case=True)
```

## Google Sheets — MCP

```python
mcp__gspace__sheets_get(file_id="sheet123")
mcp__gspace__sheets_get_values(file_id="sheet123", range="Sheet1!A1:C10")
mcp__gspace__sheets_create(name="Customer Database")
mcp__gspace__sheets_update(file_id="sheet123", range="A1:B2", values=[["Name","Value"],["Item",100]])
mcp__gspace__sheets_append(file_id="sheet123", values=[["New Row","Value"]])
```

## CLI

```bash
# Files
gspace drive files list
gspace drive files search "Q4 report"
gspace drive files metadata FILE_ID
gspace drive files download FILE_ID /tmp/doc.md --export markdown
gspace drive files download "https://docs.google.com/document/d/FILE_ID/edit" /tmp/doc.md
gspace drive files upload /path/file "Name"
gspace drive files upsert /path/file "Name" --folder FOLDER_ID
gspace drive files copy FILE_ID --name "Copy"
gspace drive files rename FILE_ID "New Name"
gspace drive files delete FILE_ID

# Folders
gspace drive folders create "Project Docs"
gspace drive folders move FILE_ID FOLDER_ID

# Docs
gspace docs create /path/notes.md "Document Title"
gspace docs download DOC_ID /tmp/output.md
gspace docs find-replace DOC_ID "old text" "new text"
gspace docs comments list DOC_ID
gspace docs comments create DOC_ID "Comment text"
gspace docs comments reply DOC_ID COMMENT_ID "Reply"
gspace docs comments resolve DOC_ID COMMENT_ID

# Sheets
gspace sheets get SHEET_ID
gspace sheets get-values SHEET_ID "Sheet1!A1:C10"
gspace sheets create "Name"
gspace sheets update SHEET_ID "A1:B2" '[["Name","Value"]]'
gspace sheets append SHEET_ID '[["Row","Value"]]'

# Permissions
gspace permissions grant FILE_ID --type user --role writer --email user@example.com
gspace permissions list FILE_ID
gspace permissions update FILE_ID PERM_ID --role commenter
gspace permissions revoke FILE_ID PERM_ID
```

## Drive Search Query Syntax

- `name contains 'text'`
- `mimeType = 'application/vnd.google-apps.document'`
- `'folder-id' in parents`
- `modifiedTime > '2026-01-01T00:00:00'`
- `trashed = false`

Common MIME types: `application/vnd.google-apps.document`, `...spreadsheet`, `...presentation`, `application/pdf`
