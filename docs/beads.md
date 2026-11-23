# Shared Beads service

The optional `beads` tool runs one Beads HTTP endpoint and one private Dolt SQL server under the native user service manager. Its trial profile selects the workspace, ports, expected Dolt branch, and private history remote. Dispatch remains with the explicitly selected controller. Installing the endpoint does not enroll or migrate tasks, synchronize GitHub issues, or replace Octo's issue lifecycle; its Beads adapter is a separate integration.

Enable `tools.beads = true` in the machine TOML, or include `"beads"` in its sets. `make plan` shows the selection; `make install` installs the catalog-pinned, checksum-verified native binaries and starts the service. Default configuration commands do not install software or start it. Explicit `python3 tools/beads/beads-service.py install` from dotfiles installs and starts only this capability.

| Command | Purpose |
| --- | --- |
| `beads-service start` | Start the installed service, preserving an existing process. |
| `beads-service restart` | Gracefully restart the installed service. |
| `beads-service stop` | Stop and disable it while retaining its data. |
| `beads-service status` | Report endpoint identity, HTTP liveness and database readiness; return nonzero unless ready. |
| `beads-service config` | Validate and print the effective trial profile without starting anything or contacting a service. |
| `beads-service backup` | Explicitly checkpoint and push the entire shared task history to the configured private GitHub repository. |
| `python3 tools/beads/test-beads-service.py` | Exercise ownership, readiness, failure cleanup and workspace protection with controlled native processes. |

The installed `~/.local/bin/beads-service` supports `start`, `restart`, `stop`, `status`, `config`, and `backup` from any directory. Its controller and configuration reader are copied into `~/.local/share/beads-service`, so deleting the installation source worktree does not interrupt the service. Runtime binaries are private and versioned; an existing `bd` on PATH is preserved.

## Source layout

[The Beads capability](../tools/beads/) groups the service controller, strict configuration reader, runtime-update adapter, and service checks. The controller uses Python’s standard library for TOML and JSON validation, native launchd property lists, inherited file-descriptor locks, atomic receipts, and bounded child-process supervision. Bootstrap remains the shell entrypoint for selected installation; source configuration and task state remain separate from the installed controller.

## Runtime updates

Use the shared [project-update lifecycle](project-updates.md) for ongoing maintenance:

```sh
project-update status beads
project-update pull beads
project-update build beads
project-update restart beads
# Or run pull, build and restart together:
project-update update beads
```

The project source is dotfiles, which owns the compatible Beads/Dolt pins. Pulling does not choose an independent upstream latest or change the private task-data repository. Build installs the selected artifacts with `--no-start`, preserving a running service; restart requires a matching staged source fingerprint and unchanged artifact hashes. Local configuration and task storage remain intact. `status` separates verified installed identity from observed service readiness and an unknown running revision. Initial explicit `python3 tools/beads/beads-service.py install` remains available; direct installs can invalidate the updater's installed-identity receipt until staged again. The optional browser UI and manual history checkpoints are separate from runtime updates.

## Trial profile

Installation seeds `$XDG_CONFIG_HOME/beads-service/config.toml` (default `~/.config/beads-service/config.toml`) from [the stock trial profile](../config/beads/trial.toml). Existing TOML, including comments, is preserved. When carrying forward the earlier two-port JSON configuration, installation validates and preserves its port choices, writes a new TOML file, and retains the original JSON unchanged. Ordinary configuration inspection does not create or convert files. If both files exist, TOML is authoritative.

```toml
version = 1
profile = "trial"

[service]
http_port = 8790
sql_port = 3310

[workspace]
database = "octo"
prefix = "octo"
branch = "main"

[history]
remote = "origin"
url = "git+https://github.com/lanej/beads-tasks.git"
mode = "manual"
```

Unknown fields, invalid identifiers or ports, and unsupported scheduling modes are errors. `mode = "manual"` means a history push occurs only through an explicit command; there is no timer. The runtime versions and checksums remain pinned in `bootstrap/tools.toml`. The browser UI is a separate optional trial process; its network listener and hostname do not expose the Beads API or SQL listener.

## Endpoint and storage

The HTTP endpoint defaults to `http://127.0.0.1:8790`; Dolt listens on `127.0.0.1:3310`. Set `service.http_port` and `service.sql_port` in the TOML profile before initializing a new workspace. An existing workspace must have matching native connection settings; a SQL port change requires deliberate reconciliation of that metadata before restarting. Changing the HTTP port requires a restart. Both ports must be distinct integers between 1024 and 65535. An occupied port is an error; the service never selects a replacement or stops another listener.

