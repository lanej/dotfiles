# Calendar Reference

## MCP Tools

```python
# List events
mcp__gspace__calendar_list(
    time_min="2026-03-01T00:00:00Z",
    time_max="2026-03-31T23:59:59Z",
    max_results=50
)

# Search
mcp__gspace__calendar_search(q="sprint planning", time_min="2026-03-01T00:00:00Z")

# Free/busy
mcp__gspace__calendar_query_freebusy(
    time_min="2026-03-26T09:00:00-07:00",
    time_max="2026-03-26T17:00:00-07:00",
    items=[{"id": "primary"}, {"id": "user@example.com"}]
)

# Find availability
mcp__gspace__calendar_find_availability(
    duration_minutes=60,
    time_min="2026-03-26T09:00:00-07:00",
    time_max="2026-03-26T17:00:00-07:00"
)

# Create
mcp__gspace__calendar_create(
    summary="Sprint Planning",
    start="2026-03-27T14:00:00-07:00",
    end="2026-03-27T15:00:00-07:00",
    description="Q2 sprint kickoff"
)

# Update / delete
mcp__gspace__calendar_update(event_id="event123", summary="Updated Title")
mcp__gspace__calendar_delete(event_id="event123")

# Reminders
mcp__gspace__calendar_update_reminders(event_id="event123", use_default=False, overrides=[])
mcp__gspace__calendar_update_reminders(
    event_id="event123",
    use_default=False,
    overrides=[{"method": "popup", "minutes": 10}]
)

# ACL
mcp__gspace__calendar_list_acl(calendar_id="primary")
```

## CLI

```bash
gspace calendar list --time-min 2026-03-01T00:00:00Z
gspace calendar today
gspace calendar tomorrow
gspace calendar yesterday
gspace calendar search "sprint planning"
gspace calendar create "Sprint Planning" --start "2026-03-27T14:00:00-07:00" --end "2026-03-27T15:00:00-07:00"
gspace calendar update EVENT_ID --summary "New Title"
gspace calendar delete EVENT_ID
gspace calendar update-reminders EVENT_ID --disable
```

## Notes

- Times are RFC3339 format with timezone offset (e.g. `2026-03-26T09:00:00-07:00`)
- `calendar_id` defaults to `"primary"` when omitted
- `find_availability` respects existing events and working hours
