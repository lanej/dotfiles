---
name: gspace/tasks
description: "Google Tasks via gspace. Use when creating or managing Google Tasks, listing task lists, completing or deleting tasks, or working with subtasks."
---

# Tasks

## CLI

```
gspace tasks lists
gspace tasks get-list <tasklist-id>
gspace tasks create-list <title>

gspace tasks list <tasklist-id> [--max-results <n>] [--show-completed] [--show-deleted] [--show-hidden]
gspace tasks get <tasklist-id> <task-id>
gspace tasks create <tasklist-id> <title> [--notes <text>] [--due <RFC3339>] [--parent <id>]
gspace tasks update <tasklist-id> <task-id> [--title <text>] [--notes <text>] [--due <RFC3339>] [--status needsAction|completed]
gspace tasks complete <tasklist-id> <task-id>
gspace tasks delete <tasklist-id> <task-id>
gspace tasks clear <tasklist-id>
gspace tasks move <tasklist-id> <task-id> [--parent <id>] [--previous <id>]
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `tasks_list_lists` | List all task lists |
| `tasks_get_list` | Get a specific task list |
| `tasks_create_list` | Create a new task list (write-gated) |
| `tasks_list` | List tasks in a task list |
| `tasks_get` | Get a specific task |
| `tasks_create` | Create a new task (write-gated) |
| `tasks_update` | Update an existing task (write-gated) |
| `tasks_complete` | Mark a task as completed |
| `tasks_delete` | Permanently delete a task (write-gated) |
| `tasks_clear_completed` | Clear all completed tasks from a list |
| `tasks_move` | Move a task to a different position or parent |

## Patterns and Gotchas

- Due dates must be RFC3339 format (e.g., `2026-04-30T00:00:00Z`).
- Task titles max 1024 chars; notes max 8192 chars.
- MCP `tasks_list` uses `hide_completed` (bool) while CLI uses `--show-completed` flag — opposite semantics.
- `tasks_complete` is not write-gated; `tasks_update` with `status: completed` is — pick `tasks_complete` for simple completions.
- Subtasks: pass `--parent <task-id>` on create. Move with `--parent` to re-parent, `--previous` to reorder siblings.
- `tasks_clear_completed` is a bulk destructive operation — no undo.
- `tasks_check_auth` is MCP-only.
