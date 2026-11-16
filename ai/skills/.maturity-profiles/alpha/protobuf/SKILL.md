---
name: protobuf
description: "Use when creating, modifying, reviewing, or validating Protobuf schemas. Apply schema correctness guidance and the selected lifecycle checks; preserve repository-specific requirements. Apply the selected alpha expectations."
---

# protobuf: alpha

Use the generated lifecycle gate for compilation, the JSON-string field rule, strict lint, and check-only formatting. Protect retained happy-path serialization behavior and consequential constraints.

When `protobuf` is listed in `.source-code.json` languages, run `python3 scripts/check-source-code.py protobuf` for the configured gate. Otherwise follow existing repository checks; guidance installation alone does not add a runtime profile.

Read [shared guidance](references/common.md) for invariant rules and tool mechanics. Command examples there describe available capabilities; they do not add checks beyond this selected entrypoint and the repository's requirements. When selecting verification, use the installed testing guidance for minimum effective coverage and useful CLI diagnostics. Preserve authored project requirements and explicit authority limits.
