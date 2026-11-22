# Related engineering guidance

Before choosing application libraries, API protocols, or migration scope, follow the authority and adoption policy in the installed skill entrypoint.

When creating, extending, or reviewing a CLI, read [CLI construction](../../cli/SKILL.md). It owns the language-tool routing and required `skill` / `skill --topic` discovery contract, subject to project authority, adoption, and compatibility.

Use optional `data-pipeline` and `ui-acceptance` guidance when those packages are installed and relevant to the task. They are selected explicitly; language detection and workstation tool availability do not opt a project into domain architecture or UI gates.
