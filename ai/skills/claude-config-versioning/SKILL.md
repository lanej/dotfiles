---
name: claude-config-versioning
description: Selective git versioning pattern for this dotfiles repo's Claude commands, agents, and skills — experiment freely under claude/commands/ and ai/{agents,skills}/ without polluting version control, then force-add the ones worth keeping. Use when deciding whether/how to version a new or edited command, agent, or skill file in this repo, or when asked about the gitignore/symlink mechanics behind ~/.claude/{commands,agents,skills,workflows}.
---

# Claude commands/agents/skills versioning pattern

This repository uses a selective versioning pattern for Claude commands, agents, and skills that allows for experimentation without polluting version control.

## Directory structure

```
~/.files/
├── ai/
│   ├── skills/       # Shared source directory (selectively versioned)
│   └── agents/       # Shared source directory (selectively versioned)
├── claude/
│   └── commands/     # Claude source directory (selectively versioned)
└── .claude/          # Gitignored (user-specific settings)
    └── settings.json

~/.claude/            # User's global Claude directory (real, not a symlink)
├── commands/         # Individual entries symlinked from ~/.files/claude/commands/
├── agents/           # Individual entries symlinked from ~/.files/ai/agents/
├── skills/           # Individual entries symlinked from ~/.files/ai/skills/
└── CLAUDE.md         # Symlinked to ~/.files/claude/CLAUDE.md
```

## Setup via Makefile

Run `make claude`. Symlinks `settings.json`, commands, agents, skills, workflows, and CLAUDE.md into `~/.claude/`, and wires MCP servers into `~/.claude.json` via `jq`. Use `make claude-shared` to refresh only shared skills and agents.

EP-specific skills live in `~/src/ep-dotfiles/`. Run `make link-skills` from there after cloning to symlink them into `~/.files/ai/skills/`.

## Workflow

1. **Experimentation**: Create/edit the file directly under `~/.files/claude/commands/`, `ai/agents/`, or `ai/skills/`
   - Run `make claude` to symlink new entries into `~/.claude/{commands,agents,skills}/`; use `make claude-shared` for skills and agents only (already-symlinked files update live since they point back to the same source; only brand-new files need the re-run)
   - Not automatically tracked by git (new files are gitignored by default)

2. **Selective versioning**: When ready to version a command:
   ```bash
   git add -f claude/commands/path/to/command.md
   git commit -m "feat(claude): add new command"
   ```

3. **Benefits**:
   - Experiment freely without polluting git history
   - Selectively version only stable/useful commands
   - Portable across machines via dotfiles
   - User-specific settings (`.claude/settings.json`) remain separate

## Examples

The pattern is already employed for several commands:
- `claude/commands/gh/fix-issue.md` - GitHub issue fixing workflow
- `claude/commands/eureka.md` - Capture technical breakthroughs
- `ai/agents/bug-reporter.md` - Evidence-based bug report drafting

## Gitignore configuration

`~/.claude/{commands,agents,skills,workflows}` are real directories; `make claude` symlinks each top-level entry in this repo's `claude/commands/` and `ai/{agents,skills}/` into them individually, so anything Claude Code, a plugin, or an installer writes as a *new* entry there stays local and never lands in the working tree. `.gitignore` still ignores new files under this repo's own `claude/commands/` and `ai/{agents,skills}/` by default; version one deliberately with `git add -f` (already-tracked files are unaffected). It also ignores repo-local `.claude/` state other than `settings.json` and `mcp-servers.json`, eval `results/`, skill-creator `*-workspace/` dirs, and packaged `*.skill` files. Anthropic-published skills are listed by name and never tracked (`ai/skills/ANTHROPIC-SKILLS.md`).

`.claude/settings.json` is tracked but rewritten in place by Claude Code; a `claude-settings` clean filter (`.gitattributes`, configured by `make claude`) drops bookkeeping keys such as `feedbackSurveyState` so they never show up as changes.

This pattern mirrors the approach used elsewhere in this repository (e.g., experimental scripts in `bin/` that are selectively versioned).
