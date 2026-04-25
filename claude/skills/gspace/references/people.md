---
name: gspace/people
description: "Use when managing personal contacts (not org-wide groups), looking up, creating, or updating contacts, updating contact photos, or managing contact group labels. This is the People API (personal contacts). NOT for org-wide Google Groups — use gspace/groups for that."
---

# People

## CLI

```
gspace people contacts list [--page-size <n>] [--page-token <token>]
gspace people contacts get <resource-name>
gspace people contacts search <query> [--page-size <n>]
gspace people contacts create [--given-name <n>] [--family-name <n>] [--email <e>] [--email-type <t>] [--phone <p>] [--phone-type <t>] [--organization <o>] [--title <t>]
gspace people contacts update <resource-name> [same flags as create]
gspace people contacts update-photo <resource-name> --url <url> | --file <path>
gspace people contacts delete <resource-name>

gspace people groups list [--page-size <n>] [--page-token <token>]
gspace people groups get <resource-name> [--max-members <n>]
gspace people groups create <name>
gspace people groups update <resource-name> <new-name>
gspace people groups delete <resource-name>
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `people_contacts_list` | List contacts (default 100, max 1000) |
| `people_contacts_get` | Get contact by resource name or bare ID |
| `people_contacts_search` | Search by name, email, phone, or notes (default 30) |
| `people_contacts_create` | Create contact (write-gated) |
| `people_contacts_update` | Update contact — requires `etag` |
| `people_contacts_update_photo` | Update contact photo from URL (write-gated) |
| `people_contacts_delete` | Permanently delete a contact |
| `people_groups_list` | List contact groups/labels (default 100) |
| `people_groups_get` | Get group by resource name or bare ID |
| `people_groups_create` | Create contact group |
| `people_groups_update` | Update group name — requires `etag` |
| `people_groups_delete` | Permanently delete a contact group |

## Patterns and Gotchas

**Resource name format:** Contacts use `people/c123` (or bare `c123`). Contact groups use `contactGroups/abc123` (or bare `abc123`).

**etag requirement (MCP only):** `people_contacts_update` and `people_groups_update` require an `etag` for optimistic concurrency. Fetch with `_get` first to obtain it. The CLI handles this automatically — it auto-fetches the etag before updating.

**Update replaces fields:** Passing `--email` in `contacts update` replaces all email addresses with a single entry. Same for phone and organization. Omit a field to leave it unchanged.

**Photo update (MCP):** Only accepts a URL. The CLI additionally accepts `--file <path>`. Both base64-encode the image before calling the API.

**Contact groups vs. Cloud Identity Groups:** `gspace people groups` manages personal contact labels (People API). `gspace groups` manages org-wide Google Groups (Cloud Identity API) — entirely different API and scope.

**Write-gated operations:** `people_contacts_create`, `people_contacts_update_photo` go through the ntfy write gate when `GSPACE_NTFY_TOPIC` is set. Deletes do not.
