# Gemini Context: Dotfiles Repository

This repository manages the user's configuration files ("dotfiles") and development environment setup. It is designed to be portable across macOS and Linux.

## Project Overview

*   **Type:** Configuration Management (Dotfiles)
*   **Core Mechanism:**
    *   **Symlinks:** The `Makefile` creates symlinks from this repository (`~/.files`) to the user's home directory (`~`).
    *   **Package Management:** `bootstrap.sh` handles installation of system packages and tools (e.g., Neovim, Rust, FZF) using OS-specific package managers (brew, apt, dnf) or direct downloads.
*   **Primary Shell:** Zsh (with `zsh-autosuggestions`, `syntax-highlighting`, `starship` prompt).
*   **Primary Editor:** Neovim (Lua-based config in `nvim/`).

## Key Workflows

### 1. Installation & Setup

To set up the environment on a new machine:

```bash
git clone https://github.com/lanej/dotfiles.git ~/.files
cd ~/.files
make          # Symlinks configuration files to ~
./bootstrap.sh # Installs packages and dependencies
```

### 2. Modifying Configuration

*   **Edit Source:** Always edit files within the `~/.files` directory.
*   **Apply Changes:**
    *   Most changes (e.g., `.zshrc`, `init.lua`) take effect immediately or upon reloading the shell/editor because they are symlinked.
    *   If you add *new* files to be symlinked, add a corresponding rule to the `Makefile` and run `make`.

### 3. Adding/Updating Tools

*   **Package Installation:** Edit `bootstrap.sh` to add new tools. Use `install_package_version` to enforce specific versions.
*   **Symlinking Configs:** Add new targets to the `Makefile` to symlink configuration files for new tools (e.g., `~/.config/newtool`).

### 4. Selective Versioning

This repository uses a "selective versioning" pattern for the `bin/` and `claude/` directories.

*   **Gitignore:** `bin/*` and `.claude/*` are ignored by default.
*   **Tracking:** To track a script or command, use `git add -f <file>`.
*   **Purpose:** Allows for local experimentation with scripts/commands without polluting the repository, while still allowing useful ones to be committed.

## Directory Structure

*   **`bootstrap.sh`**: Main installation script. Checks OS, installs packages, manages versions.
*   **`Makefile`**: Defines symlink rules. Run `make` to apply.
*   **`bin/`**: Utility scripts. Added to `$PATH`. Selectively versioned.
*   **`claude/`**: Custom commands and agents for AI assistants.
    *   `commands/`: Markdown files defining AI commands.
    *   `agents/`: Definitions for AI agents.
*   **`gemini/`**: Context and skills for Gemini AI.
    *   `skills/`: Replicated skills from Claude configuration.
*   **`nvim/`**: Neovim configuration (Lua).
*   **`zsh/`**: Zsh configuration and plugins.
*   **`git/`**: Git configuration (`.gitconfig`, `.gitignore`, etc.).
*   **`rc/`**: Miscellaneous run commands (tmux, X resources, etc.).

## Development Conventions

*   **Idempotency:** `bootstrap.sh` and `Makefile` should be idempotent. Running them multiple times should be safe and ensuring the state is correct.
*   **Cross-Platform:** Scripts should handle both macOS (`darwin`) and Linux (checking for `apt`, `dnf`, `pacman`, `brew`).
*   **Symlinks:** Prefer `ln -fs` (force symbolic) to overwrite existing files/links.
*   **Dependencies:** `bootstrap.sh` prefers installing from binary releases (GitHub Releases) or Cargo when system package managers are outdated.

## AI Integration

The `claude/` directory contains context and commands for AI assistants. While named "claude", the patterns (commands/agents defined in Markdown) are relevant for understanding the user's AI workflow.
*   **Global Config:** `~/.claude/` (symlinked from `.files/claude/` and `.files/.claude/`).
*   **Local Overrides:** `.claude/settings.json` handles user-specific settings.

## Gemini Skills

To provide specialized assistance, a set of skill definitions has been replicated from the Claude configuration to `gemini/skills/`. These Markdown files contain specific workflows and best practices for various tools.

*   **Location:** `gemini/skills/`
*   **Available Skills:**
    *   `az`: Azure CLI
    *   `bigquery`: Google BigQuery
    *   `git`: Git & GitHub CLI
    *   `go`: Go development
    *   `gspace`: Google Workspace
    *   `jira`: Jira CLI
    *   `jq`: JSON processing
    *   `just`: Command runner
    *   `lancer`: LanceDB/Search
    *   `phab`: Phabricator
    *   `pkm`: Personal Knowledge Management
    *   `presenterm`: Presentation tool
    *   `python`: Python development
    *   `rust`: Rust development
    *   `xlsx`: Excel manipulation
    *   `xsv`: CSV processing

Refer to the `SKILL.md` file within each directory (e.g., `gemini/skills/rust/SKILL.md`) for detailed instructions.