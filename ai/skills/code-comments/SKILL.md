---
name: code-comments
description: Use when deciding whether to add a source comment, writing or revising comments, or reviewing comment quality. Apply the conventional code comment specification. Excludes PR discussion comments and general prose editing.
---

# Code Comments

Use this guide for routine comment edits and reviews:

- Comment when it materially reduces the effort needed to understand or safely change code. Useful explanations of behavior and phase labels are welcome; omit obvious narration and decoration.
- Prefer clearer code when it carries the information better. Do not extract functions solely to eliminate useful prose.
- Put caller contracts in native documentation, local reasoning beside the code, and broad decisions in design documentation with useful local context.
- Distinguish current behavior, intent, assumptions, and known defects. Keep guarantees bounded to what is established; do not write reassuring claims over a behavior problem.
- Preserve useful ordinary comments and repository conventions. Update affected comments, leave unrelated comments alone, and avoid bulk tagging or annotation quotas.

When purpose or searchability helps, use lowercase `type(scope): explanation` inside normal comment syntax; scope is optional. Types: `rationale` for decisions, `warning` for hazards, `workaround` for temporary accommodations and their removal conditions, `todo` for concrete planned work, and `fixme` for known defects. Put useful ownership and references in the explanation.

For reviews, identify missing, misleading, or redundant information, its effect on the reader, and a concrete improvement. A missing tag alone is not a defect. Report behavior problems outside the requested scope.

Read [the full specification](references/standard.md) only when changing the convention, resolving a detail not covered here, or needing extended examples or editor-compatibility guidance. It remains the canonical standard; routine edits do not require loading it.
