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

## Repository Layout

- `bootstrap.sh` — main installation script; checks OS, installs packages, manages versions.
- `Makefile` — defines symlink rules; run `make` to apply.
- `bin/` — utility scripts, added to `$PATH`; selectively versioned.
- `claude/` — custom commands and agents for AI assistants (`commands/`, `agents/`).
- `gemini/skills/` — skills replicated from the Claude configuration for Gemini.
- `nvim/` — Neovim configuration (Lua).
- `zsh/` — Zsh configuration and plugins.
- `git/` — Git configuration (`.gitconfig`, `.gitignore`, etc.).
- `rc/` — miscellaneous run commands (tmux, X resources, etc.).

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

This repository uses a selective versioning pattern for Claude commands and agents that allows for experimentation without polluting version control.

### Directory Structure

```
~/.files/
├── claude/
│   ├── commands/     # Source directory (selectively versioned)
│   └── agents/       # Source directory (selectively versioned)
└── .claude/          # Gitignored (user-specific settings)
    └── settings.json

~/.claude/            # User's global Claude directory (real, not a symlink)
├── commands/         # Individual entries symlinked from ~/.files/claude/commands/
├── agents/           # Individual entries symlinked from ~/.files/claude/agents/
├── skills/           # Individual entries symlinked from ~/.files/claude/skills/
└── CLAUDE.md         # Symlinked to ~/.files/claude/CLAUDE.md
```

### Setup via Makefile

Run `make claude` (Makefile:168-178). Symlinks `settings.json`, commands, agents, skills, workflows, and CLAUDE.md into `~/.claude/`, and wires MCP servers into `~/.claude.json` via `jq`.

EP-specific skills live in `~/src/ep-dotfiles/`. Run `make link-skills` from there after cloning to symlink them into `~/.files/claude/skills/`.

### Workflow

1. **Experimentation**: Create/edit the file directly under `~/.files/claude/commands/` (or `claude/agents/`)
   - Run `make claude` to symlink new entries out into `~/.claude/commands/` (already-symlinked files update live since they point back to the same source; only brand-new files need the re-run)
   - Not automatically tracked by git (new files are gitignored by default)

2. **Selective Versioning**: When ready to version a command:
   ```bash
   git add -f claude/commands/path/to/command.md
   git commit -m "feat(claude): add new command"
   ```

3. **Benefits**:
   - Experiment freely without polluting git history
   - Selectively version only stable/useful commands
   - Portable across machines via dotfiles
   - User-specific settings (`.claude/settings.json`) remain separate

### Examples

The pattern is already employed for several commands:
- `claude/commands/gh/fix-issue.md` - GitHub issue fixing workflow
- `claude/commands/eureka.md` - Capture technical breakthroughs
- `claude/agents/commit-message-generator.md` - Git commit message generation

### Gitignore Configuration

`~/.claude/{commands,agents,skills,workflows}` are real directories; `make claude` (the `claude` Makefile target) symlinks each top-level entry in this repo's `claude/{commands,agents,skills,workflows}/` into them individually, so anything Claude Code, a plugin, or an installer writes as a *new* entry there stays local and never lands in the working tree. `.gitignore` still ignores new files under this repo's own `claude/{commands,agents,skills}/` by default; version one deliberately with `git add -f` (already-tracked files are unaffected). It also ignores repo-local `.claude/` state other than `settings.json` and `mcp-servers.json`, eval `results/`, skill-creator `*-workspace/` dirs, and packaged `*.skill` files. Anthropic-published skills are listed by name and never tracked (`claude/skills/ANTHROPIC-SKILLS.md`).

`.claude/settings.json` is tracked but rewritten in place by Claude Code; a `claude-settings` clean filter (`.gitattributes`, configured by `make claude`) drops bookkeeping keys such as `feedbackSurveyState` so they never show up as changes.

This pattern mirrors the approach used elsewhere in this repository (e.g., experimental scripts in `bin/` that are selectively versioned).

## Gemini Skills

A set of skill definitions has been replicated from the Claude configuration to `gemini/skills/` to provide specialized assistance in Gemini CLI. These Markdown files contain specific workflows and best practices for various tools.

- **Location:** `gemini/skills/`
- **Available Skills:**
    - `az`: Azure CLI
    - `bigquery`: Google BigQuery
    - `git`: Git & GitHub CLI
    - `go`: Go development
    - `gspace`: Google Workspace
    - `jira`: Jira CLI
    - `jq`: JSON processing
    - `just`: Command runner
    - `lancer`: LanceDB/Search
    - `phab`: Phabricator
    - `pkm`: Personal Knowledge Management
    - `presenterm`: Presentation tool
    - `python`: Python development
    - `rust`: Rust development
    - `xlsx`: Excel manipulation
    - `xsv`: CSV processing

Refer to the `SKILL.md` file within each directory (e.g., `gemini/skills/rust/SKILL.md`) for detailed instructions.

## Tech Radar

Tool and technology decisions are tracked in [`docs/radar.md`](docs/radar.md) using a four-ring model:

| Ring | Meaning |
|---|---|
| **Adopt** | In active use; recommended |
| **Trial** | Being evaluated in real workflows |
| **Assess** | Worth watching; not yet trialed |
| **Hold** | Deliberately not adopted; rationale documented |

### When to update the radar

- **New tool added to the stack** → move it to **Adopt** (or **Trial** if still evaluating)
- **Tool being evaluated** → add to **Trial** or **Assess**
- **Tool rejected** → add to **Hold** with a concise rationale
- **Trial concludes** → promote to **Adopt** or demote to **Hold**
- **Adopted tool retired** → move to **Hold** (or remove if fully purged)

### How to update

Edit `docs/radar.md` directly. Each entry lives under its ring heading as a `###` subsection. Cross-link related entries when one tool's fate depends on another (e.g., "Revisit if X resolves issue Y").

Use the `tech-radar` agent to make updates conversationally.
</content>
</invoke>
