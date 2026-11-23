# Pi

[Pi](https://github.com/earendil-works/pi) is an optional coding-agent runtime. The dotfiles integration shares skills and role instructions. The [Studio daily driver](https://github.com/lanej/studio#readme) adds the shared theme, task browser, idle compaction, work/personal profiles and a terminal workflow for an existing Beads task. Start it from Zellij, steer the Pi worker in its managed checkout and inspect the outcome from a separate terminal with Paseo offline.

The [runtime integration plan](https://github.com/lanej/studio/blob/main/RUNTIME.md) evaluates existing Pi packages for subagent delegation and session management, with adapters for the native worktree manager, Beads authority, Octo feedback delivery, and the merge/removal/archive sequence. It separates the next read-only delegation increment from task-bound coding and the complete delivery lifecycle.

## Install

Select `pi = true` under `[tools]` in the machine TOML and run `make install` to install the configured standalone Pi release and share its resources. The installer places the launcher at `~/.local/bin/pi`. If an older npm launcher appears first in your shell, open a new shell or put `~/.local/bin` first on PATH.

Studio is included in the `workstation` set. Select it independently with `studio = true` under `[tools]`, or override it with `studio = false`. Run `make install`, or `make studio-install` for an explicit Studio-only installation. The installer clones a missing `~/src/studio` checkout, provisions the project-pinned private Bun runtime, and calls Studio's own installer to register its bundled Pi resources. Reruns preserve the checkout revision, local edits, unrelated Pi settings, and active sessions. Configuration-only `make` does not install or download Studio. Optional Beads, Zellij, worktree, and Octo integrations remain separately configured.

If the installer reports an unmanaged launcher at `~/.local/bin/pi`, move that launcher aside before retrying.

If Pi is already installed, run `make pi` to share resources. `make pi-config` removes retired Firstmate integration registrations while preserving unrelated Pi settings and saved work. These configuration targets do not download Pi. Authenticate and select a provider/model using Pi's own setup. The shared-resource synchronizer does not copy credentials or configure providers.

This integration uses Pi's default `~/.pi/agent` directory. If you set `PI_CODING_AGENT_DIR`, its resources must be configured separately.

## Shared resources

| Source | Pi interface |
| --- | --- |
| Existing `ai/skills/` catalog | `~/.agents/skills/dotfiles`, already used by Codex and discovered by Pi |
| User guidance | Existing instructions are preserved; retired managed Builder blocks are removed |
| `ai/agents/*.md` | `/dotfiles-<filename> <task>` prompt templates |

For example, `/dotfiles-code-reviewer review the current diff` asks the current Pi conversation to read and follow `ai/agents/code-reviewer.md`. Templates point at the shared files, so role edits are available without maintaining a separate Pi copy. Run `make pi` after adding or removing roles or changing the shared skill catalog, then `/reload` in running Pi sessions.

The templates are role prompts in the current conversation. They do not create subagents, choose models, or enforce the Claude tool names in agent frontmatter. In particular, the reviewer template does not restrict an otherwise writable Pi session. A runtime adapter must supply a restricted tool set when that boundary is required. Skills that depend on Claude-specific hooks or APIs also need an adapter before those capabilities work in Pi.

Local Pi prompts are preserved, including collisions with the `dotfiles-` names. Only generated templates with the installer's marker are refreshed or removed. Existing user guidance is retained while retired managed Builder blocks are removed; linked instruction files are left alone with an actionable error. The existing shared skill synchronizer retains its project-only and platform exclusions.

## Verification boundary

`make test-pi-resources` exercises the real configuration target in an isolated home. CI also uses Pi 1.4.0 to discover the installed resources without making a model request. Resource discovery does not establish that a model follows every shared instruction or that Claude-specific skills work unchanged.

Studio owns the daily-driver source, installation, and checks in [lanej/studio](https://github.com/lanej/studio). Dotfiles installation uses its [project-owned installer](https://github.com/lanej/studio#install) and project-pinned Bun version. Dotfiles registers that checkout with `project-update`: use `project-update pull studio`, `project-update build studio`, and `project-update restart studio`, or `project-update update studio` for the sequence. Restart reports that Pi needs a manual reload or relaunch; it preserves running sessions. Studio installation remains separate from the standalone Pi launcher and shared-resource configuration above.
