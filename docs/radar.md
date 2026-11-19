# Tech Radar

<!-- Generated from radar.yaml. Edit the registry, then run: npm --prefix website run radar -->

Tool and technology decisions, organized by ring.

| Ring       | Meaning                                                    |
| ---------- | ---------------------------------------------------------- |
| **Adopt**  | In active use; recommended                                 |
| **Trial**  | Being evaluated; promising enough to run in real workflows |
| **Assess** | Worth watching; not yet trialed                            |
| **Hold**   | Not adopted; rationale documented                          |

***

## Adopt

### Neovim

[Neovim](neovim-pr-reviews.md): my editor for code navigation, editing, diagnostics, and pull request review. FzfLua provides fuzzy finding inside the editor; Octo is the default review UI, with ghlite available through a machine feature for review threads and pending feedback in ordinary source buffers.

### Git

Version control for the dotfiles and development work, with shared aliases, diffs, branch workflows, and worktree support.

### Zsh

My interactive shell, with shared aliases, completion, autosuggestions, and fuzzy navigation.

### Starship

Shared shell prompt showing directory, repository, runtime, and command context.

### Atuin

Searchable shell history integrated with the interactive shell.

### bat

Syntax-highlighted file viewing, manual pages, help output, and picker previews.

### fd

Fast file and directory discovery feeding fuzzy pickers and editor navigation.

### eza

Directory listings with icons, Git information, long views, and tree views.

### ripgrep

Fast text search across repositories, used directly and through editor and shell workflows.

### direnv

Directory-scoped environment loading for project-specific development contexts.

### delta

Readable Git diffs with syntax highlighting and structured changes in terminal review and previews.

### GitHub CLI

GitHub pull request, issue, check, and repository operations from the terminal.

### jq

JSON filtering, transformation, and inspection in command-line workflows.

### yq

YAML querying and transformation in command-line workflows.

### just

Named project commands and repeatable task recipes.

### tmux

Retained terminal multiplexer for existing sessions and agent-status integrations alongside Zellij.

### Claude Code

Coding agent used with shared skills, role instructions, and repository guidance. The repository-owned [skill-authoring workflow](skill-maintenance.md) maintains cross-host instructions without an external authoring plugin.

### Codex

Coding agent used with shared skills, role instructions, and repository guidance. Source-code setup installs repository-only publication guidance for projects that select Octo; the caller writes descriptions and [Octo validates format and publishes through pending receipts](octo-pr-submission.md), with daemon-backed tracking opt-in. Global Git and PR skills remain tool-neutral. Shared specification, writing, learning-capture, and handoff workflows use portable skill packages and the repository-owned [skill-authoring workflow](skill-maintenance.md).

### fzf

I use fzf for shell navigation and Neovim through FzfLua. A [standalone file-history helper](file-selection.md) shares frequency/recency scores between shell selections and editor file visits, supports global previously-used-file search, and prefers fewer directory levels then shorter paths when fuzzy scores tie. Shell and editor searches use smart case. The [directory and worktree picker](directory-picker.md) uses fzf's query matcher inside a Charmed terminal UI.

### Kitty

Terminal emulator. Implements tabs entirely within a single OS window — yabai sees exactly one window per Kitty instance, so tiling and focus work correctly.

### yabai

Tiling window manager via the macOS Accessibility API. Manages all windows at the OS level.

### Zellij

[Zellij](zellij.md): my adopted terminal multiplexer with tmux-style bindings and a compact layout in Kitty. Bootstrap installs version 0.45.1 or newer; `zj main` attaches to or creates a named session. Tmux remains available for existing agent-status integrations.

### Biome

Required correctness lint in the reusable [TypeScript profile](typescript-style.md), alongside typed ESLint and Prettier. Biome findings cannot be added to retrofit baselines.

### shfmt

