---
name: go
description: "Use when creating, modifying, testing, or reviewing Go code. Apply Go correctness guidance and the selected lifecycle checks; preserve repository-specific requirements. Apply the selected alpha expectations."
---

# go: alpha

Use the generated lifecycle gate for strict lint, formatting, compilation, and retained-behavior tests. Focus on meaningful happy paths and consequential failures; race and vulnerability checks are not added by this stage unless otherwise required.

When `go` is listed in `.source-code.json` languages, run `python3 scripts/check-source-code.py go` for the configured gate. Otherwise follow existing repository checks; guidance installation alone does not add a runtime profile.

Read [shared guidance](references/common.md) for invariant rules and tool mechanics. Command examples there describe available capabilities; they do not add checks beyond this selected entrypoint and the repository's requirements. When selecting verification, use the installed testing guidance for minimum effective coverage and useful CLI diagnostics. Preserve authored project requirements and explicit authority limits.
