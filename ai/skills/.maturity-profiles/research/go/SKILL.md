---
name: go
description: "Use when creating, modifying, testing, or reviewing Go code. Apply Go correctness guidance and the selected lifecycle checks; preserve repository-specific requirements. Apply the selected research expectations."
---

# go: research

Use the generated lifecycle gate for compile feedback and exercise the real experiment. Keep the useful steel-thread protection; do not automatically add the full lint, race, and vulnerability suite unless existing project requirements or consequences call for it.

When `go` is listed in `.source-code.json` languages, run `python3 scripts/check-source-code.py go` for the configured gate. Otherwise follow existing repository checks; guidance installation alone does not add a runtime profile.

Read [shared guidance](references/common.md) for invariant rules and tool mechanics. Command examples there describe available capabilities; they do not add checks beyond this selected entrypoint and the repository's requirements. When selecting verification, use the installed testing guidance for minimum effective coverage and useful CLI diagnostics. Preserve authored project requirements and explicit authority limits.
