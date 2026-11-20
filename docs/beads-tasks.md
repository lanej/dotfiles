# Beads task authority

The shared Beads HTTP service owns task briefs, work status, constraints, evidence and next actions. Pi runs ordinary worker sessions, worktree manager owns new coding checkouts, and Paseo supplies the task panel and mobile access. SQLite retains local execution bindings, managed checkout identities and durable delivery records; task content there is a refreshable projection.

## Configure the service

Select `tools.beads = true` and follow [Beads service setup](beads.md). Inspect `beads-service status` for readiness and the service URL. Read `GET /v0/beads/context` to obtain its `project_id`, then configure the intended task host explicitly:

```text
PASEO_TASKS_BEADS_URL=http://127.0.0.1:8790
PASEO_TASKS_BEADS_PROJECT_ID=<project_id from the intended service>
```

Set `PASEO_TASKS_BEADS_TOKEN_FILE` when the endpoint requires bearer authentication. The file supplies one token; credentials are never placed in the URL. Remote hosts use a deliberately configured authenticated service endpoint or existing secure tunnel. The task adapter does not create an SSH connection, replica, embedded database or server process. Beyond loopback, use a confidential authenticated transport as required by the Beads service contract.

Startup verifies the project identity, server-backed Dolt mode and required API capabilities. Every task request carries `Bd-Project-Id`, so a replacement or misdirected endpoint cannot silently bind the host to another workspace. Retired `PASEO_TASKS_BEADS_DIR`, `PASEO_TASKS_BEADS_AUTHORITY` and `PASEO_TASKS_BEADS_SSH_HOST` settings fail with an actionable error. They never initialize or migrate storage.

## Task records and guarded writes

Each new task has a stable `tasks-<task-UUID>` Beads ID. Native title, description, acceptance criteria, priority, status and assignee remain independently inspectable. Flat `paseo.*` metadata retains the accepted task context and host/task identity. Native updates to unrelated metadata keys survive a task edit. Per-field metadata merges and native expected-status/expected-assignee guards are applied together in Beads' transaction; same-field edits retain Beads' last-writer semantics.

The application uses asynchronous HTTP requests through `openapi-fetch` and generated types. Requests time out after 30 seconds and refuse redirects. Mutating requests are never retried blindly. Creation uses its stable ID for read-only reconciliation after a lost response; writes whose outcome cannot be confirmed remain errors requiring inspection. A service outage never permits an enrolled task to fall back to stale SQLite content.

Local SQLite transactions serialize task projection, execution bookkeeping and dispatch reservations while awaiting required Beads effects. This preserves local admission ordering and rollback behavior, but the two databases are not one atomic transaction: an HTTP write can commit before local persistence fails. The next successful read reconciles authoritative task content. Locks can remain held across bounded HTTP calls, so this remains a single-host pilot design; measure responsiveness before wider enrollment.

Existing local task databases without a matching service project pin are refused. No automatic task migration or history import is provided. Closed embedded pilot records and their backups remain in their original repository; new work uses the shared service.

## Generated API contract

`paseo-tasks/api/beads-1.3.4.yaml` is the upstream MIT-licensed [Beads v1.3.4 OpenAPI contract](https://github.com/gastownhall/beads/blob/v1.3.4/internal/httpapi/spec/openapi.v0.yaml). `npm --prefix paseo-tasks run generate:beads` regenerates the TypeScript contract. Generation checks detect drift; do not edit generated types by hand. The upstream REST contract is consumed as published rather than replaced with a custom application API.

Native acceptance creates disposable Dolt and Beads HTTP processes, exercises task creation, independent CLI edits, worker ownership, closed-task refusal and retained feedback, and removes only its own processes and workspace. It never writes to the configured shared service or migrates live tasks. Existing package tests protect delivery, recovery and host routing. Actual Pi/Paseo deployment and remote transport still require host-specific acceptance.

## Runtime and operator interfaces

Task integration code uses TypeScript and the pinned official Pi SDK for session types, parsing and active-context selection. Observation reads one session snapshot without opening a mutable Pi session manager or rewriting worker history. Identity, malformed-record and ancestry guards remain necessary because Pi's tolerant parser alone cannot establish ownership or a safe completion checkpoint. The scoped Undici override applies its security patch while retaining the pinned Pi API; revisit it when updating Pi.

New coding workers require native worktree manager. Missing tooling fails before checkout creation; there is no raw Git or Treehouse allocation fallback. Adopted checkouts retain their ownership, and reconciliation of a legacy allocation cannot request a new one.

[The Zellij fleet design (#362)](https://github.com/lanej/dotfiles/issues/362) defines the local operator direction: explicit Beads root → Zellij session, immediate workstream → tab, active authorized Pi attempt → live pane. Deeper hierarchy remains in a floating tree; blocker edges do not become parentage. Selection focuses the existing Pi TUI, with native attention navigation taking precedence. Pane presence, process liveness and task status remain separate observations. This workspace mapping is a design/prototype scope; the task plugin does not install it.
