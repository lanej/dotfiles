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

  Before continuing, answer: *What can this audience be assumed to know?* List 2–4 things. These become the cut floor — content the audience already holds is cuttable regardless of how well it's written.

- **Core concepts**: What are the 3–5 ideas the document cannot work without?
- **Key claims**: What assertions must survive for the document to remain true?

### 2. Map Dependencies

Before classifying anything, for each section or major block, identify:

- **What it enables**: Which later sections depend on this one to be interpretable?
- **What depends on it**: Which claims or arguments earlier in the document does this section require to land?

A section with no downstream dependents is a Cut candidate. A section that multiple later sections require is Keep regardless of local salience. Write the map as a brief list: `[Section] → unlocks [Section(s)]` or `[Section] ← requires [Section(s)]`. If no dependencies exist, say so explicitly.

### 3. Plan Cuts

Before editing, produce a cut plan. For each section or major block, apply in order — first matching rule wins:

- **Cut** if: redundant with another section, decorative/transitional only, or audience can be assumed to know it (from step 1)
- **Cut** if: has no downstream dependents (from step 2) AND doesn't directly establish a key claim
- **Compress** if: carries signal the audience needs but is overwritten. Compression is complete when no sentence can be removed without losing a key claim, and no sentence can be shortened without distorting its meaning.
- **Keep** if: a downstream section requires it to be interpretable, OR it states a key claim that cannot be paraphrased without distortion

For each section marked **Cut**: before finalizing the cut, list any key claims or load-bearing numbers it contains and relocate them to a surviving section. Then apply the cut.

State the target reduction (e.g., "~60% of current length") and what you expect to lose vs. preserve.

### 4. Apply

Rewrite the document according to the plan:

- Delete cut material entirely — no ellipses, no summaries of what was removed
- Compress kept material: one idea per sentence, no hedging, no throat-clearing
- Preserve structure only where it aids navigation; collapse trivial sections

### 5. Verify

Before reading the distilled version, generate 5–8 questions a reader would need the original to answer — questions that test the key claims, dependencies, and core concepts identified in steps 1–2. Write them down. Then read the distilled version and answer each question from it alone.

- If all questions are answerable: distillation is complete.
- If a question is unanswerable: restore the minimum content required to answer it, then re-run only the failed questions.

The questions must be specific and falsifiable — not "is the concept clear?" but "what is the threshold for X?" or "what happens if Y fails?" Generic yes/no questions about purpose are insufficient; they pass even when load-bearing specifics are lost.

## Constraints

- **Never remove meaning** — only remove words that carry no meaning
- **Never paraphrase inaccurately** — if you can't shorten a claim without distorting it, keep it verbatim
- **Preserve precision** — vague compression is worse than verbosity
- **Respect the audience** — don't add explanation the audience doesn't need, don't remove explanation they do
- **Never write to disk** — return the distilled document in the conversation; do not overwrite or create any file unless the user explicitly directs you to

## QMD Files

When the input is a `.qmd` file, apply these rules before the standard cut process:

- **Frontmatter** (YAML between `---` delimiters): always keep — it is configuration, not prose
- **Setup/library cells** (imports, `style.apply_style()`, `data = {}`): cut — boilerplate with no content value
- **Data-loading cells** (`cache.read_cache()`, scalar extraction): keep — they feed inline `{python}` expressions in the prose; removing them breaks the document
- **Figure rendering cells**: keep — figures carry visual evidence the prose references
- **LaTeX blocks** (`{=latex}` raw blocks, `\needspace`, title block inputs, etc.): ignore and leave untouched — they are required for PDF layout and identity

Apply the standard distill process only to the prose sections between these structural elements.

## Output Format

Return:

1. **Cut plan** (brief — 5–12 lines): dependency map (section → unlocks), audience assumptions, classification decisions with rationale
2. **Distilled document**: the rewritten content
3. **Stats**: original word count → distilled word count
