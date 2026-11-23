# Extraction provenance

Prepared from [lanej/dotfiles at d33526d125a69ea5be9faf12eb8507014d20e170](https://github.com/lanej/dotfiles/tree/d33526d125a69ea5be9faf12eb8507014d20e170). This package is the standalone snapshot boundary. The selected destination is `lanej/studio`, with source checkout `~/src/studio`.

`vendor/task-runtime` is derived from `tools/task-runtime` at that revision, with Bun commands, strict-lint adaptations, and configured worktree-executable support. Paseo retains its original client. Update the client, schema and generated declarations together, then run `bun run check:beads-api` in the vendor package and the driver acceptance checks. Its Beads schema provenance is in `vendor/task-runtime/api/README.md`.

`resources/socrates` and the generated theme and palette are snapshots from the same revision. Their authoring sources remain in dotfiles. Refresh them deliberately and rerun native Pi resource and terminal acceptance. Keep `LICENSE.session-snap`, `LICENSE.smart-plan`, and `generated/zellij/LICENSE.md` with redistributed source.

`acceptance/install-worktree-manager` retains the checksum-verifying dotfiles installer for the CI fixture version. `acceptance/zellij_pty.py` retains the generic PTY helper from dotfiles; it does not run the workstation navigation detectors. External native tools remain independently installed.

Cutover remains gated on standalone macOS and Linux acceptance. Only then remove the dotfiles driver sources and checks and register `~/src/studio` as `studio` in `config/project-updates.toml`.

There is no pre-extraction driver database to migrate. Existing Beads data and unrelated Pi sessions remain outside this extraction. The driver retains its normal persistent attempt and recovery records for future use.

Optional integrations are disabled by default and are admitted only when configured and present. Core installation and standalone acceptance do not require Beads, Zellij, worktree manager, or Octo; use `--with-integrations` for native delegation acceptance.

`vendor/pi-components` retains the current shared selector implementation from dotfiles commit 72494ce0 so the capability refactor and code intelligence remain available after extraction. Source export and installation select Git-visible files; snapshots without Git use the explicit `source-files.json` generated at export. Ignored local files are outside that boundary.
