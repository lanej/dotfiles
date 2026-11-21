---
name: go
description: "Use when creating, modifying, testing, or reviewing Go code. Apply Go correctness guidance and the selected lifecycle checks; preserve repository-specific requirements. Apply the selected alpha expectations."
---

# go: alpha

Protect retained behavior and meaningful happy paths. Cover consequential failures with focused regression checks and keep provisional interfaces explicit.

<!-- source-code:verification -->

Read [shared guidance](references/common.md) for invariant rules and tool mechanics. Command examples there describe available capabilities; they do not add checks beyond this selected entrypoint and the repository's requirements. When selecting verification, use the installed testing guidance for minimum effective coverage and useful CLI diagnostics. Preserve authored project requirements and explicit authority limits.
