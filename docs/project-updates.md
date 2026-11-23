# Update projects through verified activation

`project-update update --all` succeeds only when the selected installations are running, ready, and their affected sessions are restored. The eight registered projects own their native lifecycle controls; the driver stages builds, checkpoints affected targets, orders replacements, and verifies the result. Legacy processes without a trustworthy native checkpoint stay intact and return incomplete activation.

Use `make project-updates` (also `make update-projects`) for all projects, or `make update-zellij` for Zellij and its affected application owners. Make fails on incomplete activation and reports recipe error 3; use the CLI directly when distinguishing exit codes. uv, Python 3.11+, and Git are required. Invoke `./bin/project-update` directly, or run `make shell` to link it after applying the change to the normal dotfiles source.

```sh
project-update status --all --fetch
project-update update --all
project-update verify --all
project-update wait RUN_ID
project-update build intent
project-update restart beads
project-update update zellij --dry-run
```

Commands retain one JSON result array on stdout. Target reports include expected and running artifact identities, native process ownership, readiness, and session restoration. Project and target reasons explain incomplete results. Exit codes are **0** verified completion, **1** operational failure, **2** invalid usage, and **3** incomplete activation. A healthy response or installation receipt alone never establishes the running version. `verify` is read-only; an unknown identity cannot produce success.

## Stage first, then checkpoint and restore

`update` pulls shared checkouts once, stages every selected build, and inventories selected targets plus affected consumers before disruption. `restart` uses the selected installations without pulling or rebuilding. Already-current targets avoid replacement; a consumer still checkpoints when a prerequisite will change. Failed targets retain their evidence while independent targets continue. Failed prerequisites block dependent activation.

The detached coordinator survives replacement of the invoking terminal. It requests native checkpoints bound to verified ownership, process-start identities, native session IDs, and an operation UUID. Each target has at most 60 seconds to confirm a safe checkpoint. Refused or uncertain checkpoints preserve their owners; cancellation never escalates automatically to forced termination. Services activate before consumers, and Zellij replaces identified servers last. Application owners delegate terminal-owned restoration so each conversation launches once.

Managed Octo, Router, and Beads services retire through their native checkpoint owner and normal exit before OS job replacement. Their startup policy must support stopping after successful exit; a legacy or unknown policy refuses checkpointing before draining work. Final verification binds the restored process incarnation as well as its loaded artifact identity.

Native restoration preserves conversation IDs, Pi transcript paths and checkpointed branches, working directories, layouts, and recoverable input. Interrupted or uncertain effects remain recorded and are never replayed automatically. A changed process incarnation, missing session, different selected artifact, or unverified restoration returns 3. There is no cross-project rollback.

The command prints the run UUID and `project-update wait RUN_ID` recovery command. Private operation records live under `${XDG_STATE_HOME:-~/.local/state}/dotfiles/project-update/RUN_ID`, outside target process trees, with owner-only directories and files. `wait` observes the existing operation and returns its recorded result. Later updates reconcile unresolved native requests through read-only verification; they do not repeat cancellation or launches with uncertain outcomes. Original-process recovery can remove a native admission fence only when its exact owner is still present. Retain recovery records until restoration is verified.

