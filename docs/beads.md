# Shared Beads service

The optional `beads` tool runs one Beads HTTP endpoint and one private Dolt SQL server under the native user service manager. Octo owns dispatch and execution authority. Installing the endpoint does not enroll issues, synchronize GitHub, or replace Octo's issue lifecycle; its Beads adapter is a separate integration.

Enable `tools.beads = true` in the machine TOML, or include `"beads"` in its sets. `make plan` shows the selection; `make install` installs the catalog-pinned, checksum-verified native binaries and starts the service. Default configuration commands do not install software or start it. Explicit `make beads-install` installs and starts only this capability.

| Command | Purpose |
| --- | --- |
| `make beads-start` | Start the installed service, preserving an existing process. |
| `make beads-restart` | Gracefully restart the installed service. |
| `make beads-stop` | Stop and disable it while retaining its data. |
| `make beads-status` | Report endpoint identity, HTTP liveness and database readiness; return nonzero unless ready. |
| `make test-beads-service` | Exercise ownership, readiness, failure cleanup and workspace protection with controlled native processes. |

The installed `~/.local/bin/beads-service` supports `start`, `restart`, `stop` and `status` from any directory. Its controller is copied into `~/.local/share/beads-service`, so deleting the installation source worktree does not interrupt the service. Runtime binaries are private and versioned; an existing `bd` on PATH is preserved.

## Endpoint and storage

The HTTP endpoint defaults to `http://127.0.0.1:8790`; Dolt listens on `127.0.0.1:3310`. Override `http_port` and `sql_port` in `$XDG_CONFIG_HOME/beads-service/config.json` (default `~/.config/beads-service/config.json`), then restart. Both ports must be distinct integers between 1024 and 65535. An occupied port is an error; the service never selects a replacement or stops another listener.

All clients share the `octo` database and workspace at `~/.local/state/beads-service/workspace`. Its Git repository supplies the context required by Beads; it is independent of source repositories and worktrees. Dolt data lives at `~/.local/state/beads-service/dolt`. The service initializes only a missing workspace, verifies the existing server/database connection settings, and refuses automatic migration of an existing or incomplete workspace. Disabling the tool does not delete its database or stop an installed service.

`~/.local/state/beads-service/endpoint.json` records the endpoint once its database readiness and workspace identity have been observed. It is a discovery record, not a health guarantee; clients must probe current readiness. Shutdown removes the record. A workspace lock prevents a second controller from managing the same database. Multiple external `bd serve` frontends can share Dolt, but this installation intentionally runs only one.

## Lifecycle and health

On startup the controller acquires the workspace lock, checks its fixed ports, starts Dolt, initializes or validates Beads, starts HTTP, and probes database readiness. If either child exits, the controller stops the other and exits unsuccessfully. The manager retries after ten seconds. Shutdown drains HTTP before terminating Dolt, with bounded termination of owned children. It never kills processes by name or port.

macOS uses `com.lanej.beads` under launchd; logs are in `~/.local/state/beads-service/service.log`. Linux uses the user `beads.service`; inspect it with `journalctl --user -u beads.service`. A missing or failing service manager is an installation error; the same installed controller can be run explicitly in the foreground with `beads-service run`.

`GET /healthz` establishes HTTP liveness only. `GET /v0/beads/ready?limit=1` exercises the database. `GET /v0/beads/context` identifies the workspace, database and supported capabilities. The status command requires readiness and the expected workspace/database identity. All listeners bind to numeric loopback addresses. HTTP clients have local write access; Beads HTTP mutations do not execute CLI hooks.

An HTTP integration requires server-backed Dolt: `bd serve` rejects embedded Dolt. The service does not migrate existing embedded databases, install repository hooks, or change agent guidance. Back up the Dolt database using its supported backup/remote facilities; an issues JSONL export is interchange data, not a complete database backup.
