---
name: typescript
description: "Use when writing or reviewing TypeScript, enforcing exhaustive state handling, or adopting strict compiler and typed lint checks in new or existing repositories. Apply the selected production expectations."
---

# typescript: production

Use the full generated TypeScript profile with relevant recovery, rollout, and operational evidence. Protect consequential supported behavior without redundant or brittle tests.

When `typescript` is listed in `.source-code.json` languages, run `python3 scripts/check-source-code.py typescript` for the configured gate. Otherwise follow existing repository checks; guidance installation alone does not add a runtime profile.

Read [shared guidance](references/common.md) for invariant rules and tool mechanics. Command examples there describe available capabilities; they do not add checks beyond this selected entrypoint and the repository's requirements. When selecting verification, use the installed testing guidance for minimum effective coverage and useful CLI diagnostics. Preserve authored project requirements and explicit authority limits.
