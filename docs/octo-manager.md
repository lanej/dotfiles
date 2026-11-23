# Octo Manager

Octo publishes caller-written GitHub PRs through local format validation and a durable pending receipt, without requiring the daemon. Its optional daemon monitors enrolled PRs and returns actionable checks and review feedback to the owning session. Install it explicitly before using [repository-selected PR publication](octo-pr-submission.md). Neither the default configuration nor the `ai` and `workstation` sets enable Octo's local service or native hooks; configuration does not install software automatically.

## Enable

The optional [shared Beads service](beads.md) provides a separate local work-graph endpoint. It does not replace Octo's issue lifecycle or dispatch; installing it alone does not connect Octo to Beads.

Add the switch to the existing `[tools]` section of your machine configuration (`~/.config/dotfiles/config.toml`, or the selected `DOTFILES_CONFIG`):

```toml
[tools]
octo-manager = true
```

Alternatively, add `"octo-manager"` to your existing `sets` array. Then inspect and install:

```sh
make plan
make install
```

The managed installer supports macOS and Linux on x64 and arm64, selecting the matching private Bun artifact (including musl on Linux). The recipe installs its declared Git, GitHub CLI and Go dependencies, checks out the exact Octo revision pinned in `bootstrap/tools.toml`, provisions the source-pinned Bun privately, and delegates release installation, service startup and Codex hook configuration to Octo's own installer. The private runtime does not replace another Bun on your PATH. Release downloads require HTTPS and a matching published SHA-256 checksum. A modified cached checkout, mismatched existing private runtime or conflicting installation lock produces an error; it is preserved for inspection.

`make` continues to apply configuration without installing software or starting services. Octo activation happens during explicit installation. Rerunning installation reuses its checkout/runtime and existing versioned release, while reapplying the native hook/service configuration without duplicate hook commands. The catalog remains pinned; only the explicit `pull-latest` target selects upstream `main`. These commands preserve existing user checkouts.

## Manage Octo directly

Run these targets from `~/.files`. They require Python 3.11+; installation also requires Git, GitHub CLI, Go, and download access. They operate on Octo without installing the rest of the selected tool plan.

| Target | Behavior |
| --- | --- |
| `make octo-manager-install` | Install the catalog-pinned release, configure native hooks, and start its service. |
| `make octo-manager-reinstall` | Reapply the currently installed revision and its hook/service configuration. |
| `make octo-manager-pull-latest` | Resolve upstream `main` to one exact commit, then install and start that revision. `octo-manager-pull` is an alias. |
| `make octo-manager-start` | Enable and start the installed service; leave an already running process in place. |
| `make octo-manager-restart` | Enable and restart the installed service, or start it if it is stopped. |

Reinstall reuses the existing versioned release and retained state; it does not force a rebuild or delete cached artifacts. Service controls use launchd on macOS and the user systemd manager on Linux, require an installed service definition, and propagate manager failures. The dashboard remains a separate client: attach with `octo-manager dashboard`.

## Hooks and runtime

Use a Codex host exposing its app-server control socket and authenticate GitHub through the existing `gh` CLI. Octo uses that socket to deliver into the session. Installation can prepare hooks before Codex is running, but it cannot establish delivery until that host is available.

| Native hook | Purpose |
| --- | --- |
| `SessionStart` | Register the owning session and recover applicable unread messages. |
| `UserPromptSubmit` | Record exact incoming message/digest receipts and recover unread messages. |
| `PostToolUse` | Enroll successfully attached GitHub PR artifacts for background monitoring. |

If Codex requests trust approval, review the three Octo definitions in its `/hooks` flow. Installing JSON is distinct from the host accepting and executing hooks; dotfiles does not bypass that trust decision. Unrelated hook commands, custom settings and curated MCP configuration are preserved. Create PRs through [the required Octo submission command](octo-pr-submission.md); the separate interception hook is installed only through `make codex-octo-hook` and still requires native host trust. Private and public tracking use existing GitHub permissions, without repository allowlists.

