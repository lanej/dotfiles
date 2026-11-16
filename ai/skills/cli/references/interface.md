# Construct the command interface

## Choose the existing language tools

The installed source-code tool-choice catalog owns the parser and presentation selections: Commander for TypeScript/JavaScript, Cobra and Charmed for Go, Typer with Rich/Textual for Python, and clap with Ratatui for Rust. Read that catalog and the project’s authority/adoption settings before applying a choice. Use the project’s installed language skill for correctness and verification details. Keep this procedure focused on CLI behavior rather than copying those profiles.

Reuse the selected framework’s commands, argument validation, option parsing, help, and error handling. Do not write a parallel flag parser for documentation discovery. Presentation libraries serve presentation; preserve clean machine output when stdout is consumed by another program.

## Define invocation and observable results

Group commands by user capability. Identify required inputs, defaults, resource/account selection, output formats, exit outcomes, and consequential side effects. Keep common tasks discoverable through normal `--help`; the `skill` interface teaches workflows, boundaries, and troubleshooting without replacing syntax help.

Write the requested result to stdout and actionable diagnostics to stderr. For machine-readable modes, keep stdout parseable and free of banners, progress, or unsolicited prose. Make failure distinguishable from a legitimate empty result. Preserve established exit codes and output contracts when extending an interface.

Use explicit task targets for operations that change data or remote state. A printed example does not authorize executing it. Do not silently broaden a command’s scope, suppress failures, change a configured account, or turn inspection into mutation. Keep the user’s authorized task separate from any optional publish/deploy/install step.

## Extend existing CLIs safely

Inspect current commands, parser registration, startup effects, documentation, callers, and existing tests before changing the interface. Reuse established paths and protect retained behavior through representative real invocations. Follow shared/upstream conventions and project agreement; a local source-code installation does not grant stack or interface migration authority.

If `skill` already names an application capability, preserve it and report the discovery-name collision. Agree on compatibility or migration before introducing a competing meaning. Do not silently use another command name while claiming compliance with the standard discovery contract.

Scale verification to consequences and the installed lifecycle. Use existing command tests or acceptance checks for the actual behavior; avoid tests that merely count handlers or assert source strings. Test an important malformed input or failure when it could otherwise look like success. Automation for enforcing application-wide compliance remains separate follow-up work.
