# Dotfiles Repository

## Project Overview

This repository manages Josh Lane's personal configuration files ("dotfiles")
and development environment setup, portable across macOS and Linux. The
`Makefile` symlinks configuration from this repo (`~/.files`) into the home
directory; `bootstrap.sh` installs system packages and tools (Neovim, Rust,
fzf, and others) via OS-specific package managers or direct downloads.
Primary shell is Zsh (`zsh-autosuggestions`, syntax-highlighting, starship
prompt); primary editor is Neovim (Lua config in `nvim/`).

## Getting Started

```bash
git clone https://github.com/lanej/dotfiles.git ~/.files
cd ~/.files
make          # Symlinks configuration files to ~
./bootstrap.sh # Installs packages and dependencies
```

Always edit files within `~/.files`, not the symlinked targets under `~`.
Most changes (e.g. `.zshrc`, `init.lua`) take effect immediately or on
shell/editor reload because they're symlinked. Adding a *new* file to be
symlinked requires a corresponding rule in the `Makefile` plus a re-run of
`make`. New tools are added to `bootstrap.sh` (use `install_package_version`
to pin a specific version) and, if they need config symlinked, to the
`Makefile`.

## Development Conventions

- **Idempotency**: `bootstrap.sh` and `Makefile` should be idempotent — running them multiple times is safe and converges on correct state.
- **Cross-platform**: scripts handle both macOS (`darwin`) and Linux (checking for `apt`, `dnf`, `pacman`, `brew`).
- **Symlinks**: prefer `ln -fs` (force symbolic) to overwrite existing files/links.
- **Dependencies**: `bootstrap.sh` prefers installing from binary releases (GitHub Releases) or Cargo when system package managers are outdated.

## Testing

Keep one regression detector per user-visible feature. Prefer one representative
workflow through the real entrypoint and observable result. A helper, branch,
input variant, or failure mode is not a separate feature.

A detector is sufficient when it goes red if you delete the behavior it covers.
Establish falsifiability once when wiring a new harness: delete representative
behavior, confirm red, restore it, and confirm green. Do not repeat this mutation
check for each test or task in an established harness. See `methodology`'s V1
acceptance definition and harness verification procedure.

When repairing a regression, improve that feature's existing detector. Multiple
assertions may describe the same workflow; do not hide a case matrix in loops,
parameterization, or one oversized test. Add broader coverage only when the
owner explicitly requests it.

Run the affected detector once after the change; rerun it to resolve a failure
or after changing the implementation. Use syntax checks and diff review for
simple configuration/documentation edits. Do not add tests that mirror code,
check exact source strings, or merely count configured hooks.

Routine maintenance needs no evaluation bundles, source snapshots, provenance
receipts, or separate review narratives. Put the outcome and any manual findings
or verification gaps in the PR; let automated checks report their own results.
Keep CI scoped to the features it exercises.

## Pull requests

Follow [the PR guidance](docs/pull-requests.md): explain the outcome and why,
include a screenshot when it adds useful evidence, and add only context the
diff and checks do not already supply. Do not duplicate test inventories or
automated results.

## Maintaining agent instructions

Before changing skills, commands, agents, or their supporting resources, read
[the skill-maintenance policy](docs/skill-maintenance.md). It routes authoring
through the installed Anthropic skill-creator workflow and defines
this repository's focused regression checks and entrypoint size budget.

## Claude Commands & Agents Versioning Pattern

New files under `claude/{commands,agents,skills}/` are gitignored by default; force-add deliberately with `git add -f` to version one. See the `claude-config-versioning` skill for the full workflow, symlink mechanics, and gitignore/clean-filter details.

## Tech Radar

Tool/tech decisions are tracked in [`docs/radar.md`](docs/radar.md) (four-ring model: Adopt/Trial/Assess/Hold). Use the `tech-radar` agent for updates.
