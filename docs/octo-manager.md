# Opt-in Octo Manager

Octo publishes GitHub PRs through a recorded writer and publication checks, monitors enrolled PRs, and returns actionable checks and review feedback to the owning Codex session. Install it explicitly before using [the required PR publication command](octo-pr-submission.md). Neither the default configuration nor the `ai` and `workstation` sets enable Octo's local service or native hooks; configuration does not install software automatically.

## Enable

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

If Codex requests trust approval, review the three Octo definitions in its `/hooks` flow. Installing JSON is distinct from the host accepting and executing hooks; dotfiles does not bypass that trust decision. Unrelated hook commands, custom settings and curated MCP configuration are preserved. No PR-submission interception hook is installed; ordinary `gh pr create` and the repository's existing PR writer remain available. Private and public tracking use existing GitHub permissions, without repository allowlists.

macOS uses launchd; Linux uses `octo-manager.service` under the selected configuration home’s `systemd/user` directory. If a user manager is unavailable, installation still provides the launcher and hooks, reports `started: false`, and prints a foreground command with the same installation environment. A detected manager’s configuration or startup failure is an error.

The launcher is `~/.local/bin/octo-manager`, state is `~/.local/state/octo-manager`, installed releases are under `~/.local/share/octo-manager/releases`, and the macOS service is `com.lanej.octo-manager`. Hook/config installation backups remain under Octo's state directory. Platform-specific source/dependencies live under `$XDG_CACHE_HOME/dotfiles/octo-manager` (default `~/.cache/dotfiles/octo-manager`). An existing different-owner PR remains assigned to that owner.

```sh
octo-manager tracked --json
octo-manager inbox --agent-id AGENT_ID --applicable-only
```

PR attachment is the automatic enrollment path. CLI-only sessions or unattached PRs can enroll explicitly with `octo-manager track --url URL --thread-id THREAD_ID`. Receipt means the host received context; it does not accept or resolve actions or authorize repairs or merges.

## Disable future installation

Set `tools.octo-manager = false` or remove the optional set. This prevents future installation; it does not uninstall an existing release or stop its service. Stop a running macOS service with `launchctl bootout gui/$(id -u)/com.lanej.octo-manager`, or a Linux service with `systemctl --user disable --now octo-manager.service`. Remove only the three Octo commands from the configured Codex hooks file when retiring that integration; preserve unrelated commands and retained Octo state.
