---
name: gspace/gmail
description: "Use when searching, reading, or sending Gmail messages; composing or sending drafts; managing labels or filters; downloading email bodies or attachments; embedding Drive file chips in messages; or any Gmail operation via gspace CLI or MCP."
---

# Gmail

Search, read, compose, and organize Gmail messages and threads; manage labels and filters; embed Drive file chips in drafts.

## CLI

**Search / Read**
- `gspace gmail search <query>` — Gmail query syntax; `--max-results <n>` (1–500), `--label-ids <ids>` (comma-sep), `--include-spam-trash`
- `gspace gmail get <message-id>` — message metadata (no body)
- `gspace gmail thread [<thread-id-or-url>]` — thread by raw ID or `#search/` URL; `--search <query>` for query-based lookup
- `gspace gmail download-body <message-id> <output-path>` — `--body-format text|html|both` (default: both)
- `gspace gmail download-attachment <message-id> <attachment-id> <output-path>`
- `gspace gmail draft-get <draft-id>` — returns body + detected Drive chips

**Compose**

> **Preferred path**: write a `.md` file with YAML frontmatter and use `gspace gmail compose` or `gmail_send` with `body_markdown`. This produces rich HTML emails and is far easier to author and review than raw strings.

- `gspace gmail compose <file.md>` — **preferred**; saves as draft by default; add `--send` to send immediately; frontmatter provides headers; `--to`, `--subject`, `--cc`, `--bcc` flags override frontmatter

  ```yaml
  ---
  to: recipient@example.com        # string or list; required
  subject: Hello from gspace       # required
  cc: cc@example.com               # optional; string or list
  bcc: bcc@example.com             # optional; string or list
  ---
  Body in **markdown**. Sent as multipart/alternative (markdown as plain-text,
  rendered HTML as HTML part).
  ```

- `gspace gmail send <to> <subject> <body>` — plain-text only; use only for one-liners where a file is overkill
- `gspace gmail draft <to> <subject> <body>` — `--cc`, `--bcc`, `--chip <fileId>` or `--chip <fileId:title:type>` (repeatable)
- `gspace gmail send-draft <draft-id>`

**Message Actions**
- `gspace gmail label <message-id>` — `--add <ids>`, `--remove <ids>` (comma-sep)
- `gspace gmail archive <message-id>`
- `gspace gmail star <message-id>` — `--unstar` to remove
- `gspace gmail trash <message-id>`
- `gspace gmail delete <message-id>` — permanent, no recovery

**Labels**
- `gspace gmail labels list`
- `gspace gmail labels create <name>` — use `/` for hierarchy; `--text-color`, `--background-color`, `--hide`
- `gspace gmail labels update <label-id>` — same flags
- `gspace gmail labels delete <label-id>`

**Filters**
- `gspace gmail filters list`
- `gspace gmail filters get <filter-id>`
- `gspace gmail filters create` — `--from`, `--to`, `--subject`, `--query`, `--negated-query`, `--has-attachment`, `--add-labels`, `--remove-labels`, `--forward`
- `gspace gmail filters delete <filter-id>`

## MCP Tools

| Tool | Description |
|------|-------------|
| `gmail_search` | Search messages; returns metadata only (no body/attachments) |
| `gmail_get` | Get message metadata by ID |
| `gmail_thread` | Get thread by `thread_id` OR `search_query` (mutually exclusive) |
| `gmail_send` | Send new message; **prefer `body_markdown`** — rendered to HTML, sent as multipart/alternative; `body_text`/`body_html` available for edge cases |
| `gmail_draft` | Create draft, optionally with Drive `chips` array |
| `gmail_draft_get` | Get draft with body and detected Drive chips |
| `gmail_send_draft` | Send a previously created draft |
| `gmail_label` | Add/remove label IDs on a message |
| `gmail_archive` | Remove message from INBOX |
| `gmail_star` | Star a message; pass `unstar: true` to remove |
| `gmail_trash` | Move to trash |
| `gmail_delete` | Permanently delete; requires `confirm: true` |
| `gmail_download_body` | Save body to file; `format: text\|html\|both` |
| `gmail_download_attachment` | Save attachment to file |
| `gmail_labels_list` | List all labels (system + user) |
| `gmail_labels_create` | Create label with optional color and visibility |
| `gmail_labels_update` | Update label name, color, or visibility |
| `gmail_labels_delete` | Delete label by ID |
| `gmail_filters_list` | List all filters |
| `gmail_filters_get` | Get filter by ID |
| `gmail_filters_create` | Create filter with criteria and actions |
| `gmail_filters_delete` | Delete filter by ID |

Write operations go through the write gate when `GSPACE_NTFY_TOPIC` is set.

## Patterns and Gotchas

- **Subject line ASCII only**: Non-ASCII characters in subjects (em dashes, smart quotes) get mangled by RFC 2047 encoding. Use hyphens, not em dashes; straight quotes only.
- **Token reduction**: `gmail_search` and `gmail_get` return metadata only — body, headers, attachments, `sizeEstimate`, and `historyId` are stripped. Call `gmail_download_body` or `gmail_download_attachment` on demand. This cuts token usage ~95% for search results.
- **Thread ID vs message ID**: These are different. `#inbox/<id>` URLs in Gmail web use message IDs, not thread IDs — do not pass them to `gmail_thread`. Use `search_query` instead. `#search/<id>` URLs contain thread IDs and work with `thread_id`.
- **Thread lookup auto-resolve**: If you pass a message ID to `gmail_thread` (via URL or raw ID detected as `idType: 'message'`), the tool fetches the message to extract its `threadId` then loads the thread — one extra API call.
- **Drive chips in drafts**: `gmail_draft` accepts a `chips` array of `{ file_id, title?, type? }` where `type` is `file|document|spreadsheet|presentation|form`. `gmail_draft_get` parses the draft HTML and returns a `driveChips` field listing any embedded chips — useful for round-trip verification.
- **CLI chip syntax**: `--chip fileId` or `--chip fileId:title:type` (colon-delimited, repeatable flag).
- **Label hierarchy**: Use `/` separator in label names (e.g., `"Notifications/Carrier"`) — Gmail renders these as nested labels.
- **`gmail_delete` requires explicit confirm**: Pass `confirm: true` or the tool throws before the write gate even runs.
- **Preferred compose path**: `gspace gmail compose <file.md>` saves a draft by default — review it in Gmail before sending. Add `--send` to bypass the draft step. For MCP, use `gmail_send` with `body_markdown`. Both produce `multipart/alternative` emails with rendered HTML. Use `body_text`/`body_html` or `gspace gmail send` only for one-liners that don't warrant a file.
- **`gspace gmail compose` frontmatter schema**: `to` (string or list, required), `subject` (string, required), `cc` (string or list, optional), `bcc` (string or list, optional). CLI flags override frontmatter. Missing required fields throw before any API call.
- **Filter `negated_query`**: Matches messages that do NOT match the given query — distinct from `query` which must match.
