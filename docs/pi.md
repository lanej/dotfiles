# Pi trial

[Pi](https://github.com/earendil-works/pi) is an optional coding-agent runtime. The dotfiles integration shares the existing Builder standard, skills, and agent instructions. It does not change the default coding client.

## Install

Run `BOOTSTRAP_PI=1 ./bootstrap.sh` to install `@earendil-works/pi-coding-agent` at version 1.4.0 or retain an already installed newer version, then configure its shared resources. Bootstrap installs Node 24 first. The Pi package is installed with npm lifecycle scripts disabled.

If Pi is already installed, run `make pi-config` (or `make pi`). These configuration targets do not download Pi. Authenticate and select a provider/model using Pi's own setup. The dotfiles installer does not copy credentials, configure providers, or edit Pi's settings.

This integration uses Pi's default `~/.pi/agent` directory. If you set `PI_CODING_AGENT_DIR`, its resources must be configured separately.

## Shared resources

| Source | Pi interface |
| --- | --- |
| Existing `ai/skills/` catalog | `~/.agents/skills/dotfiles`, already used by Codex and discovered by Pi |
| Shared Builder package | A managed guidance block in Pi's active user context file |
| `ai/agents/*.md` | `/dotfiles-<filename> <task>` prompt templates |

For example, `/dotfiles-code-reviewer review the current diff` asks the current Pi conversation to read and follow `ai/agents/code-reviewer.md`. Templates point at the shared files, so role edits are available without maintaining a separate Pi copy. Run `make pi-config` after adding or removing roles or changing the shared skill catalog, then `/reload` in running Pi sessions.

The templates are role prompts in the current conversation. They do not create subagents, choose models, or enforce the Claude tool names in agent frontmatter. In particular, the reviewer template does not restrict an otherwise writable Pi session. A runtime adapter must supply a restricted tool set when that boundary is required. Skills that depend on Claude-specific hooks or APIs also need an adapter before those capabilities work in Pi.

Local Pi prompts are preserved, including collisions with the `dotfiles-` names. Only generated templates with the installer's marker are refreshed or removed. Existing user guidance is retained around the managed Builder block; linked instruction files are left alone with an actionable error. The existing shared skill synchronizer retains its platform exclusions and standalone Builder package.

## Verification boundary

`make test-pi-resources` exercises the real configuration target in an isolated home. CI also uses Pi 1.4.0 to discover the installed resources without making a model request. Resource discovery does not establish that a model follows every shared instruction or that Claude-specific skills work unchanged.
