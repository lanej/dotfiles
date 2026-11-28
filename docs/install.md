# Installation

**Run `make` to apply configuration. Run `make install` to install selected tools and configure them.** Both use this machine's [configuration sets](configuration.md).

## Set up a new machine

Requires Git, Make, and Bash on macOS or Linux. The [one-line quick start](index.mdx#quick-start) clones or reuses `~/.files` and runs the minimal bootstrap. To run each step yourself:

**1. Clone and initialize the native configuration.**

```sh
git clone https://github.com/lanej/dotfiles.git ~/.files
cd ~/.files
make base
```

**2. Choose this machine's tools.** Edit `~/.config/dotfiles/config.toml`; use `workstation` for the broad setup, then add work-context sets or individual overrides as needed:

```toml
sets = ["workstation"]
```

The file respects `XDG_CONFIG_HOME` and `DOTFILES_CONFIG`. `make base` creates it only when missing and selects the native `macos` or `linux` baseline. See [configuration composition](configuration.md) for available sets and override examples. To add Mermaid CLI and its headless browser for Neovim diagrams, set `tools.mermaid = true`.

**3. Bootstrap, preview, and install.**

```sh
make bootstrap
make plan
make install
```

Open a new shell after setup to load the linked shell configuration.

## Choose a setup command

| Command | Use it to |
| --- | --- |
| `make` | Reapply the native baseline, selected bundles, and individual overrides. Configuration only; requires Python 3.11+. |
| `make base` | Initialize missing machine TOML and link the built-in native baseline, without Python. |
| `make shell git` | Link basic shell and Git configuration without Python. |
| `make bootstrap` | Apply the native baseline and install only uv and Python. Ignores machine TOML. |
| `make plan` | Preview the selected tools and configuration before installation. |
| `make install` | Install selected tools and apply their configuration and integrations. Ensures uv and Python are available first. |

`make configure`, `make setup`, and `make all` are aliases for `make`. `bash bootstrap.sh` and `bash bootstrap.sh install` are the script equivalents of the two installation stages. Neither stage pulls updates or switches branches. Linting and tests run separately with `make lint` and the `test` targets.

`make lua-check` runs StyLua and Luacheck on every tracked or untracked, non-ignored Lua source file, including Neovim, WezTerm, tests, scripts, fixtures, and generated modules. `make lua-format` applies formatting before analysis. The editor tool set installs both tools through Homebrew, APT, or Pacman; other systems need Luacheck installed with LuaRocks first. Generated data tables retain their generator's layout with StyLua directives; parsing and static analysis still cover those files. The Lua quality workflow runs the same check for Lua changes in pull requests and on `master`.

## Update an existing machine

From the checkout, pull the latest changes and reapply configuration:

```sh
cd ~/.files
git pull --ff-only
make
```

Open a new shell to load shell changes. Run `make plan` followed by `make install` if you also want to install newly selected tools.

## Shell completions

**`recomp` is the completion refresh helper.** Run it in the current Zsh session after installing a supported CLI or adding a completion file:

```sh
recomp
```

It regenerates completions for supported tools on `PATH`, clears stale completion definitions, and reloads completion in the current shell. No shell restart or plugin setup is needed.

| Command | Effect |
| --- | --- |
| `recomp` | Generate completions and reload the current Zsh session. |
| `recomp add <tool>` | Find a generator, register it locally, and load its completion now. |
| `make zsh-completions` | Generate completion files only; open a new shell afterward. |
| `make` / `make configure` | Generate completions as part of configuration when the shell set is selected. |

`make install` and `make zsh-config` also generate completions. Supported tools include fd, uv, Rust, GitHub CLI, Codex, Zellij, and Atuin; [the generator script](../scripts/make/completions.sh) lists every built-in command. Missing tools are skipped. Tools without generators continue using packaged completions or existing shell integrations.

### Register a local tool

Use `recomp add` for a work-only or other locally installed CLI:

```sh
recomp add epf
```

For a new tool, it tries `epf completions zsh`, then `epf completion zsh`. It validates the output before saving the working command and loads the completion in the current shell. Existing local registrations and built-in generators are reused first. Both the target and generator must already be installed.

For a different command or an override, supply the generator explicitly:

```sh
recomp add cargo \
  rustup completions zsh cargo
```

Registrations stay outside the checkout in `~/.config/dotfiles/completions` (or `$XDG_CONFIG_HOME/dotfiles/completions`). Future `make` and `recomp` runs reuse the saved command. Repeating the same registration leaves the file unchanged; an explicit replacement updates that tool's entry without duplicating it. Built-in generators need no extra local entry unless you override them.

Failed validation leaves the registry and last working completion intact. Hand-written completion files and symlinks are preserved. If the registry itself is a symlink, edit it directly so its managed destination stays intact.

<details>
<summary>Edit the local registry manually</summary>

Each non-comment line contains a completion name, a generator command, and its arguments, separated by spaces or tabs. For example:

```text
epf epf completions zsh
```

Local entries override built-ins, and the first entry for a name wins. Run `recomp` after editing. Arguments are literal words: shell quoting, expansions, and pipelines are not evaluated. `recomp add` rejects arguments containing whitespace; put complex commands in an executable wrapper on `PATH` and register that command instead. Missing targets are skipped during normal refresh; registration does not install software.

</details>

<details>
<summary>Completion files, preservation, and older fd versions</summary>

Generated files live at `~/.zsh/completions/_<tool>`. Failed or empty generators report failure and keep the last working file. Hand-written files and symlinks are preserved; move one aside and rerun setup to let dotfiles manage it. Unchanged output preserves the file and cache; changed output invalidates the dump for the next shell. `recomp` also picks up completion files added by hand and ignores insecure completion directories.

Older fd builds without `--gen-completions` use their packaged `_fd` from standard Zsh completion locations or the fd release directory. If neither source is available, setup explains how to install it and preserves the previous file. `make test-zsh-completions` exercises generation and active-shell refresh.

</details>

## Recover an incomplete setup

The configuration checklist shows green `✓` for completed steps and red `✗` with diagnostics for incomplete steps. Independent steps continue after a failure; the command exits nonzero after the full checklist if anything needs attention. Install missing dependencies or fix the reported issue, then rerun the same target. Existing links and user configuration are safe to reuse.

Zsh starts silently during a partial install, keeping the basic prompt, completion, and history available. The custom fzf integration activates in a new shell when both `fzf` and `fd` are installed. Failed integration generators keep working cached hooks. Existing fzf-tab and tmux plugin directories are preserved, including local tmux plugins without Git metadata; failed TPM installation reports an error for manual recovery.

The native platform set is selected automatically; explicitly requesting unsupported platform tools fails before writing configuration.

| Set | Native configuration |
| --- | --- |
| `linux` | X11, Polybar, bspwm/sxhkd/rofi |
| `macos` | Yabai/skhd |

Color is enabled in terminals. Use `NO_COLOR=1` to disable it or `CLICOLOR_FORCE=1` to enable it in captured output. The [setup requirements](setup-requirements.md) record the intended boundaries and acceptance criteria.

Try the native transient prompt in one interactive shell with `DOTFILES_ZSH_PROMPT=transient zsh`. A Powerline notch marks the start of the Git branch segment after the directory. When available, the `shortpath` helper shortens each parent directory to its shortest unique sibling prefix and keeps the current directory in full. These abbreviations are display labels. The branch segment includes commits ahead or behind upstream, and a separate segment groups conflicts, staged changes, unstaged changes, and untracked files. Accepted commands retain a `$` marker in scrollback. The marker uses the terminal's error color after a failed command. Exit the trial shell to return to the parent shell. [Shortpath installation](../tools/shortpath/README.md#install)

<details>
<summary>Check shell startup and measure performance</summary>

`make test-zsh-startup` checks partial-install startup. `make benchmark-zsh-startup` measures the current home's interactive login-shell startup and exit over 30 runs after three warmups. It reports median and p95 wall time for `zsh -d -i -l -c exit`, including process launch and logout, with global rc files skipped. It inherits your `HOME` and `PATH`; run it on your workstation for representative timings. Use `ZSH_BENCHMARK_ARGS='--runs 60 --json'` for more samples and JSON output.

</details>

## AI tool integrations

| Command | Integration |
| --- | --- |
| `make claude-shared` | Link shared `ai/skills` and `ai/agents` into Claude's installed directories, preserving local entries. Included in `make claude`. |
| `make codex` | Expose shared `ai/skills` through `~/.agents/skills/dotfiles`, preserving local Codex skills. |
| `make codex-skills` | Refresh normalized file-linked or lowercase skill entrypoints in `~/.codex/dotfiles-skills`. Missing external sources are reported and skipped. |

`make configure` with the AI bundle (or `make claude`) also removes user-scope Claude Code plugins listed in [`claude/blocked-plugins.json`](../claude/blocked-plugins.json) when the Claude CLI is available. Add a marketplace-qualified ID there to retire a plugin; Superpowers is the initial entry. Already-absent plugins are a no-op. Invalid configuration, inspection, or uninstall failures mark that step incomplete.

## Worktree tracking and resource limits

The [agent worktree launchers](treehouse-launchers.md) use the [worktree manager](worktree-manager.md) for fresh task checkouts with explicit finish protection and safe pruning. The `ai` set selects the manager; the optional `worktrees` bundle installs it for standalone use. Existing Treehouse allocations retain their ownership records and guarded recovery path, and pool directories remain protected.

The optional [worktree policy](git-worktree-policy.md) tracks linked worktrees across registered repositories, including worktrees created outside the agent launchers, and supports independent per-repository and global count and disk budgets. Limits are disabled by default.

The base set installs the [patched Git runtime](git-worktree-hooks.md#install-through-dotfiles) from a pinned platform package. Shared Git configuration enables global tracking and admission hooks without per-repository installation; budgets remain disabled until configured. Stock Git keeps inventory refreshed through `post-checkout`; callers need explicit preflight checks to block creation. Legacy Treehouse leases remain independent of this machine-wide inventory.

## Shared shell history

With the Atuin recipe selected, `make install` configures sharing when an explicit sync host or saved account is available.
Have current dotfiles installed in `~/.files` on the SSH host and authenticate
to any bastion first. Choose another host with
`ATUIN_SYNC_HOST=dev2 make install`.

To configure sharing again without reinstalling other tools:

```sh
make atuin-sync                         # configure sharing with dev
make atuin-sync ATUIN_SYNC_HOST=dev2     # use another SSH alias
```

The target installs matching Atuin clients and a Linux server, starts a private
SSH tunnel, and merges existing history. Reruns reuse the account and encryption
key. Original stores stay intact; recovery details are saved with owner-only
permissions at `~/.local/share/atuin/self-hosted-account.json` on both machines.
A replacement Mac can recover those details over SSH from the configured server.
Unlock your SSH agent and authenticate to any bastion before running the target.

## Machine migration

From the checkout:

```sh
sh transfer.sh
```
