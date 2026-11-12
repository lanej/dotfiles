# Opt-in Octo Manager

Octo monitors enrolled GitHub PRs, collapses pending notifications, and returns actionable checks and review feedback to the owning Codex session. Its local service and native hooks are optional; neither the default configuration nor the `ai` and `workstation` sets enable them.

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

The managed service currently supports macOS only. Linux selection fails during plan validation, before selected installers run. The recipe installs its declared Git, GitHub CLI and Go dependencies, checks out the exact Octo revision pinned in `bootstrap/tools.toml`, provisions the source-pinned Bun privately, and delegates release installation, service startup and Codex hook configuration to Octo's own installer. The private runtime does not replace another Bun on your PATH. Release downloads require HTTPS and a matching published SHA-256 checksum. A modified cached checkout, mismatched existing private runtime or conflicting installation lock produces an error; it is preserved for inspection.

`make` continues to apply configuration without installing software or starting services. Octo activation happens during the explicit `make install` operation. Rerunning installation reuses the pinned checkout/runtime and existing versioned release, while reapplying the native hook/service configuration without duplicate hook commands. Updating the catalog revision selects a new release; the installer never pulls an arbitrary branch tip or changes an existing user checkout.

## Hooks and runtime

Open a current Codex desktop session and authenticate GitHub through the existing `gh` CLI. Octo uses the desktop app-server socket to deliver into that session. Installation can prepare hooks before Codex is running, but it cannot establish delivery until that host is available.

| Native hook | Purpose |
| --- | --- |
| `SessionStart` | Register the owning session and recover applicable unread messages. |
| `UserPromptSubmit` | Record exact incoming message/digest receipts and recover unread messages. |
| `PostToolUse` | Enroll successfully attached GitHub PR artifacts for background monitoring. |

If Codex requests trust approval, review the three Octo definitions in its `/hooks` flow. Installing JSON is distinct from the host accepting and executing hooks; dotfiles does not bypass that trust decision. Unrelated hook commands, custom settings and curated MCP configuration are preserved. No PR-submission interception hook is installed; ordinary `gh pr create` and the repository's existing PR writer remain available. Private and public tracking use existing GitHub permissions, without repository allowlists.

The launcher is `~/.local/bin/octo-manager`, state is `~/.local/state/octo-manager`, installed releases are under `~/.local/share/octo-manager/releases`, and the macOS service is `com.lanej.octo-manager`. Hook/config installation backups remain under Octo's state directory. Versioned source/dependencies live under `$XDG_CACHE_HOME/dotfiles/octo-manager` (default `~/.cache/dotfiles/octo-manager`). An existing different-owner PR remains assigned to that owner.

```sh
octo-manager tracked --json
octo-manager inbox --agent-id AGENT_ID --applicable-only
```

PR attachment is the automatic enrollment path. CLI-only sessions or unattached PRs can enroll explicitly with `octo-manager track --url URL --thread-id THREAD_ID`. Receipt means the host received context; it does not accept or resolve actions or authorize repairs or merges.

## Disable future installation

Set `tools.octo-manager = false` or remove the optional set. This prevents future installation; it does not uninstall an existing release or stop its service. To stop an already running service, use `launchctl bootout gui/$(id -u)/com.lanej.octo-manager`. Remove only the three Octo commands from the configured Codex hooks file when retiring that integration; preserve unrelated commands and retained Octo state.
