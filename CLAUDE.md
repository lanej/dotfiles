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
