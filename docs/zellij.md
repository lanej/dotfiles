# Zellij with the tmux bindings

An opt-in Zellij configuration that follows [the existing tmux setup](../rc/tmux.conf): `Ctrl-f` prefix, Vim-style splits and navigation, a single top tab bar, and the Nord purple/cyan palette. The terminal normally stays in locked mode so application shortcuts pass through.

![Zellij with the Nord top tab bar and split terminal panes](images/zellij-tmux.png)

Terminal capture of this configuration running on Zellij 0.45.1.

## Start a session

Use the **patched Zellij 0.45.1 runtime** installed by this checkout, Python 3, fzf, and Rust through rustup. `bootstrap.sh` and `make zellij-runtime` build a pinned, checksummed upstream source archive with the native fixes in [`zellij/patches`](../zellij/patches). The native build uses Rust 1.95.0 without changing your default toolchain; the top bar separately uses Rust 1.93.1 and `wasm32-wasip1`. Neovim is used to edit scrollback.

The first native build takes longer than installing an upstream binary and needs a C/C++ compiler, Make, CMake, pkg-config, and OpenSSL development files. `bootstrap.sh` installs those build dependencies. On macOS, install Xcode command line tools and run `brew install cmake pkg-config openssl@3 fzf`. Later installs reuse the Cargo cache and skip an unchanged executable after checking its hash against the installed patch set. The stock Homebrew or upstream 0.45.1 executable does not include these fixes.

From the dotfiles checkout:

```sh
make zellij-runtime zellij
zellij attach --create main
```

`make zellij-runtime` installs the patched executable. `make zellij` builds the bar and installs configuration and helpers without installing a runtime or starting a session. Default `make` also installs this configuration. To install an already-built bar, pass `ZELLIJ_STATUS_WASM=/absolute/path/lane-status.wasm`. In a new shell, `zj main` is the short form of the attach-or-create command. Configuration and individual layouts are symlinked, preserving additional user layout files.

Restart existing session servers to use the fixes: replacing the executable does not replace a running server. Keep `$HOME/.local/bin` before package-manager directories in `PATH`. Run `python3 scripts/install-zellij --check` to verify the installed executable matches this checkout. The runtime keeps the upstream `0.45.1` protocol version so existing plugins remain compatible; the installer records the patch-set and binary hashes separately.

On first launch, the bar asks for permission to read application state, run its local status helper, and switch tabs. Focus that permission prompt with **Ctrl-f k**, then press **y**. Zellij remembers the grant for this plugin. The bar becomes unselectable after permission is granted.

Use `Ctrl-f d` to detach and run the same attach command to return. Closing the terminal also detaches. Existing tmux configuration and shell startup are unchanged. [Firstmate can explicitly select Zellij](firstmate.md) through `FM_BACKEND=zellij` or its backend configuration; its default remains tmux.

## Familiar keys

Every key below follows **Ctrl-f**, unless stated otherwise. `Esc` cancels prefix mode. Most actions return immediately to locked mode.

| Key | Action |
| --- | --- |
| `f` | Send a literal Ctrl-f to the application |
| `Ctrl-f` | Fuzzy tab picker, with agent attention first and pane previews |
| `Ctrl-a` | Cross-session agent attention picker; select a record to focus its live pane |
| `Ctrl-w` | Fuzzy picker for running sessions, with a tab-tree preview |
| `h`, `j`, `k`, `l` / arrows | Focus the adjacent pane |
| `Tab`, `o` | Focus the next pane |
| `;` | Focus the previously focused pane |
| `s`, `"` | Split below, inheriting the working directory |
| `v`, `%` | Split right, inheriting the working directory |
| `c` | New tab |
| `Ctrl-n`, `n` | Next tab |
| `Ctrl-p` | Last-focused tab |
| `r`, `,` | Rename the tab; Enter accepts and Esc restores the name |
| `0`–`9` | Select the tab at that zero-based position |
| `d` | Detach, keeping the session running |
| `x` | Close the focused pane |
| `z` | Toggle pane zoom |
| `Z` | Toggle zoom without the surrounding UI |
| `J`, `K` | Move the pane down/up |
| `<`, `>`, `+`, `-` | Resize toward left/right/up/down |
| `Ctrl-r` | Enter repeatable resize mode |
| `Space`, `Ctrl-o` | Next/previous columns, rows, stacked, or equalize layout |
| `P` | Open the shared persistent popup; the same key inside it hides that view |
| `F` | Show/hide the current tab's other floating panes |
| `Ctrl-q` | Confirm shutdown of the current Zellij session |
| `u`, `i` | Return to a containing Zellij session / enter the focused nested session |
| `!` | Move the focused pane to a new tab |
| `m` | Enter pane movement mode |
| `W` | Enter tab reorder mode |
| `C`, `w` | Open the native session manager for creating, switching, renaming, and restoring sessions |
| `e` | Open the pane's scrollback in Neovim |
| `[` | Enter scroll mode |
| `/` | Search the pane's scrollback |