Octo and Studio declare Bun minimums through `package.json` and use the shared executable on PATH. Explicit builds can provision that shared runtime and record successful installation requirements; status and restart never install runtimes. Dotfiles combines the [project declarations](setup-requirements.md#project-runtime-requirements) with its baseline and preserves a newer installed version.

## Eight registered projects

| Project | Selected source and native activation |
| --- | --- |
| `octo-manager` | `~/src/oss/octo-manager`; frozen dependencies and the revision-specific installer stage an immutable release with `--stage-only`. Its private selection receipt supplies the expected artifact through that release's CLI. Global launchers, hooks, configuration and service definitions promote after the exact native checkpoint. Legacy or incompatible owners remain running. Active effects without a confirmed native checkpoint refuse replacement, and scheduler pause state is restored against the replacement incarnation. |
| `bedrock-router` | `~/src/bedrock-router`; the owner builder embeds an image identity, then the native installer stages with `--no-start --keep-env --preserve-mcp`. Native admission fencing cancels tracked requests, waits for acknowledgement, and records interrupted requests without replay. Replacement requires the exact checkpointed service owner. |
| `beads` | Dotfiles' catalog-pinned Beads/Dolt pair and immutable supervisor release. The supervisor binds its child executable images, drains HTTP before Dolt, and refuses checkpointing during a history operation. Task data and local TOML remain in place. |
| `intent` | `~/src/intent`; native installation plus platform-specific remote staging. Existing profiles discover local and paired remote brokers, including configured `dev` and `dev2` targets. Native ownership deduplicates aliases and preserves routing IDs, stable socket paths, and existing SSH connections. Unreachable targets remain incomplete independently. |
| `keylease` | `~/src/1password-agent`; native immutable releases and process-bound broker controls. Supported replacement ends the old credential owner and requires fresh approval. Active conversations lacking authoritative admission, input, or checkpoint metadata remain intact. Signing keys and credential values are never written to update records. |
| `studio` | `~/src/studio`; environment-provided Bun satisfies the project's minimum and builds a versioned extension bundle with its selected Pi host. Native checkpoint metadata captures the transcript/session/branch and recoverable draft. Unowned children, queued input, unsafe active tools, admitted asynchronous commands, or background runtime authority lacking native checkpoints refuse cancellation; managed relaunch verifies the loaded host bytes and bundle. |
| `zellij` | Dotfiles' curated runtime and compatible plugins. Native session metadata supplies persistent IDs, pane bindings, loaded plugin identities, and private activation layouts. Restoration requires application checkpoints and a verified independent user-terminal environment broker. Legacy or generic panes without native ownership remain intact. See [the activation contract](../zellij/ACTIVATION.md). |
| `worktree-manager` | Dotfiles plus the existing latest-stable Git selection and pinned manager. Both installed binaries must be selected by PATH on subsequent invocation and match the selected artifacts. There is no persistent service to stop. |

Zellij's upstream default branch remains a mirror; the selected curated runtime and compatible pins stay authoritative. Building installs selected runtime/helper/plugin/configuration targets without stopping existing servers. Derived activation support records its native patch and artifact identities instead of silently selecting upstream main. Interactive restoration inherits the environment of a verified terminal broker; the coordinator's environment is not substituted and full environments are not serialized.

Intent and Keylease remain separate installations. Their adapters retain clean-source checks, native build verification, and immutable releases. Profile discovery does not create SSH approval configuration, change authentication, or enable transports. Unsupported legacy brokers and conversations require deliberate owner-specific recovery before a later update can complete.

Beads maintenance does not push or pull task history, migrate a database, or alter the existing trial TOML. `pull beads` updates dotfiles. `build beads` stages the curated runtime; readiness and the loaded controller/child identities establish activation. The staging receipt records managed source fingerprints and artifact hashes, preserving dirty-source evidence without presenting it as a clean revision. History pushes remain explicit through `beads-service backup`.

## Preserve source selection and local work

`pull` resolves the remote's default branch, fetches it, and fast-forwards a checkout already on that branch. It prefers `upstream` when present, otherwise `origin`, unless the registry selects a remote. Nonconflicting local edits and untracked files survive; conflicting files, unfinished Git operations, topic branches, detached heads, local commits, and diverged history block the pull. The command never stashes, resets, switches branches, or pushes. Native projects may additionally require clean source before installation.

Projects sharing a checkout pull it once per invocation. `pull_sources = true` invokes an adapter's explicit additional source pull afterward; worktree manager uses it to select stable Git. Build and restart do not refresh sources implicitly. Mutations are locked per affected checkout, independently of other Git tools. `status` reports checkout and installation state; upstream information is cached or unknown unless `--fetch` is requested. `--dry-run` prints actions without fetching, locking, building, or restarting.

## Add a native adapter

The registry is `config/project-updates.toml`; `--config PATH` selects a replacement registry. Paths expand `~` and `{dotfiles}`; argv also expands `{python}`. Commands execute in the checkout without a shell and receive the action as their final argument.

```toml
[projects.example]
path = "~/src/example"
command = ["./scripts/project-update"]
lifecycle = "consumer"
depends_on = ["intent"]
```

Adapters implement `build`, `status`, `inventory`, `checkpoint`, `restart`, `restore`, and `verify`. Native activation actions emit the versioned target contract validated by `scripts/project_update_activation.py`, including explicit checkpoint confirmation and restoration dispositions. Establish the owner's authoritative lifecycle contract before adding its adapter. A successful launch request is insufficient evidence of activation. An optional `clean` removes only project-owned build artifacts and never runs automatically; bundled adapters preserve releases, sessions, dependencies, and state.

Run `make test-project-update` for the driver and adapter detector. Native owner detectors separately exercise real checkpoints, cancellation, process guards, and restoration; controlled adapters do not establish workstation or platform acceptance.
