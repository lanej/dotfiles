# Configuration sets

The full install and configuration stages read the same TOML configuration at `~/.config/dotfiles/config.toml` (or `$XDG_CONFIG_HOME/dotfiles/config.toml`). OS detection selects the `macos` or `linux` baseline; additional tools and work context are explicit, and the hostname has no effect.

The built-in native baseline (`make base`) and basic linking targets such as `make shell git` need only Make, Bash, and standard system utilities. Default `make` and configuration-driven targets such as `make config` and `make plan` require Python 3.11+; `make bootstrap` installs that runtime before the full installation stage.

```sh
make base # Initialize the machine TOML with the detected native set.
# Edit the selected sets, then inspect their resolved settings and source files.
make bootstrap
make config
```

For example:

```toml
sets = ["workstation", "easypost"]

# Individual properties override the composed bundles.
[tools]
mermaid = true
neovim = false

[zellij]
source = "release"
```

| Set | Groups |
|---|---|
| `base` | Patched Git with worktree hooks and shared settings; always applied |
| `shell` | Zsh, history, search, navigation, and command-line tools; selected by default |
| `terminal` | Tmux, Zellij, terminal configuration, font, and monitoring; selected by default |
| `editor` | Neovim, formatters, language servers, and parser tooling |
| `development` | Language runtimes, Rust maintenance, and development cache configuration |
| `ai` | Claude, Codex, worktree manager, and agent status |
| `octo-manager` | Opt-in Octo service with Codex tracking and receipt hooks |
| `worktrees` | Standalone worktree manager with task protection, tracking, optional limits, and explicit safe pruning |
| `workstation` | Adds editor, development, AI tools, source-code project setup, Studio, mail, and Quarto configuration |
| `macos` | Yabai/skhd installation and their configuration |
| `linux` | X11, Polybar, and bspwm configuration for separately installed desktop tools |
| `easypost` | GitHub app access off, EasyPost direnv integration, and Bedrock setup |
| `personal` | GitHub app access on, EasyPost direnv and Bedrock setup off |

Git and the native platform baseline apply first, followed by the default `shell` and `terminal` bundles, then additional selected sets. The `ai` bundle selects the [worktree manager](worktree-manager.md); Treehouse is disabled by default and can be selected separately with `tools.treehouse = true`. Set `tools.git-worktree-hooks = false` to keep standard Git. Set `tools.wezterm = true` to link the WezTerm configuration for a separately installed copy. A headless host can disable terminal and desktop recipes individually. On Linux, set `tools.x11`, `tools.polybar`, and `tools.bspwm` to `false`, or maintain a private `linux` set. Work context and additional tool bundles are never inferred from the hostname.

The repository maintains sets in [`config/sets`](../config/sets). Add private sets under `~/.config/dotfiles/sets/`; local files take precedence over repository sets of the same name, except `base`. A set can include other sets with its own `sets = [...]` list. Dependencies apply before the including set, each named set applies once, and later sets override earlier properties. Machine properties apply last, including overrides to native platform tools. The always-applied `base` supplies Git and shared property defaults, followed by the native OS set and the default `shell` and `terminal` sets. An unconfigured `make install` selects those tools; machine properties can disable individual tools.

Each `[tools]` property enables or disables one catalog recipe. Shared tool dependencies are added once and installed first. Explicitly disabling a required dependency, selecting an unsupported platform tool, or naming an unknown property fails before the tool plan runs. `false` skips that recipe; it does not uninstall an existing application or change that application's own package/plugin management. GUI, mail, and Ruby entries retain the existing configuration-only behavior; those applications are installed separately.

[`bootstrap/tools.toml`](../bootstrap/tools.toml) owns direct package pins, dependencies, installers, Make configuration targets, and preparation/post-install hooks. The checked-in [`config/targets.mk`](../config/targets.mk) is generated from that catalog and the built-in native sets, keeping `make base` independent of Python. This first-stage baseline links Git, shell helpers, and native OS configuration without installing software, and does not read machine settings or private sets. Default `make`, `make install`, and `make configure` resolve the full TOML configuration and respect individual overrides, including native platform tool disables. Use `make config` to inspect values and their sources, or `make plan` to inspect the resolved baseline, full tool selection, and execution phases without applying them.

Use `make install DOTFILES_CONFIG=/path/to/machine.toml` or `DOTFILES_CONFIG=/path/to/machine.toml bash bootstrap.sh install` for an alternate configuration. The full stage rejects a missing explicitly selected file. Every catalog tool has a boolean `tools.<name>` property; `codex.github_enabled` controls Codex GitHub access and `zellij.source` selects `"patched"`, `"release"`, or `"main"`.

