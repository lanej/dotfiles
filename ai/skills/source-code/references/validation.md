# Validate and upgrade project guidance

## Validate and upgrade

Run `source-code validate --repo PATH` to check authored TOML, installed package structure, links, policy metadata, and version pins without running project code. It reports configuration-only validation when no installation exists, and warnings for desired/installed drift; `--strict` fails on those warnings. `--strict` also fails on advisory/customization warnings; `--skills-dir PATH` checks a skill package or tree without requiring an installation. Structural validity does not establish engineering quality or passing application checks.

Use `source-code upgrade --repo PATH --dry-run` to preview updates from the installed command’s source checkout, retaining saved selections. It does not fetch releases automatically. Review policy and skill version changes separately from lifecycle stage changes, then apply the upgrade within the requested scope and validate again. Preserve local customizations; report conflicts, unsupported versions, or partial installations rather than claiming a complete upgrade. Do not hand-edit pins or generated summaries to bypass checks.

Report the target checkout, selected stage and visibility, guidance versus installed check profiles, validation results, and any unresolved conflict. Keep project test results separate from installer validation.
