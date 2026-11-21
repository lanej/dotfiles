# Source-code lifecycle

This skill package contains the project’s installed lifecycle policy. Preserve authored repository requirements and follow the installed testing guidance for verification depth. Read `AGENTS.override.md` and the generated `.agents/source-code.md` summary for project routing. Setup and upgrade materialize project choices; ordinary work does not require interpreting configuration to select policy.

Read the installed `references/kinds.md` in this skill package for usage-specific responsibilities. Kind does not prescribe architecture or add generated language commands.

Before choosing application libraries, API protocols, or migration scope, read [the installed tool policy](tool-choices.md). Tool choices are binding agent guidance, not an automated dependency gate.

When creating, extending, or reviewing a CLI, read [CLI construction](../../cli/SKILL.md). It owns the language-tool routing and required `skill` / `skill --topic` discovery contract, subject to project authority, adoption, and compatibility.

Use optional `data-pipeline` and `ui-acceptance` guidance when those packages are installed and relevant to the task. They are selected explicitly; language detection and workstation tool availability do not opt a project into domain architecture or UI gates.

Apply the selected stage consistently across [Builder](../../builder/SKILL.md), [testing](../../testing/SKILL.md), [comments](../../code-comments/SKILL.md), and installed language guidance. Run `python3 scripts/check-source-code.py LANGUAGE` locally and in CI for the selected stage's generated language gate. Explicit project gates remain binding at every stage.

Use `source-code validate` for structural package and pin checks, and `source-code upgrade --dry-run` to preview releases from the installed command’s source checkout while preserving project selections. Change the stage through `source-code setup --authority AUTHORITY --adoption ADOPTION --stage STAGE --dry-run`, review the added or relaxed obligations, then apply it. A stage is the project's chosen assurance level, not proof of readiness or a release version. A policy version identifies the rules; a source revision and file fingerprints identify installed contents. Four-nines reliability requires a separately defined and measured service objective.
