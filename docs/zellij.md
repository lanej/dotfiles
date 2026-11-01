# Zellij with the tmux bindings

An opt-in Zellij configuration that follows [the existing tmux setup](../rc/tmux.conf): `Ctrl-f` prefix, Vim-style splits and navigation, a single top tab bar, and the Nord purple/cyan palette. The terminal normally stays in locked mode so application shortcuts pass through.

![Zellij with the Nord top tab bar and split terminal panes](images/zellij-tmux.png)

Terminal capture of this configuration running on Zellij 0.45.1.

## Start a session

Use **Zellij 0.45.1 or newer**, Python 3, and fzf. Neovim is used to edit scrollback. `bootstrap.sh` installs the required Zellij version through the existing minimum-version installer, retaining a newer installed version; its release fallback verifies the executable's upstream checksum. On macOS, `brew install zellij fzf` also installs the two terminal tools.

From the dotfiles checkout:

```sh
make zellij
zellij attach --create main
```

`make zellij` installs configuration and helpers; it does not install the binary or start a session. Default `make` also installs this configuration. In a new shell, `zj main` is the short form of the attach-or-create command. Configuration and individual layouts are symlinked, preserving additional user layout files.

Use `Ctrl-f d` to detach and run the same attach command to return. Closing the terminal also detaches. Existing tmux configuration and shell startup are unchanged. [Firstmate can explicitly select Zellij](firstmate.md) through `FM_BACKEND=zellij` or its backend configuration; its default remains tmux.

## Familiar keys

Every key below follows **Ctrl-f**, unless stated otherwise. `Esc` cancels prefix mode. Most actions return immediately to locked mode.

| Key | Action |
| --- | --- |
| `f` | Send a literal Ctrl-f to the application |
| `Ctrl-f` | Fuzzy tab picker, with native bell tabs first and pane previews |
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
| `1`–`9` | Select the tab at that one-based position; `0` also selects the first |
| `d` | Detach, keeping the session running |
| `x` | Close the focused pane |
| `z` | Toggle pane zoom |
| `Z` | Toggle zoom without the surrounding UI |
| `J`, `K` | Move the pane down/up |
| `<`, `>`, `+`, `-` | Resize toward left/right/up/down |
| `Ctrl-r` | Enter repeatable resize mode |
| `Space`, `Ctrl-o` | Next/previous columns, rows, or stacked layout |
| `P` | Show/hide floating panes; create a floating shell if needed |
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

These are editor and prompt bindings: other foreground applications receive their own Ctrl-h/j/k/l shortcuts. Use `Ctrl-f h/j/k/l` from those applications or from other shells. Zellij remains in locked mode and no additional WASM plugin is installed.

## History and recovery

- **Live history:** at most 100,000 scrollback lines per pane.
- **Recovery history:** at most 10,000 saved scrollback lines per pane, with the viewport and session layout saved every 60 seconds.
- **Recovery behavior:** reattaching to an exited session reconstructs its layout and offers to rerun its commands. The native manager also lists these sessions. The fuzzy picker lists running sessions only.

These are line limits, **not a byte budget or a guarantee against memory exhaustion**. Recovery snapshots do not page live scrollback out of RAM. Detaching preserves live processes; restoring after server exit or reboot relaunches commands and does not restore their process memory. A crash can lose changes since the last snapshot.

## Differences that remain

| tmux behavior | This configuration |
| --- | --- |
| Agent-status glyphs/colors, cross-session attention counts, `Ctrl-f Ctrl-a` triage | The existing broker's tmux renderer is not ported. The picker can prioritize native bells but cannot infer agent state from terminal output. |
| Exact Claude conversation restoration via saved session IDs | Zellij's native command restoration is enabled; the custom `claude --resume` session-ID integration remains tmux-specific. |
| Rex OSC 7501 delivery through the patched tmux server | No replacement transport in this configuration. Upstream development features are not assumed to exist in stable 0.45.1. |
| Smart bare Ctrl-h/j/k/l across Neovim and tmux panes | Supported in Neovim normal/insert modes and at configured Zsh prompts. Other foreground applications retain their keys; use prefix navigation there. |
| Moving live windows/panes across sessions, including parking in `later` | Unsupported by Zellij. `H`, `S`, and `M` are not assigned a restart-based substitute. Native movement between tabs in the same session is available. |
| Vi visual/rectangle copy mode and shared paste buffers | Use Neovim scrollback editing, mouse selection, or supported whole-command selection; use terminal paste. |
| Zero-based windows | Number keys use Zellij's one-based tab positions. |
| Three-cell resizing and timed repeat bindings | Native Zellij resize steps; an explicit repeatable mode under prefix+Ctrl-r. |
| Golden-ratio helper (`g/G`), equalization (`=`) | Unbound; swap layouts offer explicit alternatives without claiming the same width guards or semantics. |
| Dedicated shared `popup` session | `P` toggles the current tab's floating layer. |
| Custom clock, battery, host, and agent status segments | One bundled top tab bar, with no bottom status bar or additional plugin download. |
| Kill-server confirmation and client-detach chooser | No destructive replacement shortcut; use the native session manager or explicit CLI commands. |

Reference: [Zellij 0.45.1](https://github.com/zellij-org/zellij/releases/tag/v0.45.1), [session resurrection](https://zellij.dev/documentation/session-resurrection.html), and [the upstream cross-session movement limitation](https://github.com/zellij-org/zellij/issues/5118).

## Check a change

```sh
zellij setup --check
make test-zellij
make test-zellij-navigation
```

The workflow check installs into a temporary home, sends real prefix keys to Zellij in a pseudo-terminal, exercises the actual fzf pickers, and verifies that detach/reattach keeps the panes and a shell's in-memory state. The navigation check uses installed Zsh bindings, real Neovim, and the pinned Navigator plugin to exercise editor boundaries in both directions, insert mode, zoom, application key passthrough, both multiplexer nesting directions, and a tab change during a delayed navigation query. It requires Neovim 0.12+, Zsh, tmux, git, and access to the public plugin repository. Both checks require local Unix sockets and PTYs and terminate only their own named sessions. Linux and macOS CI run them against Zellij 0.45.1. They do not establish performance under production agent output or clipboard behavior in a particular terminal emulator.
