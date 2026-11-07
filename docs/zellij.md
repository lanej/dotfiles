# Zellij

My Zellij setup uses **Ctrl-f** as the prefix, Vim-style navigation, and one top tab bar. Start with the [keybinding map](zellij-keybinds.mdx), or choose a feature below.

## Start a session

Use the **pinned [lanej/zellij fork](https://github.com/lanej/zellij)** installed by this checkout, Python 3 for the configuration helpers, fzf, and Rust through rustup. The selected Zellij recipe defaults to the exact fork revision in [`scripts/install-zellij`](../scripts/install-zellij). The fork builds on upstream `main` at `bf517077`, which includes [OSC 7501 support](https://github.com/zellij-org/zellij/pull/5734) and the startup repair; it carries the CLI completion, shutdown flush, initial-client registration, concurrent permission-cache fixes, popup-paste routing, and lossless Unicode plugin keys with their native regressions. Select the runtime explicitly through [configuration sets](../README.md#configuration-sets): `tools.zellij = true` enables the recipe; `zellij.source = "patched"` installs the fork, `"release"` installs upstream stable, and `"main"` builds pinned upstream main without the fork's fixes. The `terminal` and `workstation` bundles enable Zellij. The main and release choices omit the fork's fixes; the documented popup, query, and shutdown acceptance applies to the patched runtime. The native builds use Rust 1.95.0 without changing your default toolchain. Neovim is used to edit scrollback. Return the default pin to a stable release once it includes OSC support and these reliability fixes; the status bar uses its native attention protocol.

After upgrading the runtime, save your work and restart existing sessions so every session uses the permission-cache lock; an older session process can still perform unlocked writes. Malformed permission caches are preserved for correction rather than silently overwritten.

The first native build takes longer than installing an upstream binary and needs a C/C++ compiler, Make, CMake, pkg-config, and OpenSSL development files. `make install` installs those build dependencies when Zellij is selected. On macOS, install Xcode command line tools and run `brew install cmake pkg-config openssl@3 fzf`. Cargo uses the fork's lockfile and caches compilation artifacts under `${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/zellij/target/<revision>`. The first installation from each revision's isolated cache replaces the executable, including an already-owned binary built with stale shared artifacts. Later installations of the same verified revision reuse the cache and Cargo's installation check. Cargo manages installation ownership and locking. The stock Homebrew or upstream 0.45.1 executable does not include these fixes.

The fork also preserves the initial terminal client's registration when a temporary CLI connection closes before the first layout. A client that really disconnects remains absent when that late layout finishes. Existing session servers need a restart to use this repair.

From the dotfiles checkout:

```sh
zj
zj work
```

`zj` attaches to or creates `main`; `zj work` chooses a session named `work`. **Ctrl-f d** detaches and keeps programs running. Run the same command to return.

If a first-use permission prompt appears in the top bar, focus it with **Ctrl-f k** and press **y**. After updating Zellij or its configuration, start a new session to use the new features; finish or save work before restarting older sessions.

## Familiar keys

Press **Ctrl-f**, release it, then press the next key. Uppercase letters need Shift. **Esc**, **Enter**, or **Ctrl-c** cancels the prefix. Most shortcuts immediately return control to the application.

The [keybinding map](zellij-keybinds.mdx) lists shortcuts, aliases, and keys inside modes. **Ctrl-f p** pastes copied session text; **Ctrl-f Ctrl-p** switches tabs.

<span id="smart-pane-navigation"></span>

## Navigation

| Feature | Use it to… |
| --- | --- |
| `f` | Send a literal Ctrl-f to the application |
| `Ctrl-f` | Fuzzy tab picker, with native attention first and pane previews |
| `Ctrl-a` | Next local tab needing you, otherwise activity/bell, in tab order |
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
| `D` | Choose one attached client to detach; Enter confirms and Esc cancels |
| `x` | Close the focused pane |
| `z` | Toggle pane zoom |
| `Z` | Toggle zoom without the surrounding UI |
| `J`, `K` | Move the pane down/up |
| `<`, `>`, `+`, `-` | Resize toward left/right/up/down |
| `Ctrl-r` | Enter repeatable resize mode |
| `=` | Balance the invoking pane’s aligned row or column group |
| `g`, `G` | Golden-ratio left-pane width; `G` forces resizing past the width guard |
| `Space`, `Ctrl-o` | Next/previous columns, rows, stacked, or equalize layout |
| `P` | Open the shared persistent popup; the same key inside it hides that view |
| `:` | Open the command palette with completion, live target tables, help and history |
| `F` | Show/hide the current tab's other floating panes |
| `Ctrl-q` | Confirm shutdown of the current Zellij session |
| `u`, `i` | Return to a containing Zellij session / enter the focused nested session |
| `!` | Move the focused pane to a new tab |
| `m` | Fuzzy pane destination picker: New Tab or an existing tab in this session |
| `W` | Fuzzy swap of the current and selected tab positions |
| `C` | Immediately create a new, automatically named session in the focused pane’s directory |
| `w` | Rename this session directly; Enter saves, Esc or Ctrl-c cancels |
| `e` | Open the pane's scrollback in Neovim |
| `p` | Paste this session's last Neovim yank into the requesting pane |
| `[` | Enter scroll mode |
| `/` | Search the pane's scrollback |

`Ctrl-f Ctrl-f` follows the effective tmux binding: the later fuzzy-picker binding in `tmux.conf` overrides its earlier send-prefix binding. `Ctrl-f f` remains the way to send Ctrl-f through. Similarly, `Tab` keeps pane cycling rather than the earlier, overridden `Ctrl-i` layout binding.

With the compiled bar, the first tab and its fallback name are `0:Tab #0`; `Ctrl-f 0` selects it. Positions continue through `10`, `11`, and beyond. Use the fuzzy picker or next/last-tab controls beyond the ten digit shortcuts. Reordering or closing tabs updates displayed positions; picker selection uses stable tab IDs. Zellij's native `GoToTab` action and CLI arguments remain one-based.

Zsh updates the native tab name and its own terminal title to `directory [git-branch]` after changing directory and before each prompt. The compiled bar and picker present the focused tiled pane's shell/application title for generated or automatically managed tabs, with a zero-based fallback when there is no title or attached clients disagree about focus. Explicit tab names, including `zssh` host names, win; explicit pane names override shell/application titles. Nested tmux/Zellij uses the nearest multiplexer. Run `make zellij zsh-config`, rebuild the bar with `make zellij-status zellij`, and start a new shell/session to load these changes.

Automatic ownership requires an exact match with the last name written by the hook and a matching live session socket incarnation. State under `$XDG_STATE_HOME/zellij-auto-titles` cannot claim a recreated session's explicit title. Older records without lifecycle identity are ignored; reset the native tab name to its generated `Tab #<stable ID + 1>` name to resume automatic naming after upgrading an existing session. Zellij does not expose rename provenance: manually choosing exactly the last automatic name remains indistinguishable from automatic ownership. Other explicit names remain literal. If ownership cannot be established, the native name is displayed unchanged.

The configuration-only/0.45.1 fallback still uses Zellij's built-in bar and one-based keys (`0` also selects the first tab). That bar has no base-index option; this change does not replace it or alter the runtime. To use the zero-based bar, install the pinned 0.46 runtime and build the status plugin. Avoid manual names matching Zellij's generated forms (`Tab #<stable ID + 1>` and `Pane #<number>`): its metadata does not expose their origin, so the custom UI can treat them as fallbacks. Other manual names are retained verbatim.

**Command palette:** On the pinned runtime, `Ctrl-f :` accepts Zellij action syntax such as `rename-tab "work"`, in a slim floating command line with up to five completion suggestions. The popup shrinks with its matches; history and live target lists expand when opened. Tab completes the selected action, flag or live target; Enter runs the entered command; Esc closes it. Ctrl-p/Ctrl-n recall this client's history and restore its draft. `help` and `history` open searchable lists. `list-panes`, `list-tabs`, and `list-sessions` open live tables; Enter jumps to the selected target. Parse errors remain editable. The native popup preserves hidden floating panes and dispatches actions for the invoking client. Rebuild with `make zellij-command-prompt`, apply `make zellij`, and restart. See the [command-palette guide](../zellij/command-prompt/README.md) for syntax, permissions and limits.

`Ctrl-f =`, `g`, and `G` use Bash and jq with the pinned runtime’s background commands. They resize existing panes without changing focus or recreating shells. Equalize balances one contiguous aligned row or column containing the invoking pane; ambiguous grids, stacks, zoom, floating panes, and embedded plugin panes are rejected. The golden controls require one full-height leftmost pane: `g` skips when its content width is already at least 120 columns; otherwise the target is floor(tab width × 0.382), capped at 180 content columns. `G` ignores the 120-column guard.

Native resizing moves boundaries in roughly 5% increments, so these controls choose a reachable approximation, not tmux’s cell-exact dimensions. For example, three panes in a 120-column terminal with widths 60/30/30 balance to 42/36/42. Only native Decrease actions are used: expanding a pane shrinks its neighbor at the shared edge, avoiding native Increase’s direction-inversion fallback. A blocked edge leaves geometry unchanged. A worse overshoot is reversed only after checking the expected geometry; the 180-column cap takes priority over distance. Helpers target captured pane IDs, serialize per session/tab, and stop on unexpected geometry, native failures, 32 resize calls, or a 20-second overall budget. Manual layout changes are not atomic with helper queries. A crashed helper can leave a lock under `${XDG_CACHE_HOME:-~/.cache}/zellij/balance`; a notice identifies it. Remove that empty lock directory only after confirming no balancing helper is running. The older configuration retains its existing keys because it lacks the required background action. jq is installed with the Zellij tool through normal `make install`; the helper never installs dependencies itself.

**Resize mode:** `h/j/k/l` or arrows grow toward that edge; uppercase `H/J/K/L` shrink. `+`/`=` grows and `-` shrinks. Enter or Esc exits resize mode. The native Tab mode can still be entered explicitly with `zellij action switch-mode tab`; `W` opens the fuzzy swap picker instead.

**Tab swap:** `Ctrl-f W` selects an existing tab with the usual fuzzy menu and pane previews. It exchanges that tab’s position with the original tab, matching tmux’s `swap-window`; intervening tabs finish in their original positions. Esc or selecting the current tab leaves the order unchanged. The original pane and processes survive, and every attached client stays on its original tab ID, including viewers of the destination. The helper needs the compiled status plugin and pinned runtime; legacy reports this requirement rather than entering reorder mode.

The swap uses adjacent native moves, so other clients can see intermediate positions. It is not atomic: concurrent tab changes can race between validation and a move. The helper initially requires one identifiable requester, then pins read-only checks to that captured client and status-plugin instance. Before and after each move it verifies the full tab order, the captured attachment identity and its focus on the picker, and the original pane’s tab. Later checks validate that requester only; they do not require a complete all-client snapshot or reject another viewer joining the picker. Other viewers cannot redirect the stable-ID moves. A changed order, lost attachment, failed command, uncertain reply, or Ctrl-c during movement stops the operation with an inspection warning while the picker remains open. Enter dismisses the warning; Ctrl-c can also close it. Closing the picker during movement can terminate the helper without a warning and leave tabs partially reordered. Ordinary panes and their live processes remain intact. There is no automatic retry, rollback, or final focus action. Inspect tab positions after any interruption before trying again. No extra plugin permission is required.

`Ctrl-f m` follows the tmux pane-movement menu. It moves the original live pane, preserving its process and scrollback. Esc cancels; choosing the current tab does nothing. This menu needs the compiled status plugin and pinned runtime; rerun `make zellij-status zellij` and restart old sessions after upgrading. Existing-tab moves reserve a temporary inert split and replace it with the original pane, without running the default shell’s startup hooks or requiring additional plugin permissions. Cross-session movement remains unsupported. `Ctrl-f !` remains an optional direct shortcut, not a replacement for the menu.

`Ctrl-f M` moves all live tiled and floating terminals from the current tab to a selected existing tab in the modern configuration. There is no New Tab option; cancel and current-tab selection leave the layout unchanged. Plugins, exited commands, and the chooser are not transferred. A source with suppressed terminals is rejected, including hidden members of native stacks as well as scrollback-editor backing terminals. Expose or restore those source panes, or close the scrollback editor, before gathering. Native stacking in the destination is supported; this restriction applies to hidden panes in the source.

After confirmation, the chooser temporarily becomes tiled to keep the source tab alive while native pane replacements run. It exits after receiving the result. The invoking client follows its original pane; unrelated clients stay on their own tabs. If the source tab disappears, clients viewing it follow Zellij's native tab-close behavior. Floating terminals become tiled at the destination. Movement is sequential, not atomic: if a pane/tab changes or a reply is lost, inspect both tabs before retrying. If the CLI reply times out, the chooser stays open and defers Ctrl-c while it waits for the plugin to acknowledge that the operation has stopped. A deadline prevents queued requests from starting late or continuing with more transfers indefinitely. If the server becomes unreachable, keep the chooser open until it can confirm the stop. After acknowledgement an error remains visible until Enter; completed moves are not replayed or rolled back.

**Scroll mode:** `j/k` scroll, Ctrl-f/Ctrl-b page, Ctrl-d/Ctrl-u half-page, and `g/G` jump to the start/end. `/` starts a search; `n/N` find next/previous matches. `e` opens Neovim for arbitrary Vim selection. `y` copies an existing selection and returns to the prompt. `m` selects a command at the scroll position, and `c` copies the last command output when the application supplies OSC 133 shell markers. Esc or `q` returns to the bottom.

<span id="equalize-layout"></span>

## Pane arrangement

| Feature | Use it to… |
| --- | --- |
| [Move a pane](zellij/move-pane.mdx) | Move one running pane into a new or existing tab |
| [Gather panes](zellij/gather-panes.mdx) | Bring a tab's live panes into another tab |
| [Equalize panes](zellij/equalize.mdx) | Balance a row or column, or choose a layout |
| [Golden-ratio sizing](zellij/golden-ratio.mdx) | Size a full-height left pane for comfortable work |

## Shared popup and session shutdown

| Feature | Use it to… |
| --- | --- |
| [Shared popup](zellij/shared-popup.mdx) | Keep a scratch shell across tabs and sessions |
| [Command prompt](zellij/command-prompt.mdx) | Run a Zellij action without a shell command |
| [Create and rename sessions](zellij/sessions.mdx) | Open or name a workspace |
| [Detach one client](zellij/detach-client.mdx) | Disconnect a selected view while leaving programs running |
| [Shut down a session](zellij/shutdown.mdx) | Deliberately end one session with confirmation |

## Forwarded SSH agents

Use [SSH and forwarded agents](zellij/ssh-agent.mdx) to open remote workspaces and reconnect without losing authentication in existing panes. The same page covers the shared popup and 1Password agents.

<span id="keyboard-selection-and-paste"></span>
<span id="native-agent-status-and-attention"></span>
<span id="inbox-notices-and-history"></span>

## Text and attention

| Feature | Use it to… |
| --- | --- |
| [Copy and paste](zellij/copy-paste.mdx) | Select scrollback text and choose the right paste source |
| [Attention and triage](zellij/attention.mdx) | Visit requests, watch output, and mute panes |
| [Notifications and history](zellij/notifications.mdx) | Review events with a preview of their source panes |

## History and recovery

Detaching preserves running programs. After a session exits, the session manager may offer to reconstruct its layout and rerun commands; that does not restore program memory. The fuzzy session picker lists running sessions only.

Scrollback keeps up to 100,000 live lines per pane and up to 10,000 lines for recovery. A crash can lose recent output. The shared popup does not restore its running work after a server exit or reboot.

## Differences that remain

Older installations may use the legacy configuration: tab numbering starts at 1, several custom shortcuts are unavailable, and copying differs. See [legacy differences](zellij-keybinds.mdx#legacy-configuration) when your keys do not match.

Moving a live pane to another session, exact cell sizing, and tmux's timed repeat window are not supported. The relevant feature pages explain the alternatives.
