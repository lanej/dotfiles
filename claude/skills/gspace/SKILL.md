---
name: gspace
description: Use gspace CLI for Google Workspace operations including Drive file management, Gmail search and automation, Docs editing, Sheets manipulation, and Calendar events.
---
# Google Workspace (gspace) Skill

You are a Google Workspace specialist using the gspace CLI. This skill provides comprehensive guidance for working with Google Drive, Gmail, Docs, Sheets, and Calendar operations.

## Core Principles

### Authentication

Check authentication status before performing operations:

```bash
gspace auth status
```

### Output Formats

Control output format with global flags:

```bash
--format json    # JSON output
--format text    # Human-readable text (default)
--format quiet   # Minimal output
--json          # Shorthand for --format json
--quiet         # Shorthand for --format quiet
```

### Common Flags

```bash
-v, --verbose   # Verbose logging
-y, --yes       # Skip confirmation prompts
```

## Google Drive Operations

### Search and List Files

```bash
# Search for files
gspace drive files search "filename"
gspace drive files search "*.pdf"
gspace drive files search --query "name contains 'report'"

# List files
gspace drive files list
gspace drive files list --folder-id <folder-id>
```

### File Operations

```bash
# Download files
gspace drive files download <file-id>
gspace drive files download <file-id> --output /path/to/file

# Upload files
gspace drive files upload /path/to/file
gspace drive files upload /path/to/file --parent <folder-id>

# Copy files
gspace drive files copy <file-id> --name "New Name"

# Rename files
gspace drive files rename <file-id> "New Name"

# Move files
gspace drive files move <file-id> --parent <new-folder-id>

# Delete files
gspace drive files delete <file-id>

# Get file metadata
gspace drive files get <file-id>
```

### Folder Operations

```bash
# Create folder
gspace drive folders create "Folder Name"
gspace drive folders create "Folder Name" --parent <parent-folder-id>

# Move folder
gspace drive folders move <folder-id> --parent <new-parent-id>
```

### Permissions Management

```bash
# List permissions
gspace permissions list <file-id>

# Add permission
gspace permissions add <file-id> --email user@example.com --role writer
gspace permissions add <file-id> --email user@example.com --role reader

# Remove permission
gspace permissions remove <file-id> <permission-id>
```

## Gmail Operations

### Search and Read Emails

```bash
# Search emails
gspace gmail search "from:sender@example.com"
gspace gmail search "subject:invoice after:2024/01/01"
gspace gmail search "has:attachment"

# Get specific email
gspace gmail get <message-id>

# Get email thread
gspace gmail thread <thread-id>

# List labels
gspace gmail labels
```

### Send and Draft Emails

```bash
# Send email
gspace gmail send --to recipient@example.com --subject "Subject" --body "Message body"

# Create draft
gspace gmail draft --to recipient@example.com --subject "Subject" --body "Message body"

# Send existing draft
gspace gmail send-draft <draft-id>
```

### Manage Emails

```bash
# Mark as read/unread
gspace gmail mark-read <message-id>
gspace gmail mark-read <message-id> --unread

# Star/unstar
gspace gmail star <message-id>
gspace gmail star <message-id> --unstar

# Archive (remove from INBOX)
gspace gmail archive <message-id>

# Move to trash
gspace gmail trash <message-id>

# Permanently delete (requires confirmation)
gspace gmail delete <message-id> --confirm

# Modify labels
gspace gmail label <message-id> --add IMPORTANT --remove INBOX
gspace gmail batch-label <msg-id1> <msg-id2> --add WORK
```

### Attachments

```bash
# Download attachment
gspace gmail download-attachment <message-id> <attachment-id>
gspace gmail download-attachment <message-id> <attachment-id> --output /path/to/file
```

## Google Docs Operations

### Create and Download Docs

```bash
# Create doc from markdown
gspace docs create --title "Document Title" --content-file content.md
gspace docs create --title "Document Title" --content "Direct content"

# Download doc to markdown
gspace docs download <doc-id>
gspace docs download <doc-id> --output document.md
```

