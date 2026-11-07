---
name: sentry-cli
description: Use when working with sentry-cli to inspect Sentry issues, events, projects, or releases; manage release and deployment records; upload source maps or debug symbols; or troubleshoot CLI authentication and configuration.
---

# sentry-cli

Use the `sentry-cli` executable. Sentry also provides a separate developer CLI named `sentry`; its commands and flags are different.

## Discover the installed interface

```bash
command -v sentry-cli
sentry-cli --version
sentry-cli --help
sentry-cli issues list --help
```

Examples below were checked against version 3.8.0. Read the relevant subcommand's `--help` before using unfamiliar options or adapting examples to another version. If the executable is missing, read the [installation docs](https://docs.sentry.io/cli/installation/) and use the repository's dependency conventions.

## Authentication and target

Reuse configured credentials. Prefer `SENTRY_AUTH_TOKEN` from the existing environment or secret provider; avoid putting tokens in command arguments, logs, or tracked files. Do not print `.env`, `.sentryclirc`, or the complete environment to diagnose configuration.

Configuration can come from environment variables, `.env`, and INI files named `.sentryclirc`. The CLI searches upward from the working directory for project configuration and also loads defaults from `~/.sentryclirc`. Explicit command options override configured defaults. Check the working directory when commands unexpectedly use another server or project.

| Variable | Purpose |
|---|---|
| `SENTRY_AUTH_TOKEN` | Authenticate API operations |
| `SENTRY_URL` | Server URL; defaults to `https://sentry.io/` |
| `SENTRY_ORG` | Organization ID or slug |
| `SENTRY_PROJECT` | Project ID or slug |
| `SENTRY_DSN` | DSN for ingestion operations such as sending events |

Use `sentry-cli info` to verify authentication and defaults. Use `sentry-cli info --no-defaults` when testing authentication without an organization or project. A DSN is not a substitute for an API auth token when listing issues or managing releases.

When interactive credential setup is requested, `sentry-cli login` saves the token to the discovered project `.sentryclirc`, or the global config if no project config exists. Use `sentry-cli login --global` to save it globally. For a self-hosted server use `sentry-cli --url https://sentry.example.com/ login`, adding `--global` when global storage is intended.

For commands below, replace the example organization and project with verified values:

```bash
sentry-cli organizations list
sentry-cli projects list --org example-org
```

Pass `--org` and `--project` explicitly when the task's target differs from configured defaults. Keep the configured server unless the task specifies another one.

## Inspect issues and events

```bash
sentry-cli issues list --org example-org --project example-project \
  --query 'is:unresolved' --pages 1 --max-rows 20

sentry-cli issues list --org example-org --project example-project --id 123456789

sentry-cli events list --org example-org --project example-project \
  --pages 1 --max-rows 20
```