`Ctrl-f Ctrl-f` follows the effective tmux binding: the later fuzzy-picker binding in `tmux.conf` overrides its earlier send-prefix binding. `Ctrl-f f` remains the way to send Ctrl-f through. Similarly, `Tab` keeps pane cycling rather than the earlier, overridden `Ctrl-i` layout binding.

**Resize mode:** `h/j/k/l` or arrows grow toward that edge; uppercase `H/J/K/L` shrink. `+`/`=` grows and `-` shrinks. **Move mode:** `h/j/k/l` or arrows move the pane, `Tab` cycles positions, and `[`/`]` moves it to the adjacent tab. **Tab reorder mode:** `h/l` or arrows reorder the tab. Enter or Esc exits these modes.

**Scroll mode:** `j/k` scroll, Ctrl-f/Ctrl-b page, Ctrl-d/Ctrl-u half-page, and `g/G` jump to the start/end. `/` starts a search; `n/N` find next/previous matches. `e` opens Neovim for arbitrary Vim selection. `y` copies an existing selection and returns to the prompt. `m` selects a command at the scroll position, and `c` copies the last command output when the application supplies OSC 133 shell markers. Esc or `q` returns to the bottom.

Clipboard copying uses OSC 52, including over SSH. Use the terminal's paste shortcut; `Ctrl-f p` is deliberately unbound because Zellij does not share tmux's paste buffers. The config does not replace it with a different action.

## Smart editor and shell navigation

Bare **Ctrl-h/j/k/l** move among Neovim splits first, then cross into the adjacent Zellij pane at an editor boundary. They work in normal and insert modes. The same keys at the configured **Zsh prompt** move back into Neovim or another pane, preserving a partially typed command. Run `make zellij zsh-config vim-config` and restart the shell/editor to install both sides.

Navigation stays in the current tab and does not leave a zoomed pane. Internal Neovim split movement continues while zoomed; use `Ctrl-f z` to restore the outer layout before crossing a pane boundary. Outside Zellij, Zsh keeps its normal Ctrl-h/backspace binding and Neovim keeps Navigator's existing tmux/WezTerm detection. The shared `zellij-context provider` helper identifies the nearest live multiplexer from process ancestry: Zellij inside tmux navigates its own panes, and tmux inside Zellij retains tmux navigation despite inherited outer environment variables.

The helper verifies one attached client's current source pane and tab, then rechecks the same client/pane immediately before moving focus. It rejects ambiguous multiple-client ownership; use `Ctrl-f h/j/k/l` with multiple clients attached. This fixes delayed navigation acting on another tab. Stable Zellij's CLI does not offer an atomic conditional focus action, so a small window between the final check and the action remains; it is not a strict server-side compare-and-focus guarantee. Missing helpers or failed ownership inspection leave pane crossing disabled rather than selecting an outer multiplexer from stale variables.

These are editor and prompt bindings: other foreground applications receive their own Ctrl-h/j/k/l shortcuts. Use `Ctrl-f h/j/k/l` from those applications or from other shells. Zellij remains in locked mode; navigation itself needs no additional WASM plugin.

## Equalize layout

