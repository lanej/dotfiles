# Beads task authority

Beads owns task briefs, work status, constraints, evidence and next actions in a dedicated repository on the Mac. `bd list`, `bd show` and `bd history` read that record without Paseo. Pi and the Paseo task panel remain clients. SQLite retains execution bindings, managed checkouts, current activity, pending feedback and delivery receipts; its task content is a refreshable projection for enrolled tasks.

## Install and initialize

Enable `tools.beads = true` in the selected machine TOML, inspect `make plan`, then run `make install`. The catalog pins Beads 1.3.4. The release installer verifies the published archive checksum and installed binary version, and preserves unmanaged or modified binaries. Configuration alone neither installs Beads nor initializes task storage.

Initialize explicitly:

```sh
make beads-coordinator-init
```

The default directory is `~/.local/share/paseo-coordinator`; select another dedicated repository with `BEADS_COORDINATOR_DIR=/absolute/path`. Initialization uses embedded Dolt and does not start a database server. Embedded mode admits one writer at a time; application writes are serialized by the existing SQLite transaction and Beads enforces its storage lock against other CLI processes. A competing CLI operation can report contention; inspect current state before retrying. Server mode is optional for simultaneous writers: initialize with `BEADS_STORAGE_MODE=server` only after installing Dolt separately. Initialization preserves an existing workspace and refuses an implicit mode change.

The initializer skips Beads agent instructions and Git hooks, preserving existing canonical skills and host integrations. It records one authority UUID in Beads and prints the two environment settings required by the task service:

```text
PASEO_TASKS_BEADS_DIR=/absolute/path/to/coordinator
PASEO_TASKS_BEADS_AUTHORITY=<printed UUID>
```

Apply these to the intended Paseo daemon's environment at an idle maintenance boundary after validating the plugin. No daemon restart or worker migration occurs during installation or initialization. New tasks created by a configured service use Beads. Existing tasks retain their source until explicitly migrated. Removing the configuration cannot make enrolled tasks fall back to stale SQLite content.

## Inspect and edit independently

Run native commands from the dedicated repository:

```sh
bd list --all --json
bd show tasks-<existing-task-UUID> --json
bd history tasks-<existing-task-UUID> --json
```

Task UUIDs and host-qualified API addresses remain stable. The corresponding bead ID is `tasks-<UUID>`. Native title, description, acceptance criteria and priority remain authoritative. Structured acceptance is written as a JSON array; a human-readable replacement becomes one acceptance criterion. Other task fields use flat `paseo.*` metadata keys, which are visible in `bd show --json`. For example, `bd update ID --metadata '{"paseo.progress":"Observed result"}'` changes progress.

The adapter patches only changed fields using Beads' native atomic metadata merge, preserving unknown keys and concurrent changes to unrelated fields. Same-field concurrent CLI edits follow native last-writer semantics; this is not full-row compare-and-swap. The existing task API revision check still protects competing application updates. Status and assignee preconditions protect native worker claims. A CLI reassignment blocks further execution, delivery and worker updates until ownership is reconciled; it cannot retract an already admitted message or running turn. Closing, blocking or deferring an unbound task prevents automatic launch.

## Migrate one task first

Pause the selected task, wait for a verified idle worker with no pending native question, and run the existing task-service CLI:

```sh
printf '%s\n' '{"serverId":"<host>","taskId":"<existing UUID>"}' |
  npm --prefix paseo-tasks run maintain -- beads-migrate --json
```

The host validates its identity and worker activity. Before enrollment it creates a consistent SQLite snapshot at `<tasks-state>/backups/before-beads-<UUID>-<attempt>.sqlite`. Migration preserves the source row, task UUID, worker conversation, checkout and pending delivery records. It verifies Beads publication before recording enrollment. Retrying uses the same bead ID; a different existing record is a conflict. A Beads write followed by a local projection failure remains visible through native CLI inspection, and the next successful read reconciles the local content and coordinator report.

Verify native CLI readback, the task panel, retained feedback, worker follow-ups and restart recovery before resuming the pilot or migrating another task. Do not restore a pre-migration snapshot over a live database; retain it for explicit recovery. Use Beads' Dolt-native backup facility for database history; JSONL exports are interchange data rather than backups.

## Remote execution hosts

Remote task services use the same Mac authority, never an independently writable replica. Set `PASEO_TASKS_BEADS_SSH_HOST` to an existing noninteractive SSH alias for the Mac, use the Mac's absolute repository path as `PASEO_TASKS_BEADS_DIR`, and pin its authority UUID. The adapter executes native `bd` on that host with bounded, batch-mode SSH and quoted arguments. Configure the Mac's noninteractive PATH to expose `bd`. Unavailable SSH or a mismatched authority blocks task operations; it does not initialize local storage or redirect to another host. Native SSH inspection works independently of Paseo as well.

Distributed Beads and broader harness deployment are tracked in [issue #349](https://github.com/lanej/dotfiles/issues/349). OctoManager remains responsible for PR lifecycle work; adopting Beads does not add a PR watcher or authorize merges.

## Verification boundary

The native acceptance detector uses real embedded Beads and disposable Git/SQLite repositories. It exercises migration, direct CLI changes, claims, reassignment, unrelated concurrent edits, interrupted projection, source backup and pending feedback. It never publishes or merges a PR. Existing package tests retain the task-service delivery and host-routing checks. SSH transport and actual Pi/Paseo deployment require acceptance on the intended hosts before claiming live rollout completion.
