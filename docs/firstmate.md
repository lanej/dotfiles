# Firstmate sessions

The `firstmate` launcher starts a captain in a dedicated session. Codex is the default; [primary selection](firstmate-primary.md) can opt into Pi independently of the Codex crew and the terminal backend. Choose tmux or Zellij explicitly; installing or running Zellij does not change the selected backend.

## Install and choose a backend

`make install` installs Firstmate and its tools when the `ai` or `workstation` set is selected. To update the launcher and configuration from an existing dotfiles checkout:

```sh
make firstmate-config
```

Backend selection follows `FM_BACKEND`, then the first nonempty line of the Firstmate home's `config/backend`, then `tmux`. Only `tmux` and `zellij` are supported by this launcher. Other upstream Firstmate backends retain their own launch instructions.

Try Zellij for the current shell:

```sh
export FM_BACKEND=zellij
firstmate start
```

For the managed default, change `firstmate/backend` in this checkout to `zellij`. The installer links that file when the Firstmate home has no backend configuration; it preserves an existing selection. If the home already owns a separate `config/backend`, update that file instead. Set `FM_BACKEND=tmux` to override either configuration for a launch.

Zellij requires version 0.45.1 or newer and `jq`; `make install` installs them with the `terminal` and `shell` sets. The installed Firstmate checkout must include its experimental Zellij adapter. `make firstmate-config` also installs the shared [Zellij configuration](zellij.md), but does not install binaries or start a session.

| Setting | Purpose | Default |
| --- | --- | --- |
| `FIRSTMATE_HOME` | Firstmate checkout for the launcher, bootstrap, and `make firstmate-config` | `~/src/firstmate` |
| `FM_BACKEND` | Explicit launcher and crew backend | Home's configuration, then `tmux` |
| `FM_ZELLIJ_SESSION` | Shared Zellij session for captain and crew | `firstmate` |
| `FIRSTMATE_TMUX_SOCKET` | Dedicated tmux server socket | `firstmate` |

Use an absolute `FIRSTMATE_HOME` path. Give independent homes distinct `FM_ZELLIJ_SESSION` names; the launcher attaches to an existing named session rather than creating another captain in it. Session names start with a letter, digit, or underscore and contain only letters, digits, underscores, dots, and hyphens. This keeps upstream's `session:pane` identities unambiguous.

## Daily commands

```sh
firstmate start                  # Also the default when no command is given
firstmate start --model <model>  # Selected agent's arguments apply to a new captain
firstmate attach
firstmate reload
firstmate stop
```

Keep the same backend and session settings when running these commands. `start` creates the captain only when the session is new; otherwise it attaches. `attach` connects to the selected session without creating one. Detach with `Ctrl-f d` and return with `firstmate attach`; the captain and crew continue running.

`stop` terminates the selected Firstmate session and its panes. It leaves other sessions running, including other sessions on the dedicated tmux server. It does not perform Firstmate task teardown or return Treehouse leases; use Firstmate's normal task cleanup before intentionally stopping active work.

For tmux, `reload` sources the shared Firstmate tmux configuration. For Zellij, it validates `~/.config/zellij/config.kdl` and reports the native reload behavior: Zellij watches that file and applies supported changes automatically. Layout and other creation-only changes apply when creating panes or sessions. The command does not restart the captain or claim that every setting changes live. See [Zellij's configuration guide](https://zellij.dev/documentation/configuration.html).

Backend commands are available through `firstmate tmux ...` and `firstmate zellij ...`; the subcommand must match the selected backend. For example:

```sh
FM_BACKEND=zellij firstmate zellij action list-tabs --json
FM_BACKEND=tmux firstmate tmux list-windows
```

## Zellij limits

This launcher uses [Firstmate's existing Zellij adapter](https://github.com/kunchenguid/firstmate/blob/30d6d15ec07e1efaeb3c795f0a24e817251d0718/docs/zellij-backend.md). Tasks retain its home-scoped tab titles and recorded session/tab/pane identities; the launcher does not replace those checks with name guessing.

The backend remains experimental. Creating a task can briefly take focus before Firstmate restores the previous tab. Supervision uses screen-change polling and harness lifecycle signals; the adapter has no verified agent-process liveness signal for automatically reviving a dead secondmate. CLI success alone does not establish that a target still exists. These limits are separate from the remaining [agent-status, Rex, and exact Claude recovery gaps](zellij.md#differences-that-remain).

## Check a change

```sh
FIRSTMATE_SOURCE=/path/to/firstmate make test-firstmate
```

The check needs Zellij 0.45.1+, tmux, jq, Treehouse 3.1.6+, an upstream Firstmate checkout, and the normal TPM installation (or `TPM_SOURCE=/path/to/tpm`). It installs into a temporary home and drives a Pi captain and upstream task spawn/send/peek/teardown commands against real local sessions and a disposable Git project, then checks the Codex default through an explicit tmux selection. Agent commands use controlled interactive shells, so the check makes no model calls and does not establish live Pi extension loading or autonomous agent supervision. Linux and macOS CI use the linked upstream revision. Cleanup addresses only the check's own named sessions.