Use **Ctrl-f Space** or **Ctrl-f Ctrl-o** to cycle to the **equalize** layout. It places one full-height pane in the left half and divides the right half into equal rows for the remaining panes. An indivisible column or row goes to one pane, so dimensions can differ by one cell; the pane title and separator still consume their normal space. This is a native layout change: pane positions can change, while the original pane IDs, focused terminal, shell processes, and scrollback survive. Percentage sizing continues to fit when the outer terminal changes size.

Start a new session with the updated `tmux` layout after `make zellij`; existing sessions retain their loaded swap layouts. The preset uses the same one-row top bar as columns, rows, and stacked layouts. Prefix `=` remains unbound: stable Zellij has no direct selection of an arbitrary named swap layout, and a helper that cycles while searching could change a custom tab before discovering that its layout is unavailable. The native cycle makes each layout change explicit.

**Golden-ratio sizing and exact three-cell resizing remain unavailable.** The tmux policy skips an ordinary `g` when the left pane is already at least 120 columns; forced `G` uses `floor(window width × 0.382)`, capped at 180 columns, with no 120-column floor. Stable Zellij's native resize action uses percentage steps and exposes no cell-count or timed-repeat option. Layout overrides match original launch metadata, which can create extra shells for existing panes that do not match; fixed-cell layouts also fail to adapt reliably when the outer window becomes narrower. Those overrides are not installed as a substitute. Prefix `g/G` remain unbound, and Ctrl-f Ctrl-r remains an explicit mode that ends with Enter or Esc, rather than tmux's timed repeat window.

