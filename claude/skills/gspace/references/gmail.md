# Gmail Reference

## MCP Tools

### Search
```python
mcp__gspace__gmail_search(query="from:boss@company.com subject:urgent", max_results=10)
mcp__gspace__gmail_search(query="has:attachment after:2026/01/01")
```

### Get message / thread
```python
mcp__gspace__gmail_get(message_id="19d269df3e0475f2")

# By API thread ID
mcp__gspace__gmail_thread(thread_id="19d269df3e0475f2")

# By search query — use this when you have a Gmail web URL (#inbox/...)
mcp__gspace__gmail_thread(search_query="from:user@example.com subject:Q1 review in:inbox")
```

**Note:** Gmail web app `#inbox/` URLs use an internal format incompatible with the API. Always use `search_query` when the user provides a Gmail web URL. Only `#search/` Gmail URLs work directly as `thread_id`.

### Send / draft
```python
mcp__gspace__gmail_send(to=["user@example.com"], subject="Hello", body_text="Message")
mcp__gspace__gmail_draft(to=["team@example.com"], subject="Draft: Review", body_text="...")
mcp__gspace__gmail_send_draft(draft_id="draft123")
```

**Non-ASCII subjects get mangled** — use hyphens not em dashes, straight quotes not smart quotes.

### Message management
```python
mcp__gspace__gmail_archive(message_id="msg123")
mcp__gspace__gmail_star(message_id="msg123")
mcp__gspace__gmail_trash(message_id="msg123")
mcp__gspace__gmail_delete(message_id="msg123")
mcp__gspace__gmail_label(message_id="msg123", add_label_ids=["IMPORTANT"], remove_label_ids=["INBOX"])
```

### Download body / attachment
```python
mcp__gspace__gmail_download_body(message_id="msg123", output_path="/tmp/body.txt")
mcp__gspace__gmail_download_attachment(message_id="msg123", attachment_id="att456", output_path="/tmp/file.pdf")
```

### Labels
```python
mcp__gspace__gmail_labels_list()
mcp__gspace__gmail_labels_create(name="Notifications/Carrier")
mcp__gspace__gmail_labels_update(label_id="Label_123", name="Updated Name")
mcp__gspace__gmail_labels_delete(label_id="Label_123")
```

### Filters
```python
mcp__gspace__gmail_filters_list()
mcp__gspace__gmail_filters_get(filter_id="filter123")
mcp__gspace__gmail_filters_create(criteria={"from": "noreply@example.com"}, action={"addLabelIds": ["Label_123"]})
mcp__gspace__gmail_filters_delete(filter_id="filter123")
```

## CLI

```bash
# Search
gspace gmail search "from:boss@company.com subject:urgent"
gspace gmail search "in:inbox is:unread" --max-results 20

# Get message/thread
gspace gmail get MESSAGE_ID
gspace gmail thread THREAD_ID
gspace gmail thread --search "from:user@example.com subject:topic"
# Gmail web URLs (#inbox/...) are NOT supported — use --search

# Send
gspace gmail send user@example.com "Subject" "Body text"
gspace gmail draft user@example.com "Subject" "Body text"
gspace gmail send-draft DRAFT_ID

# Message management
gspace gmail archive MESSAGE_ID
gspace gmail star MESSAGE_ID
gspace gmail trash MESSAGE_ID
gspace gmail delete MESSAGE_ID
gspace gmail label MESSAGE_ID --add IMPORTANT --remove INBOX

# Download
gspace gmail download-body MESSAGE_ID /tmp/body.txt
gspace gmail download-attachment MESSAGE_ID ATTACHMENT_ID /tmp/file.pdf

# Labels
gspace gmail labels list
gspace gmail labels create "Notifications/Carrier"
gspace gmail labels update LABEL_ID --name "New Name"
gspace gmail labels delete LABEL_ID

# Filters
gspace gmail filters list
gspace gmail filters get FILTER_ID
gspace gmail filters delete FILTER_ID
```

## Gmail Search Syntax

- `from:sender@example.com` / `to:recipient@example.com`
- `subject:keyword`
- `has:attachment` / `filename:pdf`
- `after:2026/01/01` / `before:2026/12/31`
- `is:unread` / `is:starred`
- `in:inbox` / `in:sent` / `label:LABEL_NAME`
- `newer_than:7d` / `older_than:30d`
