---
name: go
description: "Use when creating, modifying, testing, or reviewing Go code. Apply Go correctness guidance and the selected lifecycle checks; preserve repository-specific requirements. Apply the selected production expectations."
---

# go: production

Use the full generated profile and the project’s relevant recovery and operational evidence. Retain supported behavior and compatibility, with independent review for consequential interactions. Passing race and vulnerability checks do not establish unobserved behavior.

When `go` is listed in `.source-code.json` languages, run `python3 scripts/check-source-code.py go` for the configured gate. Otherwise follow existing repository checks; guidance installation alone does not add a runtime profile.

Read [shared guidance](references/common.md) for invariant rules and tool mechanics. Command examples there describe available capabilities; they do not add checks beyond this selected entrypoint and the repository's requirements. When selecting verification, use the installed testing guidance for minimum effective coverage and useful CLI diagnostics. Preserve authored project requirements and explicit authority limits.