All clients share the configured database (default `octo`) and workspace at `~/.local/state/beads-service/workspace`. Its Git repository supplies the context required by Beads; it is independent of source repositories and worktrees. Dolt data lives at `~/.local/state/beads-service/dolt`. The service initializes only a missing workspace using the configured database and prefix, verifies the existing server/database connection settings and active Dolt branch, and refuses automatic migration of an existing or incomplete workspace. Changing the profile does not rename, migrate, or branch an existing database. Source branches and worktrees do not select task-database branches. Disabling the tool does not delete its database or stop an installed service.

`~/.local/state/beads-service/endpoint.json` records the endpoint once its database readiness and workspace identity have been observed. It is a discovery record, not a health guarantee; clients must probe current readiness. Shutdown removes the record. A workspace lock prevents a second controller from managing the same database. Multiple external `bd serve` frontends can share Dolt, but this installation intentionally runs only one.

## Lifecycle and health

On startup the controller acquires the workspace lock, checks its fixed ports, starts Dolt, initializes or validates Beads, starts HTTP, and probes database readiness. If either child exits, the controller stops the other and exits unsuccessfully. The manager retries after ten seconds. Shutdown drains HTTP before terminating Dolt, with bounded termination of owned children. It never kills processes by name or port.

macOS uses `com.lanej.beads` under launchd; logs are in `~/.local/state/beads-service/service.log`. Linux uses the user `beads.service`; inspect it with `journalctl --user -u beads.service`. A missing or failing service manager is an installation error; the same installed controller can be run explicitly in the foreground with `beads-service run`.

`GET /healthz` establishes HTTP liveness only. `GET /v0/beads/ready?limit=1` exercises the database. `GET /v0/beads/context` identifies the workspace, database and supported capabilities. The status command requires readiness and the expected workspace/database identity. All listeners bind to numeric loopback addresses. HTTP clients have local write access; Beads HTTP mutations do not execute CLI hooks.

An HTTP integration requires server-backed Dolt: `bd serve` rejects embedded Dolt. The service does not migrate existing embedded databases, install repository hooks, or change agent guidance. Back up the Dolt database using its supported backup/remote facilities; an issues JSONL export is interchange data, not a complete database backup.

## Manual history checkpoints

`beads-service backup` requires the running configured workspace, the expected active branch, an existing named Dolt remote whose URL exactly matches the profile, and a private GitHub repository verified through the authenticated `gh` CLI. Missing or mismatched remotes are reported rather than adopted or repointed. Configure a remote deliberately from the workspace with native `bd dolt remote add NAME URL` before the first push.

The command commits the current Dolt working set, pushes using `--remote NAME --no-adopt` without force, and confirms that `refs/dolt/data` exists on the remote. Git authentication uses the existing GitHub CLI login through a child-process credential helper; global Git configuration and stored credentials are not rewritten. Pushes are serialized per workspace. A checkpoint covers the committed database at that point, not a coordinated snapshot of ongoing agent work or other applications' journals. The recorded source head precedes the push; concurrent writers can advance the database afterward.

`~/.local/state/beads-service/history.json` retains the latest attempt and last confirmed success, including millisecond UTC timestamps, the observed source head, and the remote Git data ref. Status distinguishes never run, running, pushing, succeeded, failed before push, and unconfirmed after a push attempt. A failure does not erase the last success or prove the remote was unchanged; interruption can leave an unfinished attempt requiring inspection. This record is a push receipt, not a restore-verification result.

The selected Beads 1.3.4 / Dolt 2.7.4 pair has demonstrated a private Git-backed round trip using server-mode recovery. Default embedded-mode bootstrap can download this database but cannot reopen it with that version pair. The restored copy needs a writable local initialization to recreate runtime tables such as `leases`. See the private task repository's [recovery procedure](https://github.com/lanej/beads-tasks/blob/main/RECOVERY.md) and [acceptance evidence](https://github.com/lanej/beads-tasks/blob/main/acceptance/git-roundtrip-2026-11-17.json). Restore committed task data in isolation and reconcile controller journals, ownership, and external effects before resuming execution. Neither this profile nor a successful push establishes those recovery guarantees.
