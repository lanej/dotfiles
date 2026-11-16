---
name: reflection
description: Review the current conversation or a supplied session transcript for recurring misunderstandings and propose focused improvements. Use when asked to reflect on a session, invoke reflection, or diagnose repeated corrections.
---

# Reflection

Read [the shared reflection instructions](references/reflection.md) and apply them to the current conversation or the explicitly supplied transcript. Return concise, evidence-backed findings inline. Use the visible conversation directly when it provides the needed evidence; no Claude session ID or Claude transcript is required in Codex.

If earlier turns are unavailable or summarized, state the evidence limit. When the user supplies a transcript path, read that transcript; do not substitute another session or scan unrelated conversations. Cite concrete corrections and distinguish recurring patterns from one-off mistakes. Give each actionable finding its affected behavior, appropriate owner, and proposed correction; prefer repairing existing guidance over adding general rules.

Handle reflection inline by default. If the user requests independent reflection, give the available reflection agent the exact transcript or bounded conversation evidence and require findings only. If delegation is unavailable, state the limit and return the inline review.

Do not edit files, write memories, commit, message others, or dispatch implementation work as part of reflection. A legacy `auto` argument only requests findings without interactive questions. Applying proposed corrections requires a separate user instruction.
