---
name: gspace/meet
description: "Google Meet via gspace. Use when creating a Meet space, looking up past conference records, listing participants or recordings, or fetching transcript text."
---

# Meet

## CLI

```
gspace meet create [--access-type OPEN|TRUSTED|RESTRICTED] [--entry-point-access ALL|CREATOR_APP_ONLY]
gspace meet get <space-name>

gspace meet conferences list [--page-size <n>] [--page-token <token>] [--filter <expr>]
gspace meet conferences get <conference-name>

gspace meet participants list <conference-name> [--page-size <n>] [--page-token <token>]

gspace meet recordings list <conference-name> [--page-size <n>] [--page-token <token>]

gspace meet transcripts list <conference-name> [--page-size <n>] [--page-token <token>]
gspace meet transcripts entries <transcript-name> [--page-size <n>] [--page-token <token>]
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `meet_create_space` | Create a new meeting space (write-gated) |
| `meet_get_space` | Get meeting space details |
| `meet_list_conferences` | List past conference records |
| `meet_get_conference` | Get a specific conference record |
| `meet_list_participants` | List participants of a conference |
| `meet_list_recordings` | List recordings of a conference |
| `meet_list_transcripts` | List transcripts of a conference |
| `meet_get_transcript_entries` | Get spoken text entries from a transcript |

## Patterns and Gotchas

- Space names: `spaces/abc123` or bare ID. Conference names: `conferenceRecords/abc123` or bare ID.
- Transcript entries require the full transcript name: `conferenceRecords/abc/transcripts/def` — get this from `meet_list_transcripts` first.
- `access_type` controls who can join: `OPEN` (anyone with link), `TRUSTED` (org members), `RESTRICTED` (invite only). Defaults to `OPEN`.
- Conference records are historical — they represent past meetings, not upcoming ones. Use Calendar for scheduling.
- `meet_create_space` is write-gated. All other tools are read-only.
- `meet_check_auth` is MCP-only.