[shfmt](https://github.com/mvdan/sh) formats the Git worktree runtime and its bootstrap/lint entrypoints. The catalog pin is shared by explicit installation and the shell CI check; `make shell-format` applies formatting and `make shell-format-check` checks it. Adoption expands through an explicit file list without reformatting unrelated shell features.

### worktree manager

[worktree](worktree-manager.md) creates identifiable repository-local agent checkouts, tracks full ownership and protects active tasks. Finishing protection and explicit safe pruning replace reusable Treehouse allocation for new agent work. Project updates select the latest stable Git release and compile the lifecycle-hook runtime locally from a shallow upstream clone with checked-in patches; no custom Git release is required.

### Source-code application stack

The [project tool-choice policy](../ai/skills/source-code-lifecycle/references/tool-choices.md) selects Commander for TypeScript/JavaScript CLIs, Cobra with lanej/charmed for Go CLI/TUI work, Typer/Rich/Textual for Python, clap/Ratatui for Rust, and React/Vite/Connect Query/TanStack Router for web applications. The project [CLI construction skill](../ai/skills/cli/SKILL.md) requires compact agent guidance through `skill` and `skill --topic` commands for applicable new CLI surfaces. It also selects validation, logging, configuration, and testing tools. Authority and adoption govern application independently of lifecycle stage, including research proofs of concept; existing stacks and upstream conventions are preserved according to project policy.

### Connect

[Connect](https://connectrpc.com/docs/introduction/) is the selected protocol for new application APIs we control under the [source-code adoption policy](repository-bootstrap.md#authority-and-tool-adoption), using Protobuf, Buf, generated clients/servers, and Protovalidate where supported. External services retain their protocols, and existing APIs migrate only within an explicitly agreed scope.

### Buf

Strict Protobuf compilation, lint, formatting, and compatibility checks through the reusable [source-code profile](repository-bootstrap.md#protobuf-correctness-profile), with a small native Buf check plugin rejecting string fields ending in `_json`.

### Ogen

[Ogen](https://ogen.dev/) is the preferred Go client generator for OpenAPI-described JSON APIs in the shared [Go guidance](../ai/skills/go/references/common.md#api-client-generation). Generate from authoritative specifications, pin generator versions, and preserve established project tools unless a migration is authorized.

### Project-scoped engineering guidance

[Source-code profiles](repository-bootstrap.md#optional-project-capabilities) own PR review and merge assessment, optional data-pipeline architecture, and optional UI acceptance. User-level guidance retains authorization, tool operation, and personal feedback. Viewrule installation does not impose application design policy or gates; project profiles preserve their selected lifecycle, authority, adoption, and existing conventions.

***

## Trial

### Beads and Dolt

[Beads](beads.md) provides a shared local work graph through one managed HTTP endpoint backed by a private Dolt SQL server. Native binaries are pinned and checksum-verified. Octo retains dispatch ownership; issue synchronization and an Octo adapter require separate integration.

### Mergiraf

[Mergiraf](mergiraf.md): selected by the `shell` set, with a machine-level `tools.mergiraf = false` opt-out. Installation activates syntax-aware Git merging for its supported file types. Runnable TOML, Lua, and JSON examples demonstrate combined independent edits and retained disagreements. Revisit the trial after reviewing resolutions during normal branch integration; Zsh remains outside the installed binary's advertised language coverage.

### Keylease

[Keylease](keylease-ssh.md): credential broker installed by dotfiles alongside Intent. Its native installer preserves active brokers and leases; Intent supplies the shared approval SDK.

### Intent

[Intent SSH approval](intent-ssh.md): one-time Mac approval library and transport tooling for remote commands and Go applications. The stable remote socket proof uses dedicated SSH connections; automatic production activation remains pending. Keylease remains installed separately as the credential broker.

### Paseo

[Paseo](paseo-tasks.md): a workspace and conversation interface I’m trialing with Pi. Codex and Claude use their native agent tools; their Paseo providers, hooks, tools, and orchestration skills are disabled. This trial is separate from the retired Firstmate workflow.

### Viewrule

[Viewrule](ui-review.md): my tool for rendered UI checks, screenshot references, and a feedback-to-rule workflow. Trial task-specific density rules against actual rejected and accepted screens before promoting them globally.

### Commander

[Commander](https://github.com/tj/commander.js): capability-grouped TypeScript CLI parsing, validation, and generated help in Octo Manager. Evaluate command discovery and agent-friendly usage during normal operation.

***

## Assess

### Pi

[Pi](pi.md): a composable agent runtime under assessment. It can reuse the existing shared skills, Builder guidance, and role instructions. Assess supervision, review results, and status reporting before starting a trial.

### AeroSpace

[AeroSpace](https://github.com/nikitabobko/AeroSpace) is a tiling WM that operates at the app level rather than hooking into the macOS window server. It may handle Ghostty's native `NSWindowTabGroup` tab grouping without the window-jumping issue that currently blocks a Ghostty migration (see **Hold: Ghostty**).

***

## Hold

### Firstmate through Paseo and GitHub

[Firstmate mobile workflow](firstmate-mobile.md): former mobile coordination workflow through Paseo, Pi, and GitHub. Retired from my workflow; no longer being evaluated.

### Superpowers

Claude Code workflow plugin. Removed from the shared settings at the owner's request in favor of the remaining official plugins and custom skills. Skill maintenance now uses the repository-owned [skill-authoring workflow](skill-maintenance.md), without an external authoring-plugin prerequisite.

### OpenCode

AI coding assistant with a TUI interface. Put on hold due to memory leaks during long sessions and persistent lag in supporting new model releases — discovered while working around a Vertex AI 1M context window bug that required a [upstream PR](https://github.com/anomalyco/opencode/pull/14055) to fix.

Revisit if memory stability improves and model support keeps pace with provider releases.

### Ghostty

Ghostty implements tabs as native macOS `NSWindowTabGroup` windows — `tabbingMode` is set to `.preferred`/`.automatic` in the source regardless of `macos-titlebar-style`. Yabai sees each tab as a separate managed window, causing the active window to jump and resize on every tab switch. There is no config option to set `tabbingMode = .disallowed`.

A workaround was attempted using Yabai signals to force BSP layout on each Ghostty window event, but it did not resolve the jumping behaviour:

```sh
yabai -m signal --add app='^Ghostty$' event=window_created action='yabai -m space --layout bsp'
yabai -m signal --add app='^Ghostty$' event=window_destroyed action='yabai -m space --layout bsp'
```

Revisit if AeroSpace (see **Assess**) proves able to handle native tab groups transparently.

### andrej-karpathy-skills

A Claude Code plugin packaging four behavioral principles (think before coding, simplicity, surgical edits, goal-driven execution) attributed to Karpathy's coding agent guidelines. Evaluated and skipped — the global CLAUDE.md already covers all four principles, often more precisely and with harder edges. No executable tooling, MCP servers, or commands; purely policy text.

### sccache

Rust compiler cache. Grows unboundedly on disk — even with `max_cache_size` set, the cache frequently bloats to tens of gigabytes across multiple projects and toolchain versions. The disk pressure outweighs the incremental build-time savings for typical dotfiles/personal project usage.

Revisit if Mozilla ships more aggressive eviction or if a per-project cache isolation story emerges.
