---
name: distill
description: 'Reduce a document to its minimum effective dose — the least information needed to fully convey the purpose and key concepts. Use when asked to simplify, condense, distill, or strip a document down to essentials. Triggers on: "simplify this", "distill this", "trim this down", "what''s the minimum I need", "make this shorter without losing anything important".'
---

# Distill

Reduce a document to its minimum effective dose: the smallest amount of information that delivers full understanding.

**Model:** Use claude-opus-4-7 for this task — it requires deep comprehension before cutting.

## Process

### 1. Read and Comprehend

Read the entire document. Identify:

- **Purpose**: What is this document for? What decision, action, or understanding does it enable?
- **Audience**: Who reads this and what do they already know? List 2–4 assumptions — content the audience holds is cuttable regardless of how well it's written.
- **Core concepts**: The 3–5 ideas the document cannot work without.
- **Key claims**: Assertions that must survive for the document to remain true.

### 2. Map Dependencies

For each section or major block, identify what it unlocks downstream and what it requires upstream. Write the map as: `[Section] → unlocks [Section(s)]`. A section with no downstream dependents is a Cut candidate. A section multiple later sections require is Keep regardless of local salience.

### 3. Plan Cuts — in plan mode

Enter plan mode (`EnterPlanMode`). Write the plan file as a structured edit manifest — **not** the document content. The plan file must contain:

**Distill Plan: `<filename>`**

- **Purpose / audience**: one line each
- **Audience assumptions**: the 2–4 things they already know (the cut floor)
- **Target reduction**: e.g., `~55% of current length`
- **Dependency map**: `[Section] → unlocks [Section(s)]`, concise list

**Edit decisions** — one row per section/block:

| Section | Action | Rationale |
|---------|--------|-----------|
| Intro | Cut | Audience already knows context; no downstream dependents |
| Background | Compress | Needed by §3 but overwritten — 3 sentences → 1 |
| ... | ... | ... |

**Relocations** (key claims or numbers rescued from Cut sections before removing them):
- `"X metric"` from §2 → §4

Do not include any document content in the plan. The plan describes edit operations only. Exit plan mode (`ExitPlanMode`) to get user approval before applying anything.

### 4. Apply

After plan approval, rewrite the document according to the plan:

- Delete cut material entirely — no ellipses, no summaries of what was removed
- Compress kept material: one idea per sentence, no hedging, no throat-clearing
- Preserve structure only where it aids navigation; collapse trivial sections

### 5. Verify

Before writing the final version, generate 5–8 questions a reader would need the original to answer — questions testing key claims, dependencies, and core concepts from steps 1–2. Answer each from the distilled version alone.

- If all answerable: distillation is complete.
- If a question fails: restore the minimum content required to answer it, then re-run only the failed questions.

Questions must be specific and falsifiable — not "is the concept clear?" but "what is the threshold for X?" or "what happens if Y fails?"

## Constraints

- **Never remove meaning** — only remove words that carry no meaning
- **Never paraphrase inaccurately** — if you can't shorten a claim without distorting it, keep it verbatim
- **Preserve precision** — vague compression is worse than verbosity
- **Respect the audience** — don't add explanation the audience doesn't need, don't remove explanation they do
- **Write to disk, don't echo** — after plan approval, overwrite the source file in place. Do not return the full document text in the conversation. If the input was pasted inline (no file path), ask the user for a destination path before applying.

## QMD Files

When the input is a `.qmd` file, apply these rules before the standard cut process:

- **Frontmatter** (YAML between `---` delimiters): always keep — it is configuration, not prose
- **Setup/library cells** (imports, `style.apply_style()`, `data = {}`): cut — boilerplate with no content value
- **Data-loading cells** (`cache.read_cache()`, scalar extraction): keep — they feed inline `{python}` expressions in the prose; removing them breaks the document
- **Figure rendering cells**: keep — figures carry visual evidence the prose references
- **LaTeX blocks** (`{=latex}` raw blocks, `\needspace`, title block inputs, etc.): ignore and leave untouched — they are required for PDF layout and identity

Apply the standard distill process only to the prose sections between these structural elements.

**Figure verification**: After identifying which figure cells to keep, locate the rendered PNGs in `{project}_files/figure-pdf/` and read each one using the Read tool. Verify that what the figure actually shows supports the claims made in the distilled prose. If a figure contradicts or fails to support a claim, surface the discrepancy rather than silently keeping both.

## Output Format

After plan approval and apply:

1. **Edit summary**: one line per section showing action and word-count delta — e.g., `Cut §1 Intro (−120w)`, `Compressed §3 Background: 200→80w`, `Merged §6+§7 (−60w)`
2. **Stats**: `original_words → distilled_words (X% reduction)`
