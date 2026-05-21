---
description: "Write long-form markdown documents with structural discipline: outline-first, checkpoint-based, session-handoff aware. Use for any document that spans multiple sessions or exceeds ~3 major sections."
argument-hint: <path to document or topic>
tags:
  - writing
  - documentation
  - long-form
---

{file:~/.claude/agents/prompts/doc-state-schema.md}

---

# Write Doc — Structured Long-Form Writing

Your task: write or continue the document at **$ARGUMENTS** using a two-pass discipline that prevents context degradation across sessions.

## Session Start Protocol

**Before writing anything**, execute this protocol:

1. **Check for `doc-state.md`** in the same directory as the target document.
   - If found: read it. State the locked outline to the user. Confirm which section is next. Do not deviate from the locked outline without explicit user approval.
   - If not found and the document already exists: read the document, infer its current structure, and ask the user whether to proceed from current structure or reset.
   - If neither exists: proceed to Pass 1 below.

2. **Surface the structural contract** before touching prose:
   - State the current or proposed outline explicitly.
   - Identify which sections are locked (previously approved) vs. open.
   - Confirm the next section to work on.

## Pass 1: Outline Pass

**Goal**: produce a locked outline before any prose is written.

Rules:
- Produce the outline as a flat list of sections with a one-sentence purpose for each.
- Include estimated scope (e.g., "2-3 paragraphs", "one table") per section.
- Do NOT write prose in Pass 1. Headers and section summaries only.
- Present the outline to the user. Wait for approval.
- On approval: write `doc-state.md` via the checkpoint schema, mark outline as locked, set status to `drafting`.

Pass 1 ends when the user approves the outline. Not before.

## Pass 2: Prose Pass

**Goal**: write against the frozen outline without restructuring.

Rules:
- Work section by section in outline order unless the user directs otherwise.
- Do not add, remove, or reorder sections. If a structural change seems warranted, surface it explicitly: "The outline has X here — I think Y would be stronger. Want to reopen the outline?" Then stop and wait.
- Apply the `human-writer` standards: radical brevity, executive voice, no AI patterns, no extrapolation.
- After completing each major section, note the progress without asking for permission to continue.

**If structural changes are requested mid-prose**: treat it as returning to Pass 1 for the affected sections. Update `doc-state.md` after the outline revision is approved.

## Session End Protocol

At the end of every session:
1. Run `/checkpoint-doc` on the document to update `doc-state.md`.
2. State explicitly: what was completed, what is next, and any open structural questions.

## Writing Standards

Apply `human-writer` agent standards throughout:
- Radical brevity: every word earns its place
- Executive voice: decisive, action-oriented, no hedging
- No extrapolation: write only what is in scope per the outline
- One document: edit the file in place, never create versions
- No AI tells: no "furthermore", "it is worth noting", "in conclusion"

## Document Length Thresholds

Apply Pass 1 discipline whenever:
- The document has 3+ major sections, OR
- The document is expected to span multiple writing sessions, OR
- The document has failed structural coherence in a prior session

For short documents (1-2 sections, single session), the outline can be implicit — but `doc-state.md` is still written at session end if the document is unfinished.
