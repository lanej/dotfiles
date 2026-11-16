---
name: code-comments
description: "Use when deciding whether to add a source comment, writing or revising comments, or reviewing comment quality. Apply the conventional code comment specification. Excludes PR discussion comments and general prose editing. Select only the configured maturity guidance."
---

# Select the current code-comments guidance

Read the project's `.source-code.json` to identify its configured stage. Load exactly `../.maturity-profiles/<stage>/code-comments/SKILL.md`, relative to this canonical skill directory. Do not load other maturity files. Without a configured stage, preserve existing repository requirements and use the shared technical guidance without assuming a maturity.

New source-code installations link directly to the selected entrypoint. This selector preserves existing linked installations until setup or upgrade switches their discovery link. Read [shared guidance](references/common.md) when needed; the selected entrypoint controls maturity-specific expectations.
