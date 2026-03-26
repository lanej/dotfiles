# Tasks, People, Slides, Forms, Meet, Chat, Groups Reference

## Tasks

```python
mcp__gspace__tasks_list_lists()
mcp__gspace__tasks_get_list(tasklist_id="list123")
mcp__gspace__tasks_create_list(title="Q2 Goals")
mcp__gspace__tasks_list(tasklist_id="list123", show_completed=True)
mcp__gspace__tasks_get(tasklist_id="list123", task_id="task456")
mcp__gspace__tasks_create(tasklist_id="list123", title="Review PR", due="2026-04-01T17:00:00Z", notes="High priority")
mcp__gspace__tasks_update(tasklist_id="list123", task_id="task456", status="completed")
mcp__gspace__tasks_complete(tasklist_id="list123", task_id="task456")
mcp__gspace__tasks_move(tasklist_id="list123", task_id="task456", parent="parent123")
mcp__gspace__tasks_delete(tasklist_id="list123", task_id="task456")
mcp__gspace__tasks_clear_completed(tasklist_id="list123")
```

```bash
gspace tasks lists
gspace tasks list TASKLIST_ID --show-completed
gspace tasks get TASKLIST_ID TASK_ID
gspace tasks create TASKLIST_ID "Review PR" --due "2026-04-01T17:00:00Z"
gspace tasks update TASKLIST_ID TASK_ID --status completed
gspace tasks delete TASKLIST_ID TASK_ID
gspace tasks clear-completed TASKLIST_ID
```

## People / Contacts

```python
mcp__gspace__people_contacts_list()
mcp__gspace__people_contacts_search(query="Josh Lane")
mcp__gspace__people_contacts_get(resource_name="people/c123")
mcp__gspace__people_contacts_create(given_name="Jane", family_name="Doe", email="jane@example.com")
mcp__gspace__people_contacts_update(resource_name="people/c123", given_name="Jane", phone="+15551234567")
mcp__gspace__people_contacts_update_photo(resource_name="people/c123", photo_url="https://...")
mcp__gspace__people_contacts_delete(resource_name="people/c123")
mcp__gspace__people_groups_list()
mcp__gspace__people_groups_create(name="Engineering")
mcp__gspace__people_groups_get(resource_name="contactGroups/g123")
mcp__gspace__people_groups_update(resource_name="contactGroups/g123", name="Eng Team")
mcp__gspace__people_groups_delete(resource_name="contactGroups/g123")
```

## Slides

```python
mcp__gspace__slides_get(presentation_id="pres123")
mcp__gspace__slides_list_pages(presentation_id="pres123")
mcp__gspace__slides_get_page(presentation_id="pres123", page_object_id="page1")
mcp__gspace__slides_get_thumbnail(presentation_id="pres123", page_object_id="page1")
mcp__gspace__slides_create(title="Q2 Review", local_path="/tmp/content.md")
```

## Forms

```python
mcp__gspace__forms_get(form_id="form123")
mcp__gspace__forms_list_responses(form_id="form123")
mcp__gspace__forms_get_response(form_id="form123", response_id="resp456")
mcp__gspace__forms_create(title="Survey", description="Q2 feedback")
```

## Meet

```python
mcp__gspace__meet_create_space()
mcp__gspace__meet_get_space(name="spaces/abc123")
mcp__gspace__meet_get_conference(name="conferenceRecords/rec123")
mcp__gspace__meet_list_conferences(filter="space.name=spaces/abc123")
mcp__gspace__meet_list_participants(parent="conferenceRecords/rec123")
mcp__gspace__meet_list_recordings(parent="conferenceRecords/rec123")
mcp__gspace__meet_list_transcripts(parent="conferenceRecords/rec123")
mcp__gspace__meet_get_transcript_entries(parent="conferenceRecords/rec123/transcripts/t1")
```

## Chat

```python
mcp__gspace__chat_list_spaces()
mcp__gspace__chat_get_space(name="spaces/sp123")
mcp__gspace__chat_create_space(display_name="Engineering", space_type="SPACE")
mcp__gspace__chat_list_messages(parent="spaces/sp123")
mcp__gspace__chat_get_message(name="spaces/sp123/messages/msg456")
mcp__gspace__chat_send_message(parent="spaces/sp123", text="Hello team")
mcp__gspace__chat_list_members(parent="spaces/sp123")
```

## Cloud Identity Groups

```python
mcp__gspace__groups_list()
mcp__gspace__groups_search(query="engineering")
mcp__gspace__groups_get(group_id="groups/g123")
mcp__gspace__groups_create(email="eng-team@company.com", display_name="Engineering Team")
mcp__gspace__groups_update(group_id="groups/g123", display_name="Eng Team")
mcp__gspace__groups_delete(group_id="groups/g123")
mcp__gspace__groups_members_list(group_id="groups/g123")
mcp__gspace__groups_members_get(group_id="groups/g123", member_id="members/m123")
mcp__gspace__groups_members_add(group_id="groups/g123", email="user@company.com")
mcp__gspace__groups_members_remove(group_id="groups/g123", member_id="members/m123")
```