Quote the complete issue query as one argument. Use [Sentry search syntax](https://docs.sentry.io/concepts/search/) for environment, release, and other filters; no query means no filtering. `events list` in 3.8.0 has no `--query` option.

`--pages` bounds fetched pages (100 items per page); `--max-rows` limits printed rows. Start with a small bound and increase it when the task requires more. Report those limits when describing results: a bounded listing does not establish an organization-wide total or prove that no other issues exist.

Issue IDs identify grouped problems; event IDs identify individual occurrences. Keep them distinct. Issue and event listings in 3.8.0 produce tables and have no `--json` flag. Do not invent `issues get`, `events get`, or assume listing output includes a full stack trace. For structured data, event detail, or an unsupported filter, read the relevant [Sentry API docs](https://docs.sentry.io/api/) and use an available authenticated API integration.

Use `--show-tags` or `--show-user` on event listings only when the task needs that data; event content can include customer information.

### Change issue status

Status changes affect remote triage state. Use the authorization already given for the task and target the selected issue IDs. A request to investigate an error does not authorize resolving or muting it.

```bash
sentry-cli issues resolve --org example-org --project example-project --id 123456789
sentry-cli issues list --org example-org --project example-project --id 123456789
```

Other available actions are `mute` and `unresolve`. `--all` and `--status` can select many issues; use them only when the requested scope includes that bulk change. The list command's `--query` is not an option on these mutation commands.

## Releases and deployment records

```bash
sentry-cli releases list --org example-org --project example-project
sentry-cli releases info --org example-org --project example-project 'example-project@1.2.3'
sentry-cli deploys list --org example-org --project example-project --release 'example-project@1.2.3'
```

Releases are shared across an organization. Reuse the application's actual SDK release identifier; choose a project-specific identifier when independent projects otherwise share version names.

For an authorized release workflow, these are the individual steps:

```bash
sentry-cli releases new --org example-org --project example-project 'example-project@1.2.3'
sentry-cli releases set-commits --org example-org --project example-project 'example-project@1.2.3' --auto
sentry-cli releases finalize --org example-org --project example-project 'example-project@1.2.3'
sentry-cli deploys new --org example-org --project example-project \
  --release 'example-project@1.2.3' --env production
```

Use the steps required by the existing pipeline. `set-commits --auto` uses the current Git checkout; verify that it represents the release being recorded. For an explicit range, use `--commit 'owner/repo@previous-sha..current-sha'` with the repository name registered in Sentry. Diagnose missing history before using `--ignore-missing`, which changes the associated commit range.

In 3.8.0, deployments use top-level `deploys` commands. Creating a deployment record or finalizing a release changes Sentry metadata; it does not deploy application code or verify what is serving. Record a completed deployment only after the deployment workflow establishes its outcome, then verify the Sentry record with `deploys list` or `releases info`.

## Source maps and debug symbols

For a JavaScript build that uses Debug IDs:

```bash
sentry-cli sourcemaps inject --dry-run ./dist
sentry-cli sourcemaps inject ./dist
sentry-cli sourcemaps upload --org example-org --project example-project ./dist --wait
```

Generate source maps first. Injection modifies local JavaScript and matching source maps, so apply it to the intended build output before upload and deployment. Ship those same injected artifacts; rebuilding afterward can break the match. If the build integration already injects Debug IDs, follow that integration's workflow.

For Debug ID uploads, `--release` and `--dist` are optional. Add them when the application's artifact workflow requires them, and match the SDK values exactly. Read the [source map upload guide](https://docs.sentry.io/platforms/javascript/sourcemaps/uploading/cli/) when configuring SDK or build compatibility, URL prefixes, or release-based matching.

For native debug information:

```bash
sentry-cli debug-files check ./path/to/debug-file
sentry-cli debug-files upload --org example-org --project example-project ./path/to/symbols --wait
```

Inspect upload output and processing errors. Successful upload and processing establish artifact availability; verify a matching event to establish that its stack trace is correctly symbolicated. `sourcemaps explain` is unavailable in 3.8.0; use current Sentry troubleshooting tools rather than older examples.

## Troubleshooting

- **Authentication or permissions:** verify with `info --no-defaults`, then check token scope and access to the intended organization/project. Read [permissions and scopes](https://docs.sentry.io/api/permissions/) for the specific operation; do not assume a CI upload token can read issue data.
- **Unexpected `.env` warning:** fix the relevant configuration if the task requires it. If the invocation intentionally uses other configuration sources, `SENTRY_LOAD_DOTENV=0 sentry-cli ...` disables `.env` loading for that invocation.
- **Missing commits:** inspect the checkout, remote mapping, and available Git history before changing commit association options.
- **Upload failures:** inspect the command's exit status and error output. Do not introduce `SENTRY_ALLOW_FAILURE` merely to make CI green; it can hide missing debugging artifacts.
- **More diagnostics:** use `--log-level info`, then `debug` if necessary. Review and redact diagnostic output before sharing it.

Read the [configuration reference](https://docs.sentry.io/cli/configuration/) or [release guide](https://docs.sentry.io/cli/releases/) when the installed help does not explain the behavior being investigated.
