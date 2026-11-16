# Troubleshoot authentication, history, and uploads

## Troubleshooting

- **Authentication or permissions:** verify with `info --no-defaults`, then check token scope and access to the intended organization/project. Read [permissions and scopes](https://docs.sentry.io/api/permissions/) for the specific operation; do not assume a CI upload token can read issue data.
- **Unexpected `.env` warning:** fix the relevant configuration if the task requires it. If the invocation intentionally uses other configuration sources, `SENTRY_LOAD_DOTENV=0 sentry-cli ...` disables `.env` loading for that invocation.
- **Missing commits:** inspect the checkout, remote mapping, and available Git history before changing commit association options.
- **Upload failures:** inspect the command's exit status and error output. Do not introduce `SENTRY_ALLOW_FAILURE` merely to make CI green; it can hide missing debugging artifacts.
- **More diagnostics:** use `--log-level info`, then `debug` if necessary. Review and redact diagnostic output before sharing it.

Read the [configuration reference](https://docs.sentry.io/cli/configuration/) or [release guide](https://docs.sentry.io/cli/releases/) when the installed help does not explain the behavior being investigated.
