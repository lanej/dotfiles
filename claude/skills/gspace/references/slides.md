---
name: gspace/slides
description: "Google Slides via gspace. Use when reading a Google Slides presentation structure, listing slides, getting slide content or thumbnails, or creating a blank presentation."
---

# Slides

## CLI

```
gspace slides get <presentation-id>
gspace slides create <title>

gspace slides pages list <presentation-id>
gspace slides pages get <presentation-id> <page-object-id>
gspace slides pages thumbnail <presentation-id> <page-object-id> [--size SMALL|MEDIUM|LARGE]
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `slides_get` | Get presentation metadata and structure |
| `slides_create` | Create a new blank presentation (write-gated) |
| `slides_list_pages` | List all slides in a presentation |
| `slides_get_page` | Get a specific slide with all elements and text |
| `slides_get_thumbnail` | Get a thumbnail image URL for a slide |

## Patterns and Gotchas

- `presentation-id` accepts raw ID or full Google Slides URL.
- `page-object-id` is an internal object ID (e.g., `g1234567890`), not a slide number. Get it from `slides_list_pages` or `slides_get`.
- Thumbnail returns a URL, not image data — fetch the URL separately if you need the bytes.
- Thumbnail size defaults to `MEDIUM`. `LARGE` gives the highest resolution.
- No slide editing operations — content modification requires the Slides API `batchUpdate` endpoint not exposed here. Use Drive download with `--export pdf` for export.
- `slides_create` creates a blank presentation; add content via the Slides UI or Slides API directly.
- `slides_check_auth` is MCP-only.
