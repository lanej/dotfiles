# Maintaining dotfiles agent configuration

Dotfiles owns the shared workstation instructions in `codex/` and `claude/`, skills in `ai/skills/`, agents in `ai/agents/`, and commands in `claude/commands/`. Keep organization-specific guidance in its owning organization or project configuration.

New entries under `ai/{agents,skills}/` and `claude/commands/` are ignored by default so local experiments stay local. Deliberately version a repository-owned entry with `git add -f PATH`; tracked files remain tracked. Anthropic-published skills remain external; see [the external skill policy](../ai/skills/ANTHROPIC-SKILLS.md).

Read [the skill-maintenance policy](skill-maintenance.md) before changing instruction sources. Run the affected checks and review the staged diff before committing. Use [the setup requirements](setup-requirements.md) and [the configuration guide](../README.md#configuration-sets) when changing configuration or installation.

## Workstation installation

`make claude-config` links Claude settings, global instructions, and top-level commands and workflows into real directories under `~/.claude/`. `make claude-shared` refreshes shared skills and agents. Existing links point to their source files, so edits are live in the owning checkout; rerun the relevant target to discover new entries or retire broken managed links. These operations apply workstation configuration and are separate from installing project engineering guidance.

The `.claude/settings.json` source is tracked. The `claude-settings` Git clean filter configured by `make claude-config` removes bookkeeping keys such as `feedbackSurveyState`. Preserve unrelated local entries. Codex MCP configuration is manually curated; do not import or re-enable servers as a side effect.

## Dotfiles as a source-code project

`source-code.toml` declares this repository’s beta, owned tool profile with new-surface adoption. `AGENTS.override.md` routes to the authored repository instructions and the installed `.agents/source-code.md` policy. Codex reads `.agents/skills/`; Claude uses repository-local `.claude/skills/` links to those same packages. These project instructions are distinct from the workstation sources this repository distributes.

From this checkout, preview and refresh the installed profile with:

```sh
bin/source-code setup --repo . --authority owned --adoption new --conflict skip --dry-run
bin/source-code setup --repo . --authority owned --adoption new --conflict skip
bin/source-code validate --repo . --strict
```

Review the preview before applying it. The explicit skip preserves this repository’s customized `.github/workflows/python-quality.yml`, including its scoped path filters and macOS/Linux matrix. Do not use replacement to discard customizations. Existing Python paths and test commands stay in `.python-quality.json`; provision its tools with `python3 scripts/check-python.py tools` and run its checks with `python3 scripts/check-source-code.py python`. Other language guidance is installed without adding root-level check profiles for the nested applications and examples. Their existing checks remain authoritative.

Commit the managed profile, installed packages, and `.agents/repo-bootstrap.json` together. Keep unrelated local agent state untracked. Start a new agent session or reload skill discovery after installing or refreshing the profile.
