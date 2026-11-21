# Select project kind guidance

Read the installed `.source-code.json`. When `kind` is selected, read only its matching reference:

| Configuration | Read |
| --- | --- |
| `kind = service` | [Service obligations](kind-service.md) |
| `kind = library` | [Library obligations](kind-library.md) |
| `kind = tool` | [Tool obligations](kind-tool.md) |

An omitted kind preserves existing requirements; do not infer a category from files or dependencies. An unknown value requires resolving the policy rather than choosing a substitute. Kind describes how consumers use the project, independently of language, architecture, and lifecycle stage. Scale the selected obligations through the installed lifecycle entrypoint.

Kind does not select architecture, install deployment tools, or add generated language commands. Preserve existing repository gates. Project-wide kind is one optional selection; honor authored directory scope without synthesizing directory overrides.
