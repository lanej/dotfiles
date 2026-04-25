---
name: gspace/groups
description: "Use when managing org-wide Google Groups, listing or searching groups, creating groups, or adding/removing group members. This is the Cloud Identity Groups API (org-wide). NOT for personal contact labels — use gspace/people for those."
---

# Groups

## CLI

```
gspace groups list [--page-size <n>] [--page-token <token>] [--parent <parent>]
gspace groups search <query> [--page-size <n>] [--page-token <token>]
gspace groups get <group>
gspace groups create <email> [--display-name <name>] [--description <desc>] [--parent <parent>]
gspace groups update <group> [--display-name <name>] [--description <desc>]
gspace groups delete <group>

gspace groups members list <group> [--page-size <n>] [--page-token <token>]
gspace groups members add <group> <email> [--role OWNER|MANAGER|MEMBER]
gspace groups members remove <group> <email>
gspace groups members get <group> <email>
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `groups_list` | List org groups (default 200, max 1000) |
| `groups_search` | Search groups by CEL query |
| `groups_get` | Get group by resource name, ID, or email |
| `groups_create` | Create group (write-gated) |
| `groups_update` | Update display name or description (write-gated) |
| `groups_delete` | Permanently delete a group (write-gated) |
| `groups_members_list` | List group members (default 200) |
| `groups_members_add` | Add member with optional role |
| `groups_members_remove` | Remove member from group |
| `groups_members_get` | Get membership details for a member |

## Patterns and Gotchas

**Group identifier:** All operations accept resource name (`groups/xxx`), bare ID, or email address interchangeably. Email is usually the most convenient.

**CEL query syntax for search:**
```
parent == "customers/my_customer" && "cloudidentity.googleapis.com/groups.discussion_forum" in labels
```
Use `groups_search` for filtering by label type or name; `groups_list` for full enumeration.

**Parent resource:** Defaults to `customers/my_customer` (your org). Override only when targeting a specific customer resource in a multi-tenant setup.

**Membership roles:** `OWNER`, `MANAGER`, `MEMBER`. Default is `MEMBER`. Role is only settable on `add`; use the Groups admin console to change existing member roles.

**Write-gated operations:** `groups_create`, `groups_update`, and `groups_delete` go through the ntfy write gate when `GSPACE_NTFY_TOPIC` is set. Member add/remove are not gated.

**Not the same as contact groups:** `gspace groups` is the Cloud Identity Groups API (org-wide Google Groups). `gspace people groups` is the People API contact labels for personal contacts — different API, different scope, different resource names.
