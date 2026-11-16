---
name: source-code-lifecycle
description: "Use when working in a project installed by source-code setup or changing its lifecycle stage. Apply the configured maturity, authority, and adoption policy. Select only the configured maturity guidance."
---

# Select the current source-code-lifecycle guidance

Read the project's `.source-code.json` to identify its configured stage. Load exactly `../.maturity-profiles/<stage>/source-code-lifecycle/SKILL.md`, relative to this canonical skill directory. Do not load other maturity files. Without a configured stage, preserve existing repository requirements and use the shared technical guidance without assuming a maturity.

New source-code installations link directly to the selected entrypoint. This selector preserves existing linked installations until setup or upgrade switches their discovery link. Read [shared guidance](references/common.md) when needed; the selected entrypoint controls maturity-specific expectations.