### Edit Docs

```bash
# Find and replace
gspace docs find-replace <doc-id> --find "old text" --replace "new text"

# Edit doc remotely
gspace docs edit <doc-id> --content-file updates.md
```

### Comments

```bash
# List comments
gspace docs comments-list <doc-id>

# Get specific comment
gspace docs comments-get <doc-id> <comment-id>

# Create comment
gspace docs comments-create <doc-id> --content "Comment text"

# Reply to comment
gspace docs comments-reply <doc-id> <comment-id> --content "Reply text"

# Resolve comment
gspace docs comments-resolve <doc-id> <comment-id>
```

## Google Sheets Operations

### Create and Update Sheets

```bash
# Create spreadsheet
gspace sheets create --title "Spreadsheet Title"

# Update cells
gspace sheets update <spreadsheet-id> --range "Sheet1!A1:B2" --values "[[\"A1\", \"B1\"], [\"A2\", \"B2\"]]"

# Append rows
gspace sheets append <spreadsheet-id> --range "Sheet1!A:B" --values "[[\"value1\", \"value2\"]]"
```

## Google Calendar Operations

### View Events

```bash
# Today's events
gspace calendar today

# Tomorrow's events
gspace calendar tomorrow

# Yesterday's events
gspace calendar yesterday

# List events in date range
gspace calendar list --start 2024-01-01 --end 2024-12-31

# Search events
gspace calendar search "meeting"
```

### Create Events

```bash
# Create event
gspace calendar create --summary "Meeting Title" --start "2024-01-15T10:00:00" --end "2024-01-15T11:00:00"
gspace calendar create --summary "All Day Event" --start "2024-01-15" --all-day
```

## Google Tasks Operations

```bash
# Task operations
gspace tasks list
gspace tasks create --title "Task Title"
gspace tasks complete <task-id>
```

## Common Workflows

### Backup Drive Files

```bash
# Search for files and download
gspace drive files search "*.docx" --json | jq -r '.[].id' | while read id; do
  gspace drive files download "$id"
done
```

### Email Management

```bash
# Archive all emails from specific sender
gspace gmail search "from:sender@example.com" --json | jq -r '.[].id' | while read id; do
  gspace gmail archive "$id" -y
done
```

### Batch Operations

```bash
# Use --yes flag to skip confirmations
gspace drive files delete <file-id> --yes

# Use --quiet for scripting
gspace drive files list --quiet
```

## MCP Server Mode

gspace can run as an MCP (Model Context Protocol) server:

```bash
# Start MCP server
gspace mcp start

# Check MCP status
gspace mcp status
```

## Best Practices

1. **Use JSON output for scripting**: `--json` flag provides structured output for parsing
2. **Confirm destructive operations**: Always verify file IDs before delete operations
3. **Use specific queries**: Narrow searches with specific Drive queries or Gmail filters
4. **Batch operations carefully**: Use `--yes` flag cautiously with bulk operations
5. **Check authentication**: Run `gspace auth status` if encountering access errors
6. **Use folder IDs**: Reference folders by ID rather than name for reliability
7. **Handle attachments**: Download attachments separately using message and attachment IDs

## Error Handling

```bash
# Verbose mode for debugging
gspace drive files download <file-id> --verbose

# Check authentication
gspace auth status

# Re-authenticate if needed
gspace auth login
```

## Search Query Syntax

### Drive Queries

- `name contains 'text'` - Search by filename
- `mimeType = 'application/pdf'` - Filter by file type
- `'folder-id' in parents` - Files in specific folder
- `trashed = false` - Exclude trashed files

### Gmail Queries

- `from:sender@example.com` - From specific sender
- `to:recipient@example.com` - To specific recipient
- `subject:keyword` - Subject contains keyword
- `has:attachment` - Has attachments
- `after:2024/01/01` - Date filters
- `before:2024/12/31` - Date filters
- `is:unread` - Unread messages
- `label:IMPORTANT` - Specific label
