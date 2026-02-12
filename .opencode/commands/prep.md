# Daily Meeting Prep

You are helping the user prepare for today's meetings by gathering context and creating a comprehensive prep document.

## Your Task

Create a detailed meeting prep document for today by:

1. **Pull Today's Calendar**
   - Use `mcp__gdrive__list_calendar_events` to get all events for today with timezone
   - For each event, use `mcp__gdrive__get_event` to get detailed information including descriptions, attendees, and attachments
   - Note event IDs for follow-up access

2. **Research Previous Meeting Context Using Semantic Search**

   **Use Workspace Knowledge Base for Comprehensive Context:**

   For each meeting, perform multiple semantic searches across both tables to gather rich context:

   a. **Search by Person**
   - Search `easypost_people_notes` for each attendee's name
   - Search `easypost_meeting_notes` for previous discussions with this person
   - Get role, background, and relationship context

   b. **Search by Topic/Project**
   - Extract key topics from meeting title and description
   - Search for project names, initiatives, or technologies mentioned
   - Examples: "Carrier Hub", "OnTrac integration", "incident response"
   - Find related discussions even if attendees weren't present

   c. **Search by Meeting Type**
   - For skip-levels: search for team dynamics, organizational feedback
   - For 1:1s: search for ongoing projects, action items, career development
   - For staff meetings: search for cross-team initiatives, strategic topics

   d. **Search for Related Concepts**
   - Combine attendee + topic in search query
   - Example: "Andy Bakun Carrier Hub OnTrac"
   - Semantic search finds conceptually related discussions across entire workspace

   **Key Advantage:** Semantic search understands meaning and relationships, finding relevant context even when exact keywords don't match. It searches across 1,300+ documents in seconds.

   **Search the ENTIRE Workspace:** Don't limit searches to specific files or directories. The knowledge base contains all your meeting notes, people notes, and work documentation. Cast a wide net with conceptual queries to find all relevant material.

   **Example Queries:**
   - Person + Topic: "Andy Bakun Carrier Hub OnTrac integration"
   - Meeting Type: "skip-level organizational culture team feedback"
   - Strategic Context: "engineering directors priorities resource allocation"
   - Project Context: "incident response paging escalation process"

   **Local File Search** (rarely needed):
   - Only use if semantic search doesn't find sufficient context
   - Knowledge base should have everything already indexed

3. **Access Google Drive Documents**
   - If calendar events contain Google Drive/Docs links in descriptions:
     - Extract document IDs from URLs (format: `/d/{documentId}/` or `/document/d/{documentId}/`)
     - Use `mcp__gdrive__download_drive_file` with `export_format="markdown"` to get readable content
     - Or use `mcp__gdrive__get_file_metadata` to understand document type and details
     - Summarize key content relevant to the meeting
     - Download documents to `context/` directory per CLAUDE.md instructions
   - Look for agenda documents, pre-reads, or reference materials

4. **Analyze and Organize**
   - Identify meeting types (1:1s, skip-levels, staff meetings, working sessions)
   - Prioritize meetings by importance and preparation needs
   - Note any special occasions (birthdays, milestones)
   - Identify built-in prep time and breaks

5. **Generate Prep Documents**
   - Create a comprehensive prep document in `prep/meeting_prep_YYYY-MM-DD.md`
   - Create a context file in `context/meeting_context_YYYY-MM-DD.md` with historical notes
   - For each meeting include:
     - Attendee information and context
     - Previous meeting notes and discussion topics
     - Specific prep questions tailored to past conversations
     - Action items from previous meetings
     - Links to relevant documents
     - Expected outcomes and decisions needed

6. **Create Action Items List**
   - Priority-coded action items (🔴 critical, 🟡 high priority, 🟢 nice to have)
   - Time-sensitive prep tasks
   - Documents to review before specific meetings
   - Follow-ups from previous meetings

## Output Format

Generate two files:

**prep/meeting_prep_[DATE].md:**
```markdown
# Meeting Prep - [Day, Month Date, YYYY]

**Current Time:** [TIME] - [CONTEXT ABOUT PREP TIME AVAILABLE]

## Summary
[Overview of day, number of meetings, key priorities, special notes]

---

## [TIME]: [Meeting Title]
**Attendee(s):** [Names and emails]

**Context:**
[Meeting type, frequency, who scheduled it, any special notes]

**Previous Context from Notes:**
[Key points from previous meetings with dates]
[Ongoing discussions and concerns]
[Action items and follow-ups]

**Discussion Topics:**
[Tailored topics based on previous conversations]

**Prep Questions:**
[Specific questions to guide the conversation]

**Documents to Review:**
[Links to Google Docs, agendas, or other materials]

---

[Repeat for each meeting]

---

## Pre-Meeting Action Items

**CRITICAL:**
1. 🔴 [Time-sensitive or high-impact items]

**High Priority:**
2. 🟡 [Important but less urgent items]

**Nice to Have:**
3. 🟢 [Optional items]

---

## Built-In Prep Time
[List hold blocks, breaks, and when to use them]

---

## Meeting Flow & Transitions
[Timeline view of the day with emphasis on prep windows]

---

## Key Themes for Today
[Patterns, focus areas, reminders]
```

**context/meeting_context_[DATE].md:**
```markdown
# Meeting Context - [Date]

Historical context extracted from previous meeting notes.

## [Person/Meeting Name]

**Source:** [File paths and dates]

**Key Context:**
- [Historical points]
- [Previous discussions]
- [Ongoing initiatives]

**Discussion Focus:**
[What to prioritize based on history]

---

[Repeat for each person/meeting]
```

## Best Practices

- **Be specific**: Reference actual dates, quotes, and specific concerns from previous notes
- **Be actionable**: Provide concrete questions and discussion topics
- **Be contextual**: Tailor prep to each person's role, history, and current situation
- **Be realistic**: Note when prep time is limited and prioritize accordingly
- **Be thorough**: Don't skip meetings without context - note that and suggest general topics

## Important Notes

- If calendar authentication expires, inform the user they need to restart the MCP server
- If Google Drive access isn't available, note which documents couldn't be accessed
- Always check the user's current timezone and work hours
- Note birthdays, anniversaries, or special events happening today
- Flag any scheduling conflicts or back-to-back meetings without breaks
