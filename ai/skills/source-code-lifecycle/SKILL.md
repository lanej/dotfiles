---
name: source-code-lifecycle
description: Use when working in a project installed by source-code setup, selecting its research, alpha, beta, or production expectations, or changing its lifecycle stage.
---

# Source-code lifecycle

Read the project's `.source-code.json` before selecting engineering effort. It records `schema_version`, `policy_version`, `stage`, installed `languages`, pinned skill versions, optional project `kind`, and language-detection evidence. Detection selects guidance; `languages` separately identifies installed generated check profiles. Read `AGENTS.override.md` for the generated project routing and version summary, preserving the existing `AGENTS.md`. Read [the lifecycle contract](references/lifecycle.md) for stage expectations, transitions, and limits. If the project has no policy, preserve existing requirements; do not infer a lower stage from apparent immaturity.

When the policy selects a `kind`, read [project kind guidance](references/kinds.md) for service, library, or tool obligations. Kind is explicit and independent of stage; do not infer it or use it to prescribe architecture.

Apply the selected stage consistently across [Builder](../builder/SKILL.md), [testing](../testing/SKILL.md), [comments](../code-comments/SKILL.md), and installed language guidance. Run `python3 scripts/check-source-code.py LANGUAGE` locally and in CI for the selected stage's generated language gate. Explicit project gates remain binding at every stage.

Use `source-code validate` for structural package and pin checks, and `source-code upgrade --dry-run` to preview releases from the installed command’s source checkout while preserving project selections. Change the stage through `source-code setup --stage STAGE --dry-run`, review the added or relaxed obligations, then apply it. A stage is the project's chosen assurance level, not proof of readiness or a release version. A policy version identifies the rules; a source revision and file fingerprints identify installed contents. Four-nines reliability requires a separately defined and measured service objective.
