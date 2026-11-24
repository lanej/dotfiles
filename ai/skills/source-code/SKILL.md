---
name: source-code
description: Use when installing, inspecting, validating, or upgrading project engineering profiles with the source-code CLI, choosing tracked or shadow setup, or changing lifecycle stage and language checks. Excludes ordinary coding work under an existing project policy.
---

# Source-code project setup

This user-level skill manages the `source-code` CLI and project installations. It does not choose engineering policy for ordinary coding tasks; follow the target repository’s installed guidance. Reuse the intended checkout and preserve authored instructions, linked sources, customizations, and existing gates.

Inspect `source-code --help` and the selected subcommand’s help for the installed version. `source-code skill` prints this entrypoint without reading project configuration. Read references from the installed skill package, or use `source-code skill --topic NAME` when the installed CLI advertises that option.

Read the matching reference before performing these operations:

| Task | Read | CLI topic |
| --- | --- | --- |
| Resolve project policy, explain desired/installed choices, inspect language detection | [Inspection](references/inspection.md) | `inspection` |
| Configure stage, authority, adoption, visibility, skills, or language profiles | [Setup](references/setup.md) | `setup` |
| Check package integrity, inspect drift, or upgrade retained selections | [Validation and upgrades](references/validation.md) | `validation` |

Preview the exact requested setup or upgrade arguments before applying them. Review selected files, conflicts, and relaxed or added obligations. Apply only within the authorized scope; keep project customizations in authored instructions, since selected generated regular files refresh with backups. Preserve explicit authority and adoption choices rather than inferring them from hosting.

Keep installer validation, project test outcomes, and release readiness separate. Report the target checkout, effective profile, and unresolved limits. Setup and skill discovery do not authorize staging, committing, pushing, publishing, messaging, or applying unrelated workstation configuration.
