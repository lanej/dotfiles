---
name: sentry-cli
description: Use when working with sentry-cli to inspect Sentry issues, events, projects, or releases; manage release and deployment records; upload source maps or debug symbols; or troubleshoot CLI authentication and configuration.
---

# sentry-cli

Use the `sentry-cli` executable; the separate `sentry` developer CLI has different commands. Check the installed version and relevant subcommand’s `--help`. The references retain examples checked against 3.8.0; verify unfamiliar options before adapting them.

Reuse configured credentials without printing tokens, configuration files, or the complete environment. Verify the server, organization, and project before operating. Investigating an error does not authorize resolving or muting it, uploading artifacts, or changing release metadata. Read the matching reference:

| Task | Read |
| --- | --- |
| Discover commands, check authentication, select the server/org/project | [Configuration](references/configuration.md) |
| List bounded issues/events or perform authorized triage changes | [Issues and events](references/issues-and-events.md) |
| Inspect or record releases, commits, and deployments | [Releases](references/releases.md) |
| Inject/upload source maps or native debug symbols | [Artifacts](references/artifacts.md) |
| Diagnose permissions, configuration, missing commits, or upload failures | [Troubleshooting](references/troubleshooting.md) |

Preserve the difference between issue groups and individual events, printed row limits and fetched data, metadata records and actual deployments, and uploaded artifacts and confirmed symbolication. Verify the consequential outcome rather than inferring it from one successful command. Do not hide failures or disclose customer event data unnecessarily.
