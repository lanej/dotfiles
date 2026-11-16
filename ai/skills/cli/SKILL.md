---
name: cli
description: Use when creating, extending, or reviewing a command-line interface in a source-code project, including parser selection, command/output contracts, and progressive agent guidance through skill and skill --topic commands.
---

# CLI construction

Read [the project tool-choice policy](../source-code-lifecycle/references/tool-choices.md) before selecting the CLI stack. Use the matching installed language guidance (`typescript`/`javascript`, `go`, `python`, or `rust`); select missing guidance through source-code setup rather than inventing a second tool catalog. Preserve the project’s stage, authority, adoption, established stack, and compatibility contracts.

CLIs built under this policy must expose `TOOL skill` as a compact Markdown entrypoint and `TOOL skill --topic NAME` for task-specific guidance. Keep essential constraints and a usable topic index in the entrypoint. Discovery must be read-only and work without project configuration, credentials, network access, or application startup. Use the selected language’s command framework for these commands and normal help.

Read the matching references before designing or changing the interface:

| Task | Read |
| --- | --- |
| Commands, arguments, language tools, output streams, compatibility, and errors | [Interface construction](references/interface.md) |
| Bundled skill content, named topics, failure behavior, and discovery verification | [Agent discovery contract](references/agent-discovery.md) |

Apply the contract to new independent CLI surfaces when project authority and adoption permit it. Adding discovery to an existing CLI requires the task’s authorized scope; do not overwrite an existing `skill` command or break callers. Report a collision or unsupported contract as a concrete gap and resolve its compatibility or migration scope explicitly.

Exercise the actual command path with representative inputs and inspect its outputs and effects. Keep human help, machine-readable results, diagnostics, documentation discovery, and application execution distinct. A stage label, package check, or successful documentation print does not establish that the application works.
