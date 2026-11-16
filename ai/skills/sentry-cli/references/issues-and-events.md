# Inspect issues and events and change triage state

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
