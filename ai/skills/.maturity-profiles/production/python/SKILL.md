---
name: python
description: "Use when creating, modifying, testing, or reviewing Python code, or adopting its strict correctness profile. Use uv for Python dependencies and tools; preserve repository requirements. Apply the selected production expectations."
---

# python: production

Use the full generated Python profile and relevant recovery or operational evidence. Cover consequential behavior comprehensively while keeping tests diagnostic and maintainable. Observe the actual supported runtime and dependencies.

When `python` is listed in `.source-code.json` languages, run `python3 scripts/check-source-code.py python` for the configured gate. Otherwise follow existing repository checks; guidance installation alone does not add a runtime profile.

Read [shared guidance](references/common.md) for invariant rules and tool mechanics. Command examples there describe available capabilities; they do not add checks beyond this selected entrypoint and the repository's requirements. When selecting verification, use the installed testing guidance for minimum effective coverage and useful CLI diagnostics. Preserve authored project requirements and explicit authority limits.
