# Firstmate primary harness

The `firstmate` launcher can run its primary supervisor with Codex or Pi. Codex remains the default, and `firstmate/crew-harness` independently keeps crewmates on Codex. Selecting Pi changes the primary process; it does not convert the crew, checkout lifecycle, or terminal backend.

## Select a primary

Run `make firstmate-config` to install the launcher and managed default. For one launch:

```sh
FM_PRIMARY_HARNESS=pi firstmate start
FM_PRIMARY_HARNESS=codex firstmate start
```

Selection follows `FM_PRIMARY_HARNESS`, then the first nonempty line of `~/.config/firstmate/primary-harness`, then `codex`. Only `codex` and `pi` are supported. The installed file initially links to `firstmate/primary-harness` in this repository; edit that source to change the managed preference. Installation preserves an existing local file or link. `FIRSTMATE_HOME` selects the Firstmate checkout, defaulting to `~/src/firstmate`.

Arguments after `start`, or directly after `firstmate`, go to the selected agent unchanged. Codex also receives the existing `--approve-for-me` flag and 45-second watcher checkpoint. Pi receives neither that flag nor the Codex checkpoint environment variable.

The choice applies when creating a new captain. `firstmate start` attaches to an existing captain without replacing it or changing its model. Finish existing work before stopping the selected Firstmate session and starting a new primary. `attach`, `stop`, and `reload` use the configured backend; `tmux` and `zellij` commands must match that selection. Other sessions remain running when Firstmate stops.

## Pi prerequisites

Install Pi 1.4.0 or newer separately; it is not currently included in the tool catalog. Provider authentication remains Pi's own setup; the launcher does not change credentials. Use an updated [Firstmate checkout with Pi primary support](https://github.com/kunchenguid/firstmate#recommended-harnesses). The launcher requires these tracked files under its `.pi/extensions/` directory:

- `fm-primary-pi-watch.ts`
- `fm-primary-turnend-guard.ts`
- `fm-branch-supervision.ts`

The check establishes that the required entrypoints exist, not that every upstream/Pi version combination is compatible. Bootstrap reuses an existing Firstmate checkout; it does not update it automatically. Review and update that checkout deliberately, or point `FIRSTMATE_HOME` at a suitable checkout. Missing Pi, an unsupported version, or missing extension files prevent the primary from starting with a setup error; the launcher does not fall back to Codex. Zellij checks these prerequisites in the initial pane only when creating a captain, so attaching to an existing session does not require the newly selected primary to be installed.

Approve Pi's project trust prompt for the Firstmate checkout so its tracked extensions load through normal discovery. The launcher neither bypasses that decision nor loads duplicate extensions with `-e`. Firstmate's own session-start checks report missing loaded watcher/guard extensions. Before using a live crew, confirm that the watcher remains active after the primary finishes a turn and that required decisions return to the primary conversation. The [upstream supervision protocol](https://github.com/kunchenguid/firstmate/blob/main/docs/supervision-protocols/pi.md) owns those semantics.

Primary selection works with either configured [tmux or Zellij backend](firstmate.md). The launch command carries the chosen primary, executable path, and Firstmate checkout into the backend's initial pane. It preserves backend selection and the independent Codex crew configuration. Pi status rendering and restore integration remain separate capabilities.

## Check the launcher

```sh
make test-firstmate-primary
```

The detector installs the actual launcher into an isolated home and explicitly selects native tmux to exercise primary selection, argument transport, configuration preservation, and reattachment. The existing `FIRSTMATE_SOURCE=/path/to/firstmate make test-firstmate` workflow exercises a Pi captain with native Zellij and upstream task operations, including reattachment with a different primary selection. Agent executables are controlled fixtures; the focused tmux detector also uses fixture extension files. These checks make no model calls and do not establish live Pi extension loading, provider access, autonomous crew supervision, or macOS behavior from a Linux run. CI runs both workflows on Linux and macOS.
