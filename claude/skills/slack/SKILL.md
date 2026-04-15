# Skill: slack

## When to Use

Load this skill when:

- Working with Slack messages, channels, users, or files
- Searching Slack workspace content
- Sending messages or reactions via automation
- Reading unread messages or thread conversations
- Any task involving `~/src/slack` project

## Project Location

`~/src/slack` — TypeScript/Bun Slack CLI + MCP server.

## Auth Setup

Token is a Slack **user OAuth token** (`xoxp-`), NOT a bot token. Bot tokens (`xoxb-`) won't work for search or user lookup.

```bash
# Set token:
export SLACK_TOKEN=xoxp-your-token-here
# Or: echo "xoxp-your-token-here" > ~/.config/slack/token
```

Verify: `slack auth check`

### Creating a Slack App (to get xoxp token)

1. https://api.slack.com/apps → Create New App → From scratch
2. OAuth & Permissions → User Token Scopes (NOT Bot Token Scopes):
   ```
   search:read, channels:history, groups:history, im:history, mpim:history,
   channels:read, groups:read, im:read, mpim:read,
   users:read, users:read.email,
   files:read, files:write,
   chat:write, reactions:write,
   channels:write, groups:write, im:write, mpim:write
   ```
3. Install to Workspace → copy **User OAuth Token**

## MCP Tools Reference

All tools use `slack_{operation}` naming.

| Tool                     | Required Params          | Optional Params                                    | Returns                              |
| ------------------------ | ------------------------ | -------------------------------------------------- | ------------------------------------ |
| `slack_check_auth`       | —                        | —                                                  | `{valid, team_id, user_id}`          |
| `slack_search`           | `query`                  | `sort`, `sort_dir`, `count` (max 100), `page`      | messages array + total               |
| `slack_channel_history`  | `channel`                | `limit` (default 50), `oldest`, `latest`, `cursor` | messages + pagination                |
| `slack_thread`           | `channel`, `thread_ts`   | `limit` (default 100)                              | all replies                          |
| `slack_send`             | `channel`, `text`        | `thread_ts`                                        | `{ts, permalink}`                    |
| `slack_channels_list`    | —                        | `types[]`, `exclude_archived`                      | channels array                       |
| `slack_unreads`          | —                        | —                                                  | channels sorted by unread count desc |
| `slack_users_search`     | `query`                  | —                                                  | matching users                       |
| `slack_reactions_add`    | `channel`, `ts`, `emoji` | —                                                  | `{success: true}`                    |
| `slack_reactions_remove` | `channel`, `ts`, `emoji` | —                                                  | `{success: true}`                    |
| `slack_files_list`       | —                        | `channel`, `count` (default 20)                    | file metadata array                  |

**Token strategy:** MCP messages truncated to 200 chars. No file bodies. Use `slack_thread` for full content.

**Channel input:** accepts both `C123ABC` IDs and `#channel-name` strings.

**Emoji input:** without colons (e.g., `thumbsup` not `:thumbsup:`).

## CLI Commands Reference

```bash
# Auth
slack auth check

# Search
slack search "query" [--sort score|timestamp] [--count N] [--page N] [--format json|text]

# Channels
slack channels list [--types public,private,im,mpim] [--all] [--format json|text]
slack channels history #general [--limit 50] [--oldest TS] [--latest TS]
slack channels mark #general 1234567890.000001

# Threads
slack thread #general 1234567890.000001 [--format json|text]

# Messages
slack send #general "hello" [--thread TS]

# Unreads
slack unreads [--format json|text]

# Users
slack users list [--format json|text]
slack users get U123ABC
slack users get josh@easypost.com
slack users search "josh"

# Files
slack files list [--channel C123] [--count 20] [--format json|text]
slack files download F123ABC /tmp/report.pdf

# Reactions
slack reactions add #general 1234567890.000001 thumbsup
slack reactions remove C123ABC 1234567890.000001 thumbsup

# MCP server
slack mcp stdio
```

## Common Patterns

### Search then read thread

```bash
# Find message
slack search "deployment issue" --count 5 | jq '.messages[0] | {ts, channel_id, channel_name}'

# Read full thread
slack thread C123ABC 1234567890.000001 | jq '.[] | {user_id, text}'
```

### Unreads workflow

```bash
# See what needs attention
slack unreads --format text

# Read a specific channel's unreads
slack channels history #ops --limit 20 | jq '.messages[] | {user_id, text}'

# Mark as read
slack channels mark #ops $(slack channels history #ops --limit 1 | jq -r '.messages[0].ts')
```

### MCP tool sequence for reading Slack

1. `slack_unreads` — find channels with activity
2. `slack_channel_history` with `channel` ID — get recent messages
3. `slack_thread` for any message with `reply_count > 0`
4. `slack_users_search` to resolve `user_id` to names

## Rate Limits

- `conversations.history`: 1 req/min for non-Marketplace apps (Tier 3)
- `search.messages`: Tier 2 (20 req/min)
- `users.list`: Tier 2 (20 req/min) — cached internally for `searchUsers`
- `chat.postMessage`: Tier 3 (1 req/sec per channel)

The `@slack/web-api` SDK handles 429 retries automatically.

## Project Commands

```bash
cd ~/src/slack
bun test              # Run all tests (24 tests, 0 deps on real API)
bun run typecheck     # TypeScript check
bun run lint          # ESLint
bun run dev --help    # CLI help
just install          # Build + install to ~/.local/bin/slack
```

Base directory for this skill: file:///Users/joshlane/.config/opencode/skills/slack
