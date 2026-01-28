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
model: haiku
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
- **bootstrap.sh**: Installs packages and dependencies
- **Selective versioning**: Only commit stable/useful configurations

## Usage

```bash
/dotfiles/sync [tool-name]  # Update specific tool config
/dotfiles/sync all          # Update all configs
/dotfiles/sync              # Interactive mode
```

## Workflow

### 1. Identify Target Configuration

**If tool name provided in `$ARGUMENTS`:**
- Use specified tool (e.g., "zsh", "nvim", "git")

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
- Read current dotfiles: `~/.files/<tool>/`
- Check Makefile target: `grep -A 10 "^<tool>:" ~/.files/Makefile`
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

### 4. Test Configuration

**Install/reinstall the configuration:**
```bash
cd ~/.files
make <tool>
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
# Use git-commit-message-writer agent for commit message
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
# 3. Run: make nvim
# 4. Test: nvim (verify plugin loads)
# 5. Commit if stable: git add -f nvim/lua/plugins/<file>.lua
```

### Scenario 2: Update ZSH Aliases

```bash
/dotfiles/sync zsh

# Workflow:
# 1. Edit ~/.files/sh/aliases (shared across shells)
# 2. Add/modify aliases
# 3. Run: make zsh
# 4. Test: source ~/.zshrc
# 5. Commit if stable
```

### Scenario 3: Configure New Tool

```bash
/dotfiles/sync kitty

# Workflow:
# 1. Create ~/.files/kitty/kittyconf (if not exists)
# 2. Add configuration
# 3. Update Makefile with kitty target (if needed)
# 4. Run: make kitty
# 5. Test: kitty --version
```

### Scenario 4: Sync All Configs

```bash
/dotfiles/sync all

# Workflow:
# 1. Run: make (installs all targets)
# 2. Verify all symbolic links
# 3. Test each tool
```

## File Structure Reference

```
~/.files/
├── Makefile              # Installation targets
├── bootstrap.sh          # Dependency installer
├── <tool>/               # Tool-specific configs
│   ├── config-file       # Main config
│   └── subdir/           # Additional configs
└── .claude/
    └── settings.json     # User-specific (not versioned)

~/.claude/
├── commands/  -> ~/.files/claude/commands/   # Symlinked
└── agents/    -> ~/.files/claude/agents/     # Symlinked
```

## Makefile Target Pattern

```makefile
<tool>:
	@mkdir -p $(HOME)/.config/<tool>
	@ln -fs $(DOTFILES)/<tool>/config $(HOME)/.config/<tool>/config
```

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
- Check available targets: `make help` or `grep "^[a-z]" Makefile`
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
| Install all | `/dotfiles/sync all` |
| Reinstall tool | `cd ~/.files && make <tool>` |
| Commit config | `git add -f <tool>/<file> && git commit` |
