---
description: "Write or update doc-state.md for the current document: locks the outline, records decisions made, captures session handoff context. Run at the end of any structural editing session."
argument-hint: <path to document>
tags:
  - writing
  - documentation
  - checkpoint
---

{file:~/.claude/agents/prompts/doc-state-schema.md}

---

# Checkpoint Document State

Write or update the `doc-state.md` file for the document at **$ARGUMENTS**.

## Steps

1. **Read the document** in full. Do not summarize it — extract structure.

2. **Identify the file path** for `doc-state.md`:
   - If a `doc-state.md` already exists alongside the document, update it in place.
   - Otherwise create it in the same directory as the document.

3. **If a prior `doc-state.md` exists**, read it first. Preserve existing Decisions Made and Do Not Revisit entries — only append, never delete history. Update the Locked Outline only if the structure actually changed this session.

4. **Populate each section** per the schema above:
   - **Locked Outline**: extract the actual section structure from the document as it exists now. Mark it locked.
   - **Key Arguments**: infer from document content — the core claims the document makes or must make. One sentence each. Ask the user to confirm if ambiguous.
   - **Decisions Made**: include anything from this session that was deliberate — a section that was restructured, a framing that was chosen over an alternative, content that was cut.
   - **Do Not Revisit**: anything explicitly excluded or previously rejected.
   - **Next Section**: the specific section or unfinished task to work on next. If the document is complete, state that.
   - **Session Handoff**: what changed this session, where editing stopped, any open questions.

5. **Write the file**. Confirm the path to the user.

## When to use

Run `/checkpoint-doc` at the end of any session that:
- Established or changed the outline
- Made structural decisions (section order, scope, what to include/exclude)
- Completed a major section
- Is about to end with the document unfinished

Do not run it for minor prose edits within a section that change no structure.
