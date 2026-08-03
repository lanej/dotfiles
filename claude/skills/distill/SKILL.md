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

### 2. Grade Load-Bearing Nature

Break the document into its smallest coherent units — usually one sentence or one discrete fact/claim; a multi-sentence paragraph that stands or falls together can be graded as a single unit. For each unit, assign two independent scores:

- **Load-bearing** (`Essential` / `Supporting` / `Cuttable`): how much the document's purpose depends on this unit surviving. A unit multiple later claims depend on is `Essential` regardless of how it reads locally. A unit that only restates something already established is `Cuttable`.
- **Confidence** (`High` / `Medium` / `Low`): how sure you are of the load-bearing grade above — not confidence that the claim is factually true. `Low` confidence means the unit's necessity is genuinely ambiguous without the author's judgment, not that you didn't look closely.

Grade every unit before sorting — don't stop early once obvious cuts appear.

### 3. Plan Cuts — in plan mode

Sort the graded units: `High`-confidence `Cuttable` first (safest cuts), then `Medium`-confidence `Cuttable`/`Supporting`, then anything `Low`-confidence last (these require a judgment call, not an automatic cut). Work down this ranked list toward the target reduction — the sort order **is** the cut order. Never cut a `Low`-confidence unit silently; it must be called out for explicit review.

Enter plan mode (`EnterPlanMode`). Write the plan file as a structured edit manifest — **not** the document content. The plan file must contain:

**Distill Plan: `<filename>`**

- **Purpose / audience**: one line each
- **Audience assumptions**: the 2–4 things they already know (the cut floor)
- **Target reduction**: e.g., `~55% of current length`

**Graded units** — sorted by confidence (most-confidently-cuttable first), one row per unit:

| Unit | Load-bearing | Confidence | Action | Rationale |
|------|--------------|------------|--------|-----------|
| "..." (§2, sentence 3) | Cuttable | High | Cut | Restates §1's claim verbatim |
| "..." (§3, sentence 1) | Supporting | Low | **Flag — review** | Could be inference the reader needs, or could be filler; ambiguous without author intent |
| "..." (§4, sentence 2) | Essential | High | Keep | §6 and §7 both depend on this figure |
| ... | ... | ... | ... | ... |

**Relocations** (key claims or numbers rescued from Cut units before removing them):
- `"X metric"` from §2 → §4

Do not include full document content beyond the quoted unit text needed for identification. The plan describes edit operations only. Exit plan mode (`ExitPlanMode`) to get user approval before applying anything — resolve all `Flag — review` rows with the user during this approval step, before applying.

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

Compute both word counts with `wc -w` against the actual file — or `git show <sha>:<path> | wc -w` for a before/after commit pair — so the reader can reproduce them. If you exclude structural content (frontmatter, code blocks, tables) from the count, say so on the same line. Never report a bare number whose scope silently differs from what `wc -w` on the real file returns: a prose-only count presented as the file's word count is a fabricated statistic, and it will be caught later by anyone who runs the obvious command.
