---
name: gspace/forms
description: "Google Forms via gspace. Use when reading a Google Form's structure or questions, listing form responses, or creating a blank form."
---

# Forms

## CLI

```
gspace forms get <form-id>
gspace forms create <title>

gspace forms responses list <form-id> [--page-size <n>] [--page-token <token>]
gspace forms responses get <form-id> <response-id>
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `forms_get` | Get form structure including all questions and settings |
| `forms_create` | Create a new blank form (write-gated) |
| `forms_list_responses` | List responses to a form |
| `forms_get_response` | Get a specific response by ID |

## Patterns and Gotchas

- `forms_create` only creates a blank form with a title. Question/section editing is not supported via the API — do that in the Forms UI.
- Response IDs come from `forms_list_responses`; use them to fetch individual response detail.
- No update or delete operations are available — Forms API read/create only in this implementation.
- `forms_check_auth` is MCP-only.
