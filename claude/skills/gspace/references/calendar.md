---
name: gspace/calendar
description: "Load when scheduling meetings, listing or searching calendar events, finding availability across multiple calendars, creating/updating/deleting events, or querying free/busy status."
---

# Calendar

## CLI

All times are RFC3339. Default calendar is `primary` unless `--calendar-id` specified.

```
gspace calendar list [--calendar-id <id>] [--time-min <t>] [--time-max <t>] [--max-results <n>] [--show-deleted]
gspace calendar search <query> [--calendar-id <id>] [--time-min <t>] [--time-max <t>] [--max-results <n>]
gspace calendar create <summary> <start> <end> [--calendar-id <id>] [--description <text>] [--location <loc>] [--attendees <email,email>]
gspace calendar update <event-id> [--calendar-id <id>] [--summary <s>] [--start <t>] [--end <t>] [--description <d>] [--location <l>]
gspace calendar delete <event-id> [--calendar-id <id>]
gspace calendar freebusy <calendar-ids> <time-min> <time-max>   # comma-separated IDs
gspace calendar find-availability <identifiers> <time-min> <time-max> [--duration <minutes>] [--time-zone <tz>] [--ignore-types <types>] [--ignore-keywords <words>]
gspace calendar list-acl [--calendar-id <id>] [--max-results <n>] [--page-token <token>]
gspace calendar update-attachments <event-id> --attachments '<json>' [--calendar-id <id>] [--send-updates all|externalOnly|none]
gspace calendar update-reminders <event-id> [--use-default] [--overrides '<json>'] [--calendar-id <id>] [--send-updates all|externalOnly|none]
```

CLI-only shortcuts (no MCP equivalent): `today`, `tomorrow`, `yesterday`.

## MCP Tools

| Tool | Description |
|---|---|
| `calendar_list` | List events in a date range; supports `single_events` to expand recurring |
| `calendar_search` | Full-text search across events |
| `calendar_query_freebusy` | Raw free/busy data for multiple calendars |
| `calendar_find_availability` | Find common free slots across calendars (business logic layer) |
| `calendar_create` | Create event with attendees, time zone, send_updates control |
| `calendar_update` | Patch event fields (summary, start, end, description, location) |
| `calendar_delete` | Delete event |
| `calendar_list_acl` | List calendar ACL entries (max 100) |
| `calendar_update_attachments` | Replace full attachment list on event |
| `calendar_update_reminders` | Replace reminder settings (use_default or overrides array) |
| `calendar_check_auth` | Verify Calendar API auth (MCP-only) |

## Patterns and Gotchas

**`find-availability` vs `freebusy`**: `freebusy`/`calendar_query_freebusy` returns raw busy blocks. `find-availability`/`calendar_find_availability` merges busy blocks and returns free slots — use this for scheduling. Minimum slot default is 30 minutes.

**Ignore filters for find-availability**: `--ignore-types` accepts `focusTime`, `outOfOffice`, `workingLocation`, `default`. `--ignore-keywords` does case-insensitive substring match on event titles (e.g. `hold,block,dnd`). Both treat matching events as free. Requires calendar read access to the other person's calendar.

**`calendar_list` vs `calendar_search`**: `list` is date-range first; `search` is full-text first. Both accept overlapping filters but serve different primary use cases.

**`single_events`** (MCP only, not exposed in CLI): set `true` to expand recurring events into individual instances. Without it, recurring events appear as a single item.

**Attendees in CLI**: pass as comma-separated string `--attendees a@x.com,b@x.com`. MCP takes an array of strings directly.

**Attachments replace, not merge**: `update-attachments`/`calendar_update_attachments` replaces the full list. Pass `[]` to remove all attachments.

**Reminders**: max 5 overrides. `use_default: true` and `overrides` are mutually exclusive in practice — setting `use_default: true` ignores overrides per Google API behavior.

**Write gate**: `calendar_create`, `calendar_update`, `calendar_delete`, `calendar_update_attachments`, `calendar_update_reminders` are gated when `GSPACE_NTFY_TOPIC` is set. `calendar_list`, `calendar_search`, `calendar_query_freebusy`, `calendar_find_availability`, `calendar_list_acl` are read-only (no gate).

**`send_updates`**: omitting it lets the Google Calendar API apply its default behavior (typically notifies attendees). Pass `none` to suppress notifications.

**Calendar IDs**: use `primary` for the authenticated user's primary calendar. For other calendars, use the full calendar ID (usually an email address or opaque ID visible in calendar settings).
