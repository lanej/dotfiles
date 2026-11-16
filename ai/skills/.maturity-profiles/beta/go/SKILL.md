---
name: go
description: "Use when creating, modifying, testing, or reviewing Go code. Apply Go correctness guidance and the selected lifecycle checks; preserve repository-specific requirements. Apply the selected beta expectations."
---

# go: beta

Use the full generated profile: formatting, module tidiness, strict lint, uncached race tests, and reachable-vulnerability analysis. Protect adopted behavior, important errors, and affected compatibility and integration boundaries.

When `go` is listed in `.source-code.json` languages, run `python3 scripts/check-source-code.py go` for the configured gate. Otherwise follow existing repository checks; guidance installation alone does not add a runtime profile.

Read [shared guidance](references/common.md) for invariant rules and tool mechanics. Command examples there describe available capabilities; they do not add checks beyond this selected entrypoint and the repository's requirements. When selecting verification, use the installed testing guidance for minimum effective coverage and useful CLI diagnostics. Preserve authored project requirements and explicit authority limits.
