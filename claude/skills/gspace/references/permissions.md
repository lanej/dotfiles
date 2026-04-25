---
name: gspace/permissions
description: "Use when sharing a Drive file or folder, granting or revoking access, listing who has access, or changing permission roles. Covers permissions_list, permissions_grant, permissions_update, permissions_revoke MCP tools and their CLI equivalents."
---

# Permissions

## CLI

```
gspace permissions list <file_id>
gspace permissions grant <file_id> --type <type> --role <role> [--email <email>] [--domain <domain>]
gspace permissions update <file_id> <permission_id> --role <role>
gspace permissions revoke <file_id> <permission_id>
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `permissions_list` | List all permissions on a file or folder |
| `permissions_grant` | Grant access (write-gated) |
| `permissions_update` | Change role on existing permission (write-gated) |
| `permissions_revoke` | Remove a permission (write-gated) |

## Patterns and Gotchas

**Permission types:** `user`, `group`, `domain`, `anyone`

**Roles:** `owner`, `writer`, `commenter`, `reader`

**Type + identity mapping:**
- `user` or `group` → requires `--email` / `email_address`
- `domain` → requires `--domain`
- `anyone` → no email or domain needed

**File ID:** Accepts raw IDs or any Drive/Docs/Sheets URL — resolved via `resolveFileId()`.

**Permission ID:** Returned by `permissions_list`. Required for `update` and `revoke`. There is no lookup-by-email; list first to find the ID.

**Write gate:** `permissions_grant`, `permissions_update`, and `permissions_revoke` all go through the ntfy write gate when `GSPACE_NTFY_TOPIC` is set.

**Cross-cutting domain:** Permissions operate on any Drive file regardless of type (Docs, Sheets, Slides, folders). This is intentional — the domain is modular and not duplicated per service.

**Revoking owner:** Transferring or revoking the `owner` role has additional restrictions enforced by the Drive API; the operation may fail if the target is the sole owner.
