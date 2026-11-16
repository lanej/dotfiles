# Installed interface, credentials, and targets

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
