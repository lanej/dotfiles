# Dotfiles Repository

## Project Overview

This repository manages Josh Lane's personal configuration files ("dotfiles")
and development environment setup, portable across macOS and Linux. The
`Makefile` symlinks configuration from this repo (`~/.files`) into the home
directory. `make bootstrap` applies the built-in OS baseline and installs uv
and Python; `make install` installs selected tools (Neovim, Rust, fzf, and
others) via the installers in `bootstrap.sh`, then applies configuration.
Primary shell is Zsh (`zsh-autosuggestions`, syntax-highlighting, starship
prompt); primary editor is Neovim (Lua config in `nvim/`).

## Getting Started

Follow [the setup requirements](docs/setup-requirements.md) when changing configuration, bootstrap, or software installation.

```bash
git clone https://github.com/lanej/dotfiles.git ~/.files
cd ~/.files
make           # Initialize the machine TOML and native OS baseline
make bootstrap # Native macos or linux baseline plus uv and Python
make plan      # Inspect the selected tool bundles
make install   # Install selected tools and apply their configuration
```

Always edit files within `~/.files`, not the symlinked targets under `~`.
Most changes (e.g. `.zshrc`, `init.lua`) take effect immediately or on
shell/editor reload because they're symlinked. Adding a *new* file to be
symlinked requires a corresponding rule in the `Makefile` plus a re-run of
`make`. Declare tool recipes and version pins in `bootstrap/tools.toml`, then
group their `tools.<name>` switches under `config/sets/`. The resolver derives
selected Make targets and bootstrap phases from that catalog. Default `make`
applies the native OS baseline; `make configure` adds the configured bundles.
Reuse the installers in `bootstrap.sh`; add a new adapter there only when needed.
Configuration symlink rules remain in the `Makefile` and its helper scripts.
Default `make` initializes a missing machine TOML with the detected native set
and links the built-in baseline without Python. Preserve existing machine files
and symlinks. `make configure` applies the full resolved configuration without installing
packages. Keep `config/targets.mk` generated from the native sets and tool catalog
with `python3 scripts/dotfiles-config.py --format make-targets > config/targets.mk`.
Do not add tools to an unconditional install or setup list.

## Development Conventions

- **Idempotency**: `bootstrap.sh` and `Makefile` should be idempotent — running them multiple times is safe and converges on correct state.
- **Cross-platform**: scripts handle both macOS (`darwin`) and Linux (checking for `apt`, `dnf`, `pacman`, `brew`).
- **Symlinks**: prefer `ln -fs` (force symbolic) to overwrite existing files/links.
- **Dependencies**: `bootstrap.sh` prefers installing from binary releases (GitHub Releases) or Cargo when system package managers are outdated.
- **Makefiles**: Keep Makefiles declarative: targets, dependencies, variables, and calls to scripts or tools. Put shell logic in scripts, including loops, conditionals, pipelines, redirections, and command substitutions. Scripts called by Make must pass `make shellcheck`; include new shell entrypoints in that check, which also runs through `make lint` and CI.

## Testing

Keep one regression detector per user-visible feature. Prefer one representative
workflow through the real entrypoint and observable result. A helper, branch,
input variant, or failure mode is not a separate feature.

A detector is sufficient when it goes red if you delete the behavior it covers.
Establish falsifiability once when wiring a new harness: delete representative
behavior, confirm red, restore it, and confirm green. Do not repeat this mutation
check for each test or task in an established harness. See the [verification guide](docs/verification.md) for the acceptance
definition and harness verification procedure.

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

## Bug reports

Before filing a bug report or making a substantive revision, invoke the
`bug-reporter` as a separate subagent and follow [the shared standard](docs/bug-reports.md).
Supply the destination, required fields, observed failure, and existing evidence.
Its only job is to report: do not ask it to investigate, reproduce, fix, or submit.
Encourage load bearing screenshots and diagrams; omit redundant prose and visuals.
Resolve its blockers, use its draft, then submit and verify the saved result through
the existing workflow. The reporter must not invoke further writers or reviewers.
If named selection is unavailable, use a generic drafting-only agent with the
installed `~/.codex/agents/bug-reporter.toml` instructions or shared
`ai/agents/bug-reporter.md` definition; report the gap if neither is available.
Feature requests keep their existing workflows.

## Claude Commands & Agents Versioning Pattern

New files under `claude/commands/` and `ai/{agents,skills}/` are gitignored by default; force-add deliberately with `git add -f` to version one. See the `claude-config-versioning` skill for the full workflow, symlink mechanics, and gitignore/clean-filter details.

## Tech Radar

Tool/tech decisions are tracked in [`docs/radar.md`](docs/radar.md) (four-ring model: Adopt/Trial/Assess/Hold). Edit the radar directly using the entry conventions documented there.
