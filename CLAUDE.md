# Claude Code Project Guidelines

This document contains project-specific guidelines for working with this dotfiles repository in Claude Code.

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

~/.claude/            # User's global Claude directory
├── commands/         # Symlinked to ~/.files/claude/commands/
└── agents/           # Symlinked to ~/.files/claude/agents/
```

### Setup via Makefile

The `make claude` target (Makefile:155-161) establishes the symlinks:

```makefile
claude:
	@mkdir -p $(HOME)/.claude
	@mkdir -p $(HOME)/.claude/local
	@ln -fs $(DOTFILES)/.claude/settings.json $(HOME)/.claude/settings.json
	@ln -fns $(DOTFILES)/claude/commands $(HOME)/.claude/commands
	@ln -fns $(DOTFILES)/claude/agents $(HOME)/.claude/agents
	@ln -fs $(DOTFILES)/bin/claude-wrapper $(HOME)/.claude/local/claude-wrapper
```

### Workflow

1. **Experimentation**: Create/edit commands in `~/.claude/commands/` (or agents in `~/.claude/agents/`)
   - Changes appear immediately in `.files/claude/` due to symlink
   - Not automatically tracked by git (`.claude/` is globally gitignored)

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
- `claude/commands/gh/review-pr.md` - Pull request review workflow
- `claude/commands/eureka.md` - Capture technical breakthroughs
- `claude/agents/commit-message-generator.md` - Git commit message generation

### Gitignore Configuration

- **Global** (`~/.gitignore`): Ignores `.claude/` directory
- **Local** (`.files/.gitignore`): No special Claude rules needed
- Use `git add -f` to force-add specific commands when ready to version

This pattern mirrors the approach used elsewhere in this repository (e.g., experimental scripts in `bin/` that are selectively versioned).

## OpenCode Configuration

`~/.config/opencode/opencode.json` is **generated** by `make opencode` — do not edit it directly.

The source template is `.opencode/opencode.json`. It uses `$HOME` placeholders that are expanded via `envsubst` at install time. Always edit the template, then run `make opencode` to regenerate.

```
.opencode/opencode.json          ← EDIT THIS (template with $HOME placeholders)
~/.config/opencode/opencode.json ← GENERATED (do not edit)
```

Running `make opencode` will:
1. Remove the old file/symlink at `~/.config/opencode/opencode.json`
2. Run `envsubst` to expand `$HOME` and write the result