For a versioned package recipe, the installer first checks the installed version, then prefers a catalog fallback or a custom release or source installer. A catalog entry such as `fallback = { via = "cargo", package = "fd-find" }` supplies that direct install path. npm fallbacks use `~/.local` or the active NVM installation under `~/.nvm` so upgrades replace older NVM launchers. If the direct install fails, the installer can try a sufficiently recent system package. `via` accepts `cargo`, `go`, or `npm`. The optional fallback `package` defaults to the recipe’s package name. Use the crate name for Cargo, the full install path for Go, and the registry package name for npm. Declare `rust`, `go`, or `node` in `requires` so the resolver schedules that runtime first. The fallback uses the recipe’s version and the installer verifies the resulting executable.

Tools that need custom download verification, platform-specific steps, or integration use dedicated installers. A versioned package can use an `install_<package>_from_release` or `install_<package>_from_source` adapter in [`bootstrap.sh`](../bootstrap.sh), which can call a script under [`scripts/`](../scripts/). For example, Bun delegates to its runtime installer and Atuin handles archive verification before placing the executable. Each tool’s selection, version, and dependencies stay in the catalog.

During `make install`, consecutive plain `system` recipes with no prerequisites share a single package-manager invocation for the commands missing from `PATH`. For example, a fresh machine can install Zsh and tmux in one call. The installer verifies that the requested commands are available before moving on. On Linux, the installer reports when it uses `sudo` to install missing system packages. Versioned recipes and system recipes with custom installers or prerequisites run in plan order.

Neovim installs Taplo through Mason and automatically uses the checkout's local [JSON Schema](../config/schema.json) for these settings, private sets, and repository examples. This provides property and value completion, hover documentation, and inline diagnostics for wrong types, unsupported values, and unknown properties. The schema is read locally; its use does not depend on a hosted schema. Set names can reference private files, so missing sets and dependency cycles remain runtime checks. If you select an alternate machine file outside the conventional directory, launch Neovim with the same `DOTFILES_CONFIG` environment variable.

Other Taplo-based editors can associate the same local schema or use a header comment such as `#:schema file:///absolute/path/to/dotfiles/config/schema.json`. The repository's `.taplo.toml` associates its example and set files automatically. The schema and Python-free Make target list are generated from the runtime definitions; `make test-dotfiles-config` checks that neither has drifted. After changing settings, native sets, or the tool catalog, regenerate them with:

```sh
python3 scripts/dotfiles-config.py --format schema > config/schema.json
python3 scripts/dotfiles-config.py --format make-targets > config/targets.mk
```

`make test-dotfiles-config-editor` checks the real Neovim/Taplo editing workflow and requires both tools on `PATH`.

`IS_EASYPOST` and `BOOTSTRAP_MERMAID` are retired. Select `easypost` or `personal` and set `tools.mermaid` directly. Existing installations should select `workstation` and run `make install` for the previous broad installation; the native platform set is automatic. Use `make` to reapply the selected configuration without installing tools. Personal machines must explicitly select `personal` to enable GitHub app access. Rerun `make codex-permissions` and reload Codex to apply that access choice. Rerun `make zellij-runtime` to apply a runtime source change, then restart existing Zellij session servers. Set selection does not uninstall previously installed optional tools. For local PR monitoring, see [the opt-in Octo Manager setup](octo-manager.md).

`make codex` converts the shared `ai/agents` Markdown files (including
external symlinks) into personal agents in `~/.codex/agents/*.toml`.
Names, descriptions, and instructions are preserved; Claude model aliases and
tool lists are omitted so agents inherit Codex's model and tools. Agents limited
to Read/Glob/Grep receive a read-only sandbox. Local Codex agents are preserved,
including name collisions. Rerun `make codex-agents` after changing agent
sources, then start a new Codex session. Missing external sources are reported
and skipped.

Codex MCP servers are manually curated in `~/.codex/config.toml`. Setup preserves
user removals, disabled servers, and custom settings; it does not import servers
from Claude or its plugins. The old `codex-mcp` target and importer are retired.
See Codex's
[MCP configuration documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

`make codex` also installs the shared Claude/Codex tmux window-status hooks.
Run `make codex-tmux` for just this integration, then restart Codex and trust
the new handlers with `/hooks`. The shell's `codex` function uses `--no-daemon`
inside tmux so hooks inherit the launching pane. See
[tmux window status](tmux.md#claude-and-codex-window-status) for the states
and event mapping.
