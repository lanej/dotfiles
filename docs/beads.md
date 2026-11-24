# Shared Beads service

The optional `beads` tool runs one Beads HTTP endpoint and one private Dolt SQL server under the native user service manager. Its trial profile selects the workspace, ports, expected Dolt branch, and private history remote. Dispatch remains with the explicitly selected controller. Installing the endpoint does not enroll or migrate tasks, synchronize GitHub issues, or replace Octo's issue lifecycle; its Beads adapter is a separate integration.

Enable `tools.beads = true` in the machine TOML, or include `"beads"` in its sets. `make plan` shows the selection; `make install` resolves preinstalled Homebrew binaries on macOS, or installs catalog-pinned, checksum-verified private binaries on Linux, and starts the service. Default configuration commands do not install software or start it. Explicit `python3 tools/beads/beads-service.py install` from dotfiles installs and starts only this capability.

| Command | Purpose |
| --- | --- |
| `beads-service start` | Start the installed service, preserving an existing process. |
| `beads-service restart` | Gracefully restart the installed service. |
| `beads-service stop` | Stop and disable it while retaining its data. |
| `beads-service status` | Report endpoint identity, HTTP liveness and database readiness; return nonzero unless ready. |
| `beads-service config` | Validate and print the effective trial profile without starting anything or contacting a service. |
| `beads-service backup` | Explicitly checkpoint and push the entire shared task history to the configured private GitHub repository. |
| `python3 tools/beads/test-beads-service.py` | Exercise ownership, readiness, failure cleanup and workspace protection with controlled native processes. |

The installed `~/.local/bin/beads-service` supports `start`, `restart`, `stop`, `status`, `config`, and `backup` from any directory. Its controller and configuration reader are copied into `~/.local/share/beads-service`, so deleting the installation source worktree does not interrupt the service. Linux runtime binaries are private and versioned. macOS resolves `bd` and `dolt` through Homebrew formula prefixes, not an arbitrary `bd` on PATH. Neither platform replaces a user's CLI.

[The Neovim task explorer](neovim-beads.md) browses the project graph and opens editable Markdown task buffers. Explicit saves use the same HTTP authority and revision guards, independently of chat or a worker.

## Source layout

[The Beads capability](../tools/beads/) groups the service controller, strict configuration reader, runtime-update adapter, and service checks. The controller uses Python’s standard library for TOML and JSON validation, native launchd property lists, inherited file-descriptor locks, atomic receipts, and bounded child-process supervision. The capability-local `tool.toml` is composed with the legacy catalog by the configuration resolver; Beads staging fingerprints only its own recipe and source inputs. Bootstrap remains the shell entrypoint for selected installation; source configuration and task state remain separate from the installed controller.

## macOS installation and compatibility

Install the Homebrew `beads` and `dolt` formulae explicitly before selecting this service. The installer never runs `brew install`, `brew upgrade`, or private runtime downloads on macOS. It discovers `brew` on PATH, falling back to `/opt/homebrew/bin/brew` or `/usr/local/bin/brew`, queries each formula's prefix, and records absolute resolved Cellar executable paths. This works without Homebrew on launchd's PATH and keeps a later `opt` symlink change from silently selecting another runtime. Do not remove the selected Cellar versions with Homebrew cleanup while they are installed or running.

Preflight runs only version and help commands in a disposable directory, with isolated HOME, XDG configuration/data/state/cache directories and Dolt root, and bounded timeouts. Ambient Beads/Dolt overrides are removed; Homebrew auto-update and analytics and Dolt update checks are disabled for these probes. It requires stable Beads >=1.3.4, <2.0.0 and Dolt >=2.7.4, <3.0.0, plus the server, initialization, SQL, history and loopback-binding CLI flags used by the controller. The Beads version floor and `serve --addr` contract select the versioned HTTP API; help checks alone cannot establish its real HTTP behavior or task-data compatibility. Formula binaries must be executable and read-only, as required by the existing native child-identity guard; the installer does not chmod Homebrew files. Missing formulae, writable binaries, unsupported versions, failed probes or absent capabilities abort before changing installed controller links, runtime manifest, launchd definition, configuration or task data. Diagnostics identify the failing tool/contract and ask for explicit Homebrew repair before retrying.

To stage without starting or restarting anything:

```sh
python3 tools/beads/beads-service.py install --no-start
```

This still installs the controller and service definition; it is not a dry run. For an existing service prefer `project-update build beads` so artifact receipts and guarded activation remain coordinated. Preflight does not contact the existing endpoint or open a database, migrate it, or initialize a workspace.

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

The project source is dotfiles, which owns Linux pins and macOS compatibility floors. Pulling does not upgrade Homebrew or change the private task-data repository. On macOS, upgrade formulae explicitly under a maintenance plan, retain the old Cellar versions, then build to resolve and preflight the new pair. Build installs the selected artifacts with `--no-start`, preserving a running service, and records the actual Homebrew versions; restart requires a matching staged source fingerprint and unchanged artifact hashes. Local configuration and task storage remain intact. `status` separates verified installed identity from observed service readiness and an unknown running revision. Initial explicit `python3 tools/beads/beads-service.py install` remains available; direct installs can invalidate the updater's installed-identity receipt until staged again. The optional browser UI and manual history checkpoints are separate from runtime updates.

### Rollback and delivery gates

Keep the prior controller release, runtime manifest, updater receipt and selected binaries before staging an upgrade; do not delete the old private runtime when moving macOS to Homebrew. Rollback is an explicit maintenance operation: restore/reselect the previously accepted controller/runtime pair, then restage it and use guarded activation. An old Homebrew pair must remain available through its formula prefixes to be reselected by this installer. Do not hand-edit an active release's manifest, repoint a running owner's binaries, bypass checkpoint refusal, or overwrite the database with an older copy. If old executables are unavailable or data has changed incompatibly, stop and plan recovery from a separately verified backup rather than attempting an automatic downgrade. Installing an older binary does not undo database changes.

`node --test scripts/test-beads-inputs.mjs` checks the actual workflow path filters using the locked task-runtime validation dependencies. The Beads recipe selects service, editor, integration and composed-configuration checks; the worktree-manager integration also consumes it through full Make configuration resolution. Independent Git hooks, worktree policy, treehouse and directory-picker inputs stay in the legacy catalog. Changing a shared resolver or workflow still selects its actual consumers. The test runs the real Make configuration entrypoint in a disposable checkout, rejects a missing recipe, includes removed-input counterexamples, and treats unsupported filter syntax conservatively.

`python3 tools/beads/test-beads-service.py HomebrewRuntime` is socket-free and protects resolver, preflight failures, staging and Linux provisioning decisions with controlled command responses. It is not native compatibility evidence. Before merging this runtime change, independent review must assess the exact candidate, and separate external gates must demonstrate native startup/readiness/restart, Studio guarded operations, and restored-copy task-data compatibility with the selected Homebrew pair. These gates remain held until actually observed; do not run them against the live service as part of isolated verification. The dispatch lead rechecks overlapping open PRs before publication.

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

Unknown fields, invalid identifiers or ports, and unsupported scheduling modes are errors. `mode = "manual"` means a history push occurs only through an explicit command; there is no timer. `tools/beads/tool.toml` owns the Beads recipe, Linux runtime pins and checksums; those versions are macOS compatibility floors within the same major release. The browser UI is a separate optional trial process; its network listener and hostname do not expose the Beads API or SQL listener.

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
