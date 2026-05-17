---
name: distill
description: Reduce a document to its minimum effective dose — the least information needed to fully convey the purpose and key concepts. Use when asked to simplify, condense, distill, or strip a document down to essentials. Triggers on: "simplify this", "distill this", "trim this down", "what's the minimum I need", "make this shorter without losing anything important".
---

# Distill

Reduce a document to its minimum effective dose: the smallest amount of information that delivers full understanding.

**Model:** Use claude-opus-4-7 for this task — it requires deep comprehension before cutting.

## Process

### 1. Read and Comprehend

Read the entire document before cutting anything. Identify:

- **Purpose**: What is this document for? What decision, action, or understanding does it enable?
- **Audience**: Who reads this and what do they already know?
- **Core concepts**: What are the 3–5 ideas the document cannot work without?
- **Key claims**: What assertions must survive for the document to remain true?

### 2. Plan Cuts

Before editing, produce a cut plan. For each section or major block, classify:

- **Keep**: Essential to purpose or core concepts — cannot be removed
- **Compress**: Carries real signal but overwritten — shorten in place
- **Cut**: Redundant, decorative, transitional, or already implied

State the target reduction (e.g., "~60% of current length") and what you expect to lose vs. preserve.

### 3. Apply

Rewrite the document according to the plan:

- Delete cut material entirely — no ellipses, no summaries of what was removed
- Compress kept material: one idea per sentence, no hedging, no throat-clearing
- Preserve structure only where it aids navigation; collapse trivial sections

### 4. Verify

Read the distilled version cold. Ask:

- Does it still serve the original purpose?
- Are all core concepts present and clear?
- Is anything load-bearing missing?

If yes to the last question, restore the minimum needed and re-verify.

## Constraints

- **Never remove meaning** — only remove words that carry no meaning
- **Never paraphrase inaccurately** — if you can't shorten a claim without distorting it, keep it verbatim
- **Preserve precision** — vague compression is worse than verbosity
- **Respect the audience** — don't add explanation the audience doesn't need, don't remove explanation they do

## Output Format

Return:

1. **Cut plan** (brief — 3–10 lines): what you're keeping, compressing, and cutting, and why
2. **Distilled document**: the rewritten content
3. **Stats**: original word count → distilled word count
