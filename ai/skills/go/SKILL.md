---
name: go
description: "Use when creating, modifying, testing, or reviewing Go code. Apply Go correctness guidance and the selected lifecycle checks; preserve repository-specific requirements. Select only the configured maturity guidance."
---

# Select the current go guidance

Read the project's `.source-code.json` to identify its configured stage. Load exactly `../.maturity-profiles/<stage>/go/SKILL.md`, relative to this canonical skill directory. Do not load other maturity files. Without a configured stage, preserve existing repository requirements and use the shared technical guidance without assuming a maturity.

New source-code installations link directly to the selected entrypoint. This selector preserves existing linked installations until setup or upgrade switches their discovery link. Read [shared guidance](references/common.md) when needed; the selected entrypoint controls maturity-specific expectations.
