---
description: "Update dotfile configurations and sync across systems: edit configs, run make targets, commit changes, and verify symbolic links"
argument-hint: [tool name or 'all']
allowed-tools:
  - Read
  - Edit
  - Bash(make:*)
  - Bash(git:*)
  - Bash(ls:*)
  - Bash(readlink:*)
tags:
  - dotfiles
  - config
  - sync
  - automation
---

# Dotfiles Sync - Manage Dotfile Configuration

Manage and synchronize dotfile configurations across systems following the repository's architecture.

## Overview

This dotfiles repository uses:
- **Makefile**: Creates symbolic links from dotfiles to home directory
- **bootstrap.sh**: Implements minimal bootstrap and explicit selected-tool installation
- **bootstrap/tools.toml**: Declares tool recipes, pins, dependencies, and configuration targets
- **config/sets/**: Composes reusable platform, tool, and context bundles
- **Machine TOML**: Selects additional sets and individual property overrides
- **Selective versioning**: Only commit stable/useful configurations

Read [the configuration guide](../../../README.md#configuration-sets) for the
current selection rules. Default `make` initializes a missing machine TOML and
links the native OS baseline without Python or software installation.
`make bootstrap` prepares uv and Python for TOML-driven commands;
`make install` explicitly installs selected tools. `make configure` reapplies
selected configuration. Preserve existing machine files, explicit tool disables,
and individual overrides.

## Usage

```bash
/dotfiles/sync [tool-name]  # Update specific tool config
/dotfiles/sync all          # Apply the machine's selected configuration
/dotfiles/sync              # Interactive mode
```

## Workflow

### 1. Identify Target Configuration

**If tool name provided in `$ARGUMENTS`:**
- Use specified tool (e.g., "zsh", "nvim", "git")
- Resolve its existing Make target; Neovim uses `make vim`, not `make nvim`.

**If `all` is provided:**
- Apply the machine's selected configuration with `make configure`.
- Do not enable every repository tool or replace the machine's selected sets.

**If no arguments:**
- Ask user which tool to configure
- Show available tools from Makefile targets

**Common tools:**
- zsh, bash, sh (shells)
- nvim, vim (editors)
- git, gh (version control)
- kitty, alacritty, wezterm (terminals)
- tmux (multiplexer)
- yabai, skhd (macOS window manager)

### 2. Understand Current State

**Check what's installed:**
```bash
# Verify symbolic links
ls -la ~/.<config-file>
readlink ~/.<config-file>

# Check if config directory exists
ls -la ~/.config/<tool>/
```

**Review existing configuration:**
- Read the machine file selected by `DOTFILES_CONFIG`, or `$XDG_CONFIG_HOME/dotfiles/config.toml` (default `~/.config/dotfiles/config.toml`).
- Run `make config` and `make plan` to inspect effective properties, their sources, and selected recipes before applying changes.
- Read current dotfiles: `~/.files/<tool>/`
- Read the existing Make target and its helper script.
- Identify linked files and their sources

### 3. Make Configuration Changes

**Based on user request:**
- Edit configuration files in `~/.files/<tool>/`
- Update related files (if tool has multiple configs)
- Follow project conventions:
  - No extra blank lines in markdown (single line breaks between paragraphs)
  - TOML comments on separate lines (not inline)
  - Consistent formatting

**Common operations:**
- Add new plugin/setting
- Update existing configuration
- Remove deprecated settings
- Reorganize structure

For a new tool, declare its recipe and configuration targets in
`bootstrap/tools.toml`, reuse the bootstrap installers, and add its `tools.<name>`
switch to the appropriate reusable set. Keep machine-specific selections and
overrides in the private machine TOML.

### 4. Test Configuration

**Install/reinstall the configuration:**
```bash
cd ~/.files
make <tool>
```

For `all`, preview and apply the selected plan instead:

```bash
make plan
make configure
```

**Verify the changes:**
- Check symbolic links are correct
- Test the tool works with new config
- Verify no broken links or missing files

**For specific tools:**
- **zsh**: `zsh -c 'echo $ZSH_VERSION'` or restart shell
- **nvim**: `nvim --version` and check for errors
- **git**: `git config --list | grep <setting>`
- **tmux**: `tmux source ~/.tmux.conf`

### 5. Commit Changes (if requested)

**Use selective versioning pattern:**

Only commit if:
- Configuration is stable and tested
- User explicitly requests versioning
- Changes are meaningful (not experimental)

**Commit process:**
```bash
cd ~/.files
git status
git add -f <tool>/<config-file>
# Write a Conventional Commit message from the staged diff
git commit -m "feat(<tool>): <description>"
```

**Note:** `.claude/` directory is globally gitignored. Use `git add -f` to force-add specific files when ready to version.

### 6. Sync to Other Systems (optional)

**If user wants to sync across machines:**
```bash
cd ~/.files
git push origin master
```

**On other machine:**
```bash
cd ~/.files
git pull origin master
make <tool>
```

## Common Scenarios

### Scenario 1: Add Neovim Plugin

```bash
/dotfiles/sync nvim

# Workflow:
# 1. Edit ~/.files/nvim/lua/plugins/<plugin-file>.lua
# 2. Add plugin configuration
# 3. Run: make vim
# 4. Test: nvim (verify plugin loads)
# 5. Commit if stable: git add -f nvim/lua/plugins/<file>.lua
```

### Scenario 2: Update ZSH Aliases

```bash
/dotfiles/sync zsh

# Workflow:
# 1. Edit ~/.files/sh/alias (shared across shells)
# 2. Add/modify aliases
# 3. Run: make zsh
# 4. Test: source ~/.zshrc
# 5. Commit if stable
```

### Scenario 3: Configure New Tool

```bash
/dotfiles/sync kitty

# Workflow:
# 1. Create ~/.files/kitty/kitty.conf (if not exists)
# 2. Add configuration
# 3. Update Makefile with kitty target (if needed)
#    Declare its recipe in bootstrap/tools.toml and select it through a set.
# 4. Run: make kitty
# 5. Test: kitty --version
```

### Scenario 4: Apply Selected Configuration

```bash
/dotfiles/sync all

# Workflow:
# 1. Run: make plan (inspect the baseline and selected additions)
# 2. Run: make configure (apply that selection)
# 3. Verify the selected configuration links and tools
```

## File Structure Reference

```
~/.files/
├── Makefile              # Installation targets
├── bootstrap.sh          # Dependency installer
├── bootstrap/tools.toml  # Tool recipes and configuration targets
├── config/sets/          # Reusable configuration bundles
├── <tool>/               # Tool-specific configs
│   ├── config-file       # Main config
│   └── subdir/           # Additional configs
└── .claude/
    └── settings.json     # User-specific (not versioned)

~/.claude/
├── commands/  -> ~/.files/claude/commands/   # Symlinked
└── agents/    -> ~/.files/ai/agents/     # Symlinked
```

## Makefile Target Pattern

```makefile
<tool>-config:
	@bash "$(MAKE_SCRIPTS)/config.sh" "$@" "$(DOTFILES)" "$(HOME)" "$(UV)" "$(UNAME_S)"
```

Keep Make declarative. Add configuration logic to the helper script and declare
the target in the tool catalog's `setup` list.

## Important Notes

- **Symlinks not copies**: Changes to `~/.files/` immediately affect `~/`
- **Experiment freely**: Changes aren't versioned until you `git add -f`
- **Selective versioning**: Only commit stable, useful configs
- **Test before committing**: Verify configs work before versioning
- **No `.claude/settings.json`**: Keep user-specific settings out of git

## Error Handling

**Broken symlinks:**
```bash
# Remove broken link
rm ~/.<config-file>
# Recreate with make
make <tool>
```

**Makefile target not found:**
- Read the Makefile and tool catalog to find the supported target or alias.
- Create new target if needed
- Follow existing pattern

**Permission issues:**
- Check file ownership: `ls -la ~/.files/<tool>/`
- Ensure files are readable: `chmod 644 ~/.files/<tool>/*`

## Integration with Other Skills

- **After config changes**: Use `/continue` to test and verify
- **Before PR**: Use `/pr-prep` to prepare dotfile updates for review
- **Document insights**: Use `/eureka` for config breakthroughs
- **Track failures**: Use `/stahp` for config approaches that didn't work

## Quick Reference

| Task | Command |
|------|---------|
| Update ZSH | `/dotfiles/sync zsh` |
| Update Neovim | `/dotfiles/sync nvim` |
| Update Git | `/dotfiles/sync git` |
| Apply selected sets | `/dotfiles/sync all` |
| Reinstall tool | `cd ~/.files && make <tool>` |
| Commit config | `git add -f <tool>/<file> && git commit` |
