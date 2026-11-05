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
make base      # Initialize the machine TOML and native OS baseline
# Add this machine's tool and work-context sets to its TOML.
make bootstrap # Native macos or linux baseline plus uv and Python
make plan      # Inspect the selected tool bundles
make install   # Install selected tools and apply their configuration
```

Always edit files within `~/.files`, not the symlinked targets under `~`. Most changes (e.g. `.zshrc`, `init.lua`) take effect immediately or on shell/editor reload because they're symlinked. Adding a *new* file to be symlinked requires a corresponding rule in the `Makefile` plus a re-run of its target, or `make` when that target's recipe is selected. Declare tool recipes and version pins in `bootstrap/tools.toml`, then group their `tools.<name>` switches under `config/sets/`. The resolver derives selected Make targets and bootstrap phases from that catalog. Default `make` applies the full resolved configuration, including selected bundles and individual overrides, without installing packages; `make configure`, `make setup`, and `make all` are aliases. It requires Python 3.11+, installed by `make bootstrap`. Reuse the installers in `bootstrap.sh`; add a new adapter there only when needed. Configuration symlink rules remain in the `Makefile` and its helper scripts. `make base` initializes a missing machine TOML with the detected native set and links only the built-in baseline without Python. Preserve existing machine files and symlinks. Keep `config/targets.mk` generated from the native sets and tool catalog with `python3 scripts/dotfiles-config.py --format make-targets > config/targets.mk`. Do not add tools to an unconditional install or setup list.

## Development Conventions

- **Idempotency**: `bootstrap.sh` and `Makefile` should be idempotent — running them multiple times is safe and converges on correct state.
- **Cross-platform**: scripts handle both macOS (`darwin`) and Linux (checking for `apt`, `dnf`, `pacman`, `brew`).
- **Symlinks**: prefer `ln -fs` (force symbolic) to overwrite existing files/links.
- **Dependencies**: `bootstrap.sh` prefers installing from binary releases (GitHub Releases) or Cargo when system package managers are outdated.
- **Makefiles**: Keep Makefiles declarative: targets, dependencies, variables, and calls to scripts or tools. Put shell logic in scripts, including loops, conditionals, pipelines, redirections, and command substitutions. Scripts called by Make must pass `make shellcheck`; include new shell entrypoints in that check, which also runs through `make lint` and CI.

## Testing

Choose the smallest check that can expose a defect in the changed behavior. Scale verification to consequences and uncertainty: a small alias or wrapper needs a focused check, while installation, destructive cleanup, concurrency, and terminal interactions may need stronger evidence. Routine documentation and simple configuration edits need diff review and applicable syntax or structural checks.

Prefer focused protection through the caller's real entrypoint and an observable result. Improve existing coverage before adding another harness. Keep separate features independently runnable; do not force unrelated checks into one oversized journey to meet a test-count rule. Add cases for meaningful risks, not every helper, branch, or input variation. Do not mirror implementation details, assert exact source strings, or merely count configured hooks.

Control external commands or services when testing decisions and argument forwarding. Use real integrations when the claim depends on actual platform or external behavior; a simulated boundary cannot establish compatibility. Install and start only the runtime dependencies exercised by the selected check. A wrapper test should not require an editor, terminal stack, native build, credentials, or network unless those are part of the behavior being checked.

Run the affected check once after the change. Rerun it after relevant edits or to resolve a failure; broaden only when changed shared behavior or an unresolved interaction justifies it. Run both operating systems when platform differences matter, rather than automatically duplicating every check. Treat test setup time, flakiness, and failure isolation as maintenance costs.

A detector must fail when the behavior it protects is broken. Establish sensitivity once when introducing a new harness, then reuse that evidence; do not repeat mutation checks for routine changes. See the [verification guide](docs/verification.md) for the procedure.

Keep CI selection scoped to affected features and their actual dependencies. Trace changed paths to the entrypoints, configuration, shared code, and source content each check consumes; workflow names and directory proximity are not evidence of a dependency. Shared Makefile or lint-wiring edits must not automatically start every integration suite. Run the affected detector explicitly when changing a feature's Make recipe. When an overloaded shared shell file repeatedly causes unrelated checks to run, consider extracting a cohesive feature entrypoint with narrow loading and workflow paths. Preserve coverage for real shared behavior rather than simply removing its path from filters.

Relevant checks and required repository checks govern merging; unrelated pending suites are not automatic merge gates. Investigate failures before classifying them as unrelated, and state unresolved limits.

Routine maintenance needs no evaluation bundles, source snapshots, provenance receipts, or separate review narratives. Put material manual findings and verification gaps in the PR; let automated checks report their own results.

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
