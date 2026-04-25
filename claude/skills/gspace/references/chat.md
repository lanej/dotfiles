---
name: gspace/chat
description: "Google Chat via gspace. Use when sending messages to a Google Chat space, listing spaces or members, reading message history, or creating spaces."
---

# Chat

## CLI

```
gspace chat spaces list [--page-size <n>] [--page-token <token>] [--filter <expr>]
gspace chat spaces get <space-name>
gspace chat spaces create <display-name> [--space-type SPACE|GROUP_CHAT]

gspace chat members list <space-name> [--page-size <n>] [--page-token <token>]

gspace chat messages list <space-name> [--page-size <n>] [--page-token <token>] [--filter <expr>] [--order-by <expr>]
gspace chat messages get <message-name>
gspace chat messages send <space-name> <text> [--thread-key <key>]
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `chat_list_spaces` | List Chat spaces the user is a member of |
| `chat_get_space` | Get details about a space |
| `chat_create_space` | Create a new space (write-gated) |
| `chat_list_members` | List members of a space |
| `chat_list_messages` | List messages in a space |
| `chat_get_message` | Get a specific message by full name |
| `chat_send_message` | Send a message to a space (write-gated) |

## Patterns and Gotchas

- Space names are `spaces/AAAA123` format; CLI accepts bare IDs or full names interchangeably.
- Message names are fully qualified: `spaces/AAAA123/messages/msg1`. Get this from `messages list` output before calling `messages get`.
- `--order-by` for messages uses Google AIP ordering syntax: `createTime desc`.
- Thread replies: pass `--thread-key` (CLI) or `thread_key` (MCP) to reply within a thread. The key is a stable identifier you define, not a message name.
- `chat_create_space` and `chat_send_message` go through the write gate if `GSPACE_NTFY_TOPIC` is set.
- `chat_check_auth` is MCP-only; no CLI equivalent.