Upstream implementation references: [native resize step](https://github.com/zellij-org/zellij/blob/v0.45.1/zellij-server/src/panes/tiled_panes/tiled_pane_grid.rs), [layout reuse and overrides](https://github.com/zellij-org/zellij/blob/v0.45.1/zellij-server/src/tab/layout_applier.rs), and [CLI actions](https://github.com/zellij-org/zellij/blob/v0.45.1/zellij-utils/src/cli.rs).

## Shared popup and session shutdown

**Ctrl-f P** opens a floating view of the dedicated `dotfiles-popup` session. Press **Ctrl-f P** again inside the popup to detach that view. Reopening it from another tab or another Zellij session on the same host and socket namespace returns to the same live shell, including its working directory and unexported variables. Each opening attaches a client to that session; it does not move a working pane between sessions. The outer configuration automatically focuses nested sessions so the popup receives its own prefix keys.

The popup has one shell, no inner tab bar or status plugin, and a 10,000-line live history limit. Its prefix keys are deliberately small: `P` or `d` hides the view, `f` sends Ctrl-f, `u/i` changes nested-session focus, and Esc, Enter, or Ctrl-c cancels prefix mode. Other main-session controls, including prefix `p` clipboard pasting and the shutdown shortcut, are unavailable inside this scratch session; the terminal's paste shortcut remains available. The popup stays alive after its view closes or its outer session shuts down. Running `exit` in the scratch shell ends it; its in-memory state does not survive server exit or reboot, and this dedicated session does not create resurrection snapshots. Keep `dotfiles-popup` reserved for this workflow. The previous floating-layer toggle is available as **Ctrl-f F**.

Automatic nesting focus applies to other compatible Zellij sessions too, including sessions reached over SSH. With these dotfiles in the guest, **Ctrl-f u** returns to its containing session without detaching; **Ctrl-f i** in the host enters its focused nested session again. The top bar uses italic labels while keyboard focus belongs to another session, following Zellij's native host/guest state. A guest with another configuration uses its own `FocusHostSession` binding (upstream 0.45.1 defaults to Ctrl-o, then `]`). Detaching the guest also returns control to its host.

**Ctrl-f Ctrl-q** in the main configuration opens a confirmation naming the current session. Type `SHUTDOWN` to close its panes and disconnect its clients, or press Enter or Ctrl-c to cancel. The helper checks the owning server's Unix socket identity again before executing, rejecting a session that was renamed or replaced while confirmation was open. This ends one Zellij session and its server; other sessions, including a separately running popup, continue. **Ctrl-f d** still detaches the current client without shutting down its session.

**Selected-client detachment remains unsupported.** Prefix `D` is unbound. Stable 0.45.1 exposes a client list and current-client detach, but its CLI has no client-ID detach argument; the plugin API's disconnect-other-clients action affects every other client. Use `zellij action list-clients` to inspect the current session and detach from the intended client's terminal. A chooser must wait for a genuinely targeted API.

Implementation references: [native nesting options and focus behavior](https://github.com/zellij-org/zellij/blob/v0.45.1/zellij-integration-tests/tests/nested_session_handling_config.rs), [CLI session actions](https://github.com/zellij-org/zellij/blob/v0.45.1/zellij-utils/src/cli.rs), and [plugin client controls](https://github.com/zellij-org/zellij/blob/v0.45.1/zellij-tile/src/shim.rs).

## Agent status and attention

![Native Zellij status bar showing a working Codex fixture and an attention record in another session](images/zellij-status.png)

Cropped terminal capture from the installed workflow with controlled local hook producers.

The compact Nord bar shows the hostname, zero-based tabs, prefix mode, zoom, a clock, and battery percentage when the host exposes it. Per-tab states use `?` for a question, `!` for approval or a plan, `×` for failure, `✓` for a completed result, and `●` for work in progress. The right-hand `!` count includes agents needing attention or with a result ready across live local Zellij sessions; `●` counts working agents. Native bell notifications still mark tabs without a broker record. `Ctrl-f Ctrl-a` prioritizes human action, then completed results, then active work.

**Broker prerequisite:** this integration requires [the merged Zellij provider](https://github.com/lanej/agent-status-broker/commit/a3b9881df6bae8f3434bdb8943550b59a6e871d9). The installer is prepared to default to **v0.1.8**; v0.1.7 lacks this provider. **Release gate: pending.** Publication of v0.1.8, archive/checksum verification, and an actual default-installer run are still required. Source workflow validation does not establish that a released installation works. Until that gate is complete, use a source checkout containing the merged commit and install it explicitly:

```sh
AGENT_STATUS_SOURCE="$HOME/src/agent-status-broker" make agent-status-broker
"$HOME/.local/lib/agent-status/agent-status-broker" install
```

The first command builds the source and installs hooks without starting a service; the second starts the broker through its normal installer. `make zellij` alone remains usable and displays `broker?` with unknown counts when the broker is missing, stopped, or too old. With no broker records, the attention picker falls back to native bell notifications. It does not infer conversation state from captured screen text.

The plugin reports native pane IDs, shell roots, and titles through the permission-gated SDK. The broker binds those to live process generations and authenticated Claude hook ancestry or a unique native Codex conversation identity. A session-wide bar keeps that manifest current while detached or hidden. Cross-session selection rechecks the record and destination before focusing; exited or replaced owners disappear. Restarting the broker discards old activity while retaining and revalidating Claude ownership, so ordinary fresh hooks restore status without restarting the agent. This status integration does not provide exact Claude resurrection or Rex OSC 7501 transport.

Codex binding requires its native conversation title to remain visible to the API. A custom pane name can hide that identity; such a pane has no broker record until its native title is available again. Counts describe bound records, not a discovery count of every agent process on the host.

## History and recovery

- **Live history:** at most 100,000 scrollback lines per pane.
- **Recovery history:** at most 10,000 saved scrollback lines per pane, with the viewport and session layout saved every 60 seconds.
- **Recovery behavior:** reattaching to an exited session reconstructs its layout and offers to rerun its commands. The native manager also lists these sessions. The fuzzy picker lists running sessions only.

These are line limits, **not a byte budget or a guarantee against memory exhaustion**. Recovery snapshots do not page live scrollback out of RAM. Detaching preserves live processes; restoring after server exit or reboot relaunches commands and does not restore their process memory. A crash can lose changes since the last snapshot.

## Differences that remain

| tmux behavior | This configuration |
| --- | --- |
| Agent-status glyphs/colors, cross-session attention counts, `Ctrl-f Ctrl-a` triage | Implemented with the merged broker provider above; the planned v0.1.8 default still requires release verification. |
| Exact Claude conversation restoration via saved session IDs | Zellij's native command restoration is enabled; the custom `claude --resume` session-ID integration remains tmux-specific. |
| Rex OSC 7501 delivery through the patched tmux server | No replacement transport in this configuration. Upstream development features are not assumed to exist in stable 0.45.1. |
| Smart bare Ctrl-h/j/k/l across Neovim and tmux panes | Supported in Neovim normal/insert modes and at configured Zsh prompts. Other foreground applications retain their keys; use prefix navigation there. |
| Moving live windows/panes across sessions, including parking in `later` | Unsupported by Zellij. `H`, `S`, and `M` are not assigned a restart-based substitute. Native movement between tabs in the same session is available. |
| Vi visual/rectangle copy mode and shared paste buffers | Use Neovim scrollback editing, mouse selection, or supported whole-command selection; use terminal paste. |
| Zero-based windows | Tab labels, picker labels, and `0`–`9` keys are zero-based; Zellij's underlying CLI positions remain one-based. |
| Three-cell resizing and timed repeat bindings | Native Zellij resize steps; an explicit repeatable mode under prefix+Ctrl-r. |
| Golden-ratio helper (`g/G`) | Unbound; the width guard, exact ratio, and cap are not safely implemented with stable APIs. |
| Equalization (`=`) | The native equalize preset is available through layout cycling. Direct `=` selection and preserving each pane's position during equalization remain unsupported. |
| Dedicated shared `popup` session | `P` attaches to the live `dotfiles-popup` scratch session across tabs and sessions on the same host; `F` toggles other floating panes. |
| Custom clock, battery, host, and agent status segments | Built from the checked-in bar source; no third-party plugin download or bottom status bar. |
| Kill-server confirmation | `Ctrl-q` confirms shutdown of the current session's server. It does not shut down every Zellij session. |
| Client-detach chooser | `D` remains unbound because stable APIs cannot detach one selected client. Ordinary `d` detaches the current client. |

Reference: [Zellij 0.45.1](https://github.com/zellij-org/zellij/releases/tag/v0.45.1), [session resurrection](https://zellij.dev/documentation/session-resurrection.html), and [the upstream cross-session movement limitation](https://github.com/zellij-org/zellij/issues/5118).

## Check a change

```sh
zellij setup --check
make test-zellij
make test-zellij-navigation
make test-zellij-layout
make test-zellij-sessions
AGENT_STATUS_SOURCE=/path/to/zellij-enabled-broker make test-zellij-status
```

The workflow check installs into a temporary home, sends real prefix keys to Zellij in a pseudo-terminal, exercises the actual fzf pickers, and verifies that detach/reattach keeps the panes and a shell's in-memory state. The navigation check uses installed Zsh bindings, real Neovim, and the pinned Navigator plugin to exercise editor boundaries in both directions, insert mode, zoom, application key passthrough, both multiplexer nesting directions, and a tab change during a delayed navigation query. It requires Neovim 0.12+, Zsh, tmux, git, and access to the public plugin repository. Both checks require local Unix sockets and PTYs and terminate only their own named sessions. Linux and macOS CI run them against Zellij 0.45.1. They do not establish performance under production agent output or clipboard behavior in a particular terminal emulator.

The layout check cycles through the installed layout control with an explicit-command shell, observes equalize dimensions before and after a terminal resize, and checks stable pane IDs, focus, shell PIDs, unexported shell variables, and scrollback.

The session checks observe host/guest focus control and the same popup shell PID, cwd, and unexported state across hiding, another tab, and another outer session. They exercise shutdown cancellation, reject an old confirmation after renaming its session and recreating the original name, and verify that other sessions and the original popup shell survive a valid targeted shutdown. All servers use a private temporary socket directory.

The status workflow builds the real broker and plugin and drives the installed Claude/Codex hook entrypoints with local executable fixtures. It checks concurrent identities, Codex without inherited mux hints, cross-session counts and triage, process continuity, owner exit, broker restart, detached pane discovery, and background leadership after closing the original bar's tab. The fixtures do not call models or validate a production agent's current UI. The private broker portion runs only for trusted repository branches; public/fork runs still exercise the installed Zellij UI.
