## doc-state.md Schema

`doc-state.md` lives alongside the document being written (same directory, same base name with `-state` suffix, or explicitly named `doc-state.md` for single-document directories). It is the structural contract for the document — not a summary of content, but a record of decisions.

### Format

```markdown
# Doc State: [document title]

**File**: [relative path to document]
**Last updated**: [date]
**Status**: outline | drafting | revising | final

## Locked Outline

[The agreed section structure. Once approved, do not restructure without explicitly reopening this section with the user.]

- # Section 1: [title]
  - [key claim or purpose of section]
- # Section 2: [title]
  - [key claim or purpose of section]
...

## Key Arguments

[One sentence per argument the document must make. These are settled — do not relitigate.]

1. [Argument]
2. [Argument]

## Decisions Made

[Structural and content decisions that were explicitly considered and resolved. Do not reopen these.]

- **[Decision]**: [What was decided and why. What was rejected.]

## Do Not Revisit

[Topics, framings, or structural choices that were considered and deliberately excluded. Reopening these wastes the session.]

- [Item]: [Brief reason it was excluded]

## Next Section

[The specific section or task to work on next. Clear enough that a cold session can pick it up without re-reading the whole document.]

## Session Handoff

[What happened in the last session. What changed. Where editing stopped. Any unresolved questions that are genuinely open (not settled).]
```

### Rules

- `doc-state.md` is updated at the end of every structural pass, before the session ends.
- The Locked Outline is frozen after user approval. Prose edits do not change it.
- Structural changes require explicit user approval and a new `doc-state.md` write.
- The Session Handoff section is overwritten each session — it reflects only the most recent session.
