# Locate the shared terminal context

## Notice the context

Prefer the native collaboration helpers:

```sh
zellij-context inspect
zellij-context inspect --json
```

`inspect` checks the session's current server identity and returns native pane/tab metadata and client information. JSON distinguishes `available`, `selection_required`, and `unavailable`; unavailable inspection exits unsuccessfully. Caller pane/tab are present only when inherited context matches a live terminal pane.

When caller context is missing, `inspect` lists sessions without choosing one. Select the session from verified task context or the user's choice and inspect it with `--session NAME`. Do not choose an unrelated session just because it exists. Restricted socket access can make a live session appear exited or inaccessible; treat that status as uncertain and reconcile through the permitted tool or approval path before concluding it has exited.

Set `zellij_session` to the verified session name for the examples below, rather than continuing to rely on the inherited environment. Set `zellij_tab_id` from live tab and pane metadata before creating a view; an explicit verified tab ID is required when caller-pane context is unavailable.

Read `zellij-pane --help` for helper options. If helpers are unavailable, use `zellij --help` and the relevant subcommand's `--help`: this dotfiles runtime supports `list-panes --all --json`, `list-tabs --all --json`, `list-clients`, and targeted `dump-screen`. Other installations and already-running servers may expose fewer capabilities. A replaced executable does not update an existing server.

Use pane IDs, tab IDs, titles, running commands, and geometry to locate the relevant view. Focus is client-specific; the agent's pane need not be the pane the user is viewing. Keep discovery scoped to the task instead of reading every pane's contents.