`make codex-permissions` installs scoped command allowances in `$CODEX_HOME/rules/octo-manager.rules` (default `~/.codex/rules/octo-manager.rules`). They cover inspection, local PR validation, delivery receipts, acknowledgments, and caller activity reporting through `octo-manager` and the home-directory launcher. The grouped allowances include issue, assessment, history, repair-list, and conflict inspection. `read ID` retrieves evidence and records delivery; it does not accept, resolve, or merge work. Both `merge ID` and `messages merge ID`, publication, issue approvals and lifecycle changes, assessment retries, rebase requests, and service controls receive no allowance from this policy. Setup replaces only its marked block and preserves other rules and unrelated Codex settings. It neither installs nor starts Octo, grants hook trust, nor broadens filesystem or network access for other commands. Restart Codex to load newly installed rules. Legacy `pr ID`, `action ID`, and bare `activity` calls remain outside the allowance because their prefixes overlap newer command groups; use grouped inspection commands when supported.

macOS uses launchd; Linux uses `octo-manager.service` under the selected configuration home’s `systemd/user` directory. If a user manager is unavailable, installation still provides the launcher and hooks, reports `started: false`, and prints a foreground command with the same installation environment. A detected manager’s configuration or startup failure is an error.

The launcher is `~/.local/bin/octo-manager`, state is `~/.local/state/octo-manager`, installed releases are under `~/.local/share/octo-manager/releases`, and the macOS service is `com.lanej.octo-manager`. Hook/config installation backups remain under Octo's state directory. Platform-specific source/dependencies live under `$XDG_CACHE_HOME/dotfiles/octo-manager` (default `~/.cache/dotfiles/octo-manager`). An existing different-owner PR remains assigned to that owner.

Persist the default worker model in `workerModel` under `~/.config/octo-manager/config.json`; `serve --model` overrides it. These settings survive reinstalling Octo. Provider-qualified selections such as `amazon-bedrock/us.anthropic.claude-sonnet-5-5` use native Bedrock authentication without copying credentials or requiring a Codex login. Supply the service's existing AWS environment separately; on Linux, keep custom environment setup in a user-owned systemd drop-in so regeneration of the managed unit preserves it.

```sh
octo-manager pr list --json
octo-manager agent inbox --agent-id AGENT_ID --applicable-only
```

Publishing with a known Codex thread enrolls the PR by default. Use `--no-track` to opt out. The attachment hook enrolls existing PRs attached to the session. For an existing PR that was published without enrollment or never attached, use `octo-manager pr track --url URL --thread-id THREAD_ID`. Receipt means the host received context; it does not accept or resolve actions or authorize repairs or merges.

## Disable future installation

Set `tools.octo-manager = false` or remove the optional set. This prevents future installation; it does not uninstall an existing release or stop its service. Stop a running macOS service with `launchctl bootout gui/$(id -u)/com.lanej.octo-manager`, or a Linux service with `systemctl --user disable --now octo-manager.service`. Remove only the three Octo commands from the configured Codex hooks file when retiring that integration; preserve unrelated commands and retained Octo state.

## Repository notification policy

When the source-code project profile selects Octo, setup seeds `octo-manager.toml` without overwriting an existing file. Its state-specific instructions refer to installed project guidance. `merging.auto_merge = "project_stage"` follows the effective stage in `.source-code.json`: research and alpha enable inherited auto-merge; beta, production, and unknown stages disable it. Literal `true` or `false` selects a repository-wide default. Per-PR `--on` and `--off` override inheritance; `pr auto-merge PR --inherit --agent-id AGENT` resumes it. Promotion updates inherited PRs and invalidates readiness when the effective switch changes.

The coordinator reloads local policy on its scheduler cadence without GitHub requests. Enrollment binds a verified checkout to the PR’s repository. Invalid or unavailable policy suspends inherited automatic merging and retains last-valid instructions; explicit switches and already-submitted operations retain their separate authority and reconciliation. Authored policy is preserved by source-code upgrades, and shadow setup excludes the seeded file locally.
