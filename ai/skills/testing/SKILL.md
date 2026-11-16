---
name: testing
description: Use when resolving current-maturity testing guidance in a legacy source-code installation or maintaining the canonical testing package.
---

# Select the current testing guidance

Read the project's `.source-code.json` to identify its configured stage. Load exactly `../.maturity-profiles/<stage>/testing/SKILL.md`, relative to this canonical testing directory, and follow that file for project work. Do not load the other maturity files. Without a configured stage, preserve the repository's requirements and resolve the missing project policy rather than assuming a maturity.

New source-code installations link directly to the selected entrypoint. This selector preserves existing linked installations until setup or upgrade switches their discovery link. Change maturity through setup or upgrade. Skill versions, project maturity, and observed verification remain separate facts.
