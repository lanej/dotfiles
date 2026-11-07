# Zellij with the tmux bindings

An opt-in Zellij configuration that follows [the existing tmux setup](../rc/tmux.conf): `Ctrl-f` prefix, Vim-style splits and navigation, a single top tab bar, and the Nord purple/cyan palette. The terminal normally stays in locked mode, with bare Ctrl-h/j/k/l reserved for smart pane navigation.

![Zellij with the Nord top tab bar and split terminal panes](images/zellij-tmux.png)

Terminal capture of this configuration running on Zellij 0.45.1.

## Start a session

Use the **pinned [lanej/zellij fork](https://github.com/lanej/zellij)** installed by this checkout, Python 3 for the configuration helpers, fzf, and Rust through rustup. The selected Zellij recipe defaults to the exact fork revision in [`scripts/install-zellij`](../scripts/install-zellij). The fork builds on upstream `main` at `bf517077`, which includes [OSC 7501 support](https://github.com/zellij-org/zellij/pull/5734) and the startup repair; it carries the CLI completion, shutdown flush, initial-client registration, and concurrent permission-cache fixes with their native regressions. Select the runtime explicitly through [configuration sets](../README.md#configuration-sets): `tools.zellij = true` enables the recipe; `zellij.source = "patched"` installs the fork, `"release"` installs upstream stable, and `"main"` builds pinned upstream main without the fork's fixes. The `terminal` and `workstation` bundles enable Zellij. The main and release choices omit the fork's fixes; the documented popup, query, and shutdown acceptance applies to the patched runtime. The native builds use Rust 1.95.0 without changing your default toolchain. Neovim is used to edit scrollback. Return the default pin to a stable release once it includes OSC support and these reliability fixes; the status bar uses its native attention protocol.

After upgrading the runtime, save your work and restart existing sessions so every session uses the permission-cache lock; an older session process can still perform unlocked writes. Malformed permission caches are preserved for correction rather than silently overwritten.

The first native build takes longer than installing an upstream binary and needs a C/C++ compiler, Make, CMake, pkg-config, and OpenSSL development files. `make install` installs those build dependencies when Zellij is selected. On macOS, install Xcode command line tools and run `brew install cmake pkg-config openssl@3 fzf`. Cargo uses the fork's lockfile and caches compilation artifacts under `${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/zellij/target/<revision>`. The first installation from each revision's isolated cache replaces the executable, including an already-owned binary built with stale shared artifacts. Later installations of the same verified revision reuse the cache and Cargo's installation check. Cargo manages installation ownership and locking. The stock Homebrew or upstream 0.45.1 executable does not include these fixes.

The fork also preserves the initial terminal client's registration when a temporary CLI connection closes before the first layout. A client that really disconnects remains absent when that late layout finishes. Existing session servers need a restart to use this repair.

From the dotfiles checkout:

```sh
make zellij-runtime zellij
zellij attach --create main
```

`make config` shows the selected source before installation. `make zellij-runtime` installs that runtime, replacing the managed executable even when switching from a newer development version back to stable. `make zellij` installs configuration and helpers without installing software or starting a session. Without a built bar, or with an older runtime, it selects the built-in tab bar and compatible keys. `make install` builds the native-attention bar for the patched/main runtime and reapplies configuration; `make zellij-status zellij` explicitly does the same on an existing installation. The bar uses Rust 1.95.0 and `wasm32-wasip1`; pass `ZELLIJ_STATUS_WASM=/absolute/path/lane-status.wasm` to use an already-built bar. `make configure` also applies this configuration when Zellij is selected. Setup records Zellij's native "never show again" choice for its configuration wizard, preserving other desktop settings, so the wizard does not block the managed keybindings on first launch. In a new shell, `zj` attaches to or creates `main`, matching the remote default of `zssh HOST`. Use `zj work` to choose another session. Existing sessions with other names remain available; `zj` no longer selects the newest one automatically. Configuration and individual layouts are symlinked, preserving additional user layout files.

Kitty tabs show only the session name while local Zellij runs in the foreground, so `main` stays `main` when pane titles or focus change. Apply the Kitty configuration with `make kitty-config` and reload it with `Cmd+Shift+R`.

Restart existing session servers to use the fixes: replacing the executable does not replace a running server. Keep `$HOME/.local/bin` before package-manager directories in `PATH`. The fork reports the pinned upstream version, `0.46.0`, and includes its matching bundled plugins.

Run `zssh myhost` inside your local Zellij to open a tab named `myhost` and attach to or create the remote `main` session. Use `zssh myhost work` to choose another remote session. Each host needs Zellij installed and discoverable in its interactive login shell. `zssh` runs the remote account's Bash or Zsh with `-lic`, loading its usual `PATH` rather than assuming an installation directory. This also runs interactive startup integrations before attaching. The command uses Kitty's SSH kitten when available, otherwise ordinary SSH; outside Zellij it connects in the current terminal. Remote sessions remain available after disconnecting. With this configuration on both hosts, `Ctrl-f u` returns control to the local Zellij and `Ctrl-f i` enters the remote one.

After updating the local checkout, start a new shell or run `source ~/.files/sh/functions` to refresh `zssh` in an existing one.

`Ctrl-f e` opens scrollback in Neovim with the terminal's original colors, including syntax colors emitted by commands. Neovim's Baleia plugin renders the ANSI colors and removes escape codes from the displayed text. Install the pinned plugin with `:Lazy restore` and restart Zellij to load the updated binding. The legacy configuration exports plain text, which receives shell syntax highlighting instead.

On first launch, the bar asks for permission to read application state, run its local helpers, switch tabs or detach a client, write to pane input, configure each client's runtime paste binding, exchange messages with its clipboard receiver, and receive CLI messages from the client chooser. Focus that permission prompt with **Ctrl-f k**, then press **y**. Zellij remembers the grant for this plugin. The bar becomes unselectable after permission is granted. An existing installation may ask again when these permissions expand.

Use `Ctrl-f d` to detach and run the same attach command to return. Closing the terminal also detaches. Existing tmux configuration and shell startup are unchanged. [Firstmate can explicitly select Zellij](firstmate.md) through `FM_BACKEND=zellij` or its backend configuration; its default remains tmux.

## Forwarded SSH agents

Use `zj SESSION` or `zssh HOST SESSION` when connecting with agent forwarding. The attach helper refreshes an owner-only, session-specific link under `~/.ssh/dotfiles-agent/`, including noninteractive remote commands. Links use the pinned runtime's persistent session IDs, so renaming a session or reusing its old name does not redirect existing panes. A new session initializes its link in the first shell after the runtime registers its ID. Existing panes keep that stable path across reconnects. A plain `zj` attaches to or creates `main`, matching the existing launcher default. Recovery uses a short, unfocused native command inside the target session to identify its owning server. It requires only the pinned runtime and standard shell utilities, with no Python or SQLite client at runtime. If recovery fails or times out, ordinary attachment still proceeds with the incoming socket. Forwarding must already be enabled for the trusted host with `ssh -A` or a host-specific `ForwardAgent yes`.

Each Zellij session has its own selection. Reconnecting to `work` does not change the agent used by `personal` or by tmux. Multiple clients sharing the same Zellij session share its last completed forwarded-agent update; if that connection closes, reconnect with forwarding to that session to refresh it. A fresh login without forwarding does not adopt an unrelated session's agent. No private keys are copied or local agents started remotely. Direct `zellij attach` bypasses the helper; use `zj SESSION` for forwarded reconnects.

The shared popup follows the containing session's managed agent link, not the raw socket captured when its server first started. Opening it selects that containing session as its source; later reconnects to that session refresh the popup's existing shells too, even while the popup is hidden. Opening the same shared popup from another outer session switches the popup's source without changing either outer session's selection. As with sharing a regular session, all clients of the popup share that selection. Only owned, direct managed links in the private agent directory are accepted; arbitrary symlinks, follower chains, self-reference and loops are rejected. Ordinary session refresh still accepts only raw agent sockets.

This agent repair does not require restarting a live popup. After installing the updated helpers, reconnect the outer session through `zj`/`zssh` and reopen the popup once. Shells already using their popup-specific stable path recover automatically. In older popup shells that still hold a raw socket or the outer session's path, run `source ~/.local/bin/fix-ssh` once to select the popup's stable path. Already-running applications with an old exported path need their own environment refreshed or to be restarted after their work is saved. This is independent of the new-layout migration below.

Tmux retains its existing `tmux show-environment` recovery, which selects the agent from that tmux session. Run `fixssh` in an older pane to refresh its socket and list the available keys. The `git-ssh` helper performs the same recovery when an inherited socket disappears, without requiring `SSH_TTY`. After installing with `make shell`, reconnect through the attach helper and run `fixssh` once in panes created before this change.

Run `make test-ssh-agent` for local-agent, tmux, and attachment-failure checks, and `python3 scripts/test-zellij-agent-update.py` for reconnects through the pinned native runtime, including a surviving popup shell, host switching and rejected unsafe agent sources. These checks use real temporary agents but do not open a real SSH connection or authenticate against 1Password.

### 1Password compatibility

The link forwards the existing SSH agent protocol, so it also works with the [1Password SSH agent](https://developer.1password.com/docs/ssh/agent/forwarding/). Local shell startup keeps its existing agent selection, and the remote host does not need 1Password or a copy of the private key. Enable forwarding only for trusted hosts (`ssh -A host` or a host-specific `ForwardAgent yes`). Approvals remain on the originating computer; other processes running as your remote OS user can use an already-authorized key while forwarding is active.

If the remote workstation also runs 1Password, its `IdentityAgent` setting overrides `SSH_AUTH_SOCK`. Replace an unconditional 1Password `IdentityAgent` rule in that workstation's `~/.ssh/config` with a local-only rule (use `~/.1password/agent.sock` on Linux):

```sshconfig
Match host * exec "test -z \"$SSH_CONNECTION\""
    IdentityAgent "~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
Match all
```

Use `SSH_CONNECTION`, not `SSH_TTY`, so remote commands without a terminal still use forwarding. Remove any other unconditional `IdentityAgent` rule for these hosts. The dotfiles do not manage or overwrite `~/.ssh/config`. Check `ssh -G github.com` in the remote shell for an unexpected `identityagent` override, then use `fixssh` and `ssh -T git@github.com` to check the actual forwarded agent. Git commit signing is separate: 1Password's `op-ssh-sign` currently requires both `SSH_AUTH_SOCK` and `SSH_TTY` to choose forwarding; non-TTY signing should use OpenSSH's `ssh-keygen` with the public signing key instead.

## Familiar keys

Use the [Zellij keybindings reference](zellij-keybinds.mdx) for everyday shortcuts, the complete prefix and mode tables, popup controls, and modern/legacy differences. Press **Ctrl-f**, release it, then press the command key. Most commands return to Locked mode; Esc, Enter, or Ctrl-c cancels the prefix.

In the modern configuration, **Ctrl-f C** switches only the requesting client to a fresh session using the installed regular `tmux` layout. Existing sessions and their processes keep running, including when invoked from the popup. **Ctrl-f w** shows the editable private name draft in the top bar; invalid or already-used names leave the session unchanged. The legacy configuration retains the session manager for both keys.

With the compiled status bar, pressing **Ctrl-f** turns the entire top row pink (#B48EAD), matching the selected pane border, with bold dark **PREFIX  waiting for next key** text and an **Esc cancels** hint. The normal tabs return as soon as you run or cancel the command. Resize, move, tab, rename, and scroll/search modes keep their own labels rather than claiming another prefix key is pending. The cue requires the bar to be visible; UI-free zoom does not show it.

Actual isolated PTY captures: [before](images/zellij-prefix/before.png), [waiting for the next key](images/zellij-prefix/waiting.png), and [after returning to Locked mode](images/zellij-prefix/after.png). These captures render the test session’s decoded terminal cells, not a live user session.

| Key | Action |
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
| `:` | Open a centered Zellij command prompt; `help` lists actions and `history` recalls this client's commands |
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

**Command prompt:** On the pinned runtime, `Ctrl-f :` accepts Zellij action syntax
without `zellij action`, such as `rename-tab "work"`, `new-pane --direction right`,
or `move-focus left`. Enter runs it and Esc cancels. `help` opens the action picker;
`history` recalls the client's in-memory command history for review. This is a
Zellij command line, not a shell or tmux command interpreter. It uses the native
popup layer, leaves hidden floating panes hidden, and targets the invoking client.
For an existing pinned installation, run `make zellij-command-prompt`, apply
`make zellij`, and restart. See the [command-prompt guide](../zellij/command-prompt/README.md)
for supported scope, quoting, permissions and verification.

`Ctrl-f =`, `g`, and `G` use Bash and jq with the pinned runtime’s background commands. They resize existing panes without changing focus or recreating shells. Equalize balances one contiguous aligned row or column containing the invoking pane; ambiguous grids, stacks, zoom, floating panes, and embedded plugin panes are rejected. The golden controls require one full-height leftmost pane: `g` skips when its content width is already at least 120 columns; otherwise the target is floor(tab width × 0.382), capped at 180 content columns. `G` ignores the 120-column guard.

Native resizing moves boundaries in roughly 5% increments, so these controls choose a reachable approximation, not tmux’s cell-exact dimensions. For example, three panes in a 120-column terminal with widths 60/30/30 balance to 42/36/42. Only native Decrease actions are used: expanding a pane shrinks its neighbor at the shared edge, avoiding native Increase’s direction-inversion fallback. A blocked edge leaves geometry unchanged. A worse overshoot is reversed only after checking the expected geometry; the 180-column cap takes priority over distance. Helpers target captured pane IDs, serialize per session/tab, and stop on unexpected geometry, native failures, 32 resize calls, or a 20-second overall budget. Manual layout changes are not atomic with helper queries. A crashed helper can leave a lock under `${XDG_CACHE_HOME:-~/.cache}/zellij/balance`; a notice identifies it. Remove that empty lock directory only after confirming no balancing helper is running. The older configuration retains its existing keys because it lacks the required background action. jq is installed with the Zellij tool through normal `make install`; the helper never installs dependencies itself.

**Resize mode:** `h/j/k/l` or arrows grow toward that edge; uppercase `H/J/K/L` shrink. `+`/`=` grows and `-` shrinks. Enter or Esc exits resize mode. The native Tab mode can still be entered explicitly with `zellij action switch-mode tab`; `W` opens the fuzzy swap picker instead.

**Tab swap:** `Ctrl-f W` selects an existing tab with the usual fuzzy menu and pane previews. It exchanges that tab’s position with the original tab, matching tmux’s `swap-window`; intervening tabs finish in their original positions. Esc or selecting the current tab leaves the order unchanged. The original pane and processes survive, and every attached client stays on its original tab ID, including viewers of the destination. The helper needs the compiled status plugin and pinned runtime; legacy reports this requirement rather than entering reorder mode.

The swap uses adjacent native moves, so other clients can see intermediate positions. It is not atomic: concurrent tab changes can race between validation and a move. The helper initially requires one identifiable requester, then pins read-only checks to that captured client and status-plugin instance. Before and after each move it verifies the full tab order, the captured attachment identity and its focus on the picker, and the original pane’s tab. Later checks validate that requester only; they do not require a complete all-client snapshot or reject another viewer joining the picker. Other viewers cannot redirect the stable-ID moves. A changed order, lost attachment, failed command, uncertain reply, or Ctrl-c during movement stops the operation with an inspection warning while the picker remains open. Enter dismisses the warning; Ctrl-c can also close it. Closing the picker during movement can terminate the helper without a warning and leave tabs partially reordered. Ordinary panes and their live processes remain intact. There is no automatic retry, rollback, or final focus action. Inspect tab positions after any interruption before trying again. No extra plugin permission is required.

`Ctrl-f m` follows the tmux pane-movement menu. It moves the original live pane, preserving its process and scrollback. Esc cancels; choosing the current tab does nothing. This menu needs the compiled status plugin and pinned runtime; rerun `make zellij-status zellij` and restart old sessions after upgrading. Existing-tab moves reserve a temporary inert split and replace it with the original pane, without running the default shell’s startup hooks or requiring additional plugin permissions. Cross-session movement remains unsupported. `Ctrl-f !` remains an optional direct shortcut, not a replacement for the menu.

`Ctrl-f M` moves all live tiled and floating terminals from the current tab to a selected existing tab in the modern configuration. There is no New Tab option; cancel and current-tab selection leave the layout unchanged. Plugins, exited commands, and the chooser are not transferred. A source with suppressed terminals is rejected, including hidden members of native stacks as well as scrollback-editor backing terminals. Expose or restore those source panes, or close the scrollback editor, before gathering. Native stacking in the destination is supported; this restriction applies to hidden panes in the source.

After confirmation, the chooser temporarily becomes tiled to keep the source tab alive while native pane replacements run. It exits after receiving the result. The invoking client follows its original pane; unrelated clients stay on their own tabs. If the source tab disappears, clients viewing it follow Zellij's native tab-close behavior. Floating terminals become tiled at the destination. Movement is sequential, not atomic: if a pane/tab changes or a reply is lost, inspect both tabs before retrying. If the CLI reply times out, the chooser stays open and defers Ctrl-c while it waits for the plugin to acknowledge that the operation has stopped. A deadline prevents queued requests from starting late or continuing with more transfers indefinitely. If the server becomes unreachable, keep the chooser open until it can confirm the stop. After acknowledgement an error remains visible until Enter; completed moves are not replayed or rolled back.

**Scroll mode:** `j/k` scroll, Ctrl-f/Ctrl-b page, Ctrl-d/Ctrl-u half-page, and `g/G` jump to the start/end. `/` starts a search; `n/N` find next/previous matches. `e` opens Neovim for arbitrary Vim selection. `y` copies an existing selection and returns to the prompt. `m` selects a command at the scroll position, and `c` copies the last command output when the application supplies OSC 133 shell markers. Esc or `q` returns to the bottom.

### Keyboard selection and paste

Use `Ctrl-f e` to open scrollback in Neovim, then use `v` for character selection, `V` for whole lines, or `Ctrl-v` for a rectangle. Move to extend the selection and press `y`. `:q!` returns to the original terminal. The installed Neovim integration preserves Unicode, multiline text, rectangle padding, and the final newline of a linewise yank. Zellij's scrollback export itself trims invisible spaces at the end of terminal lines; it cannot recover whitespace that is absent from the exported text.

Inside Zellij, each Neovim yank writes two destinations: the session copy buffer and a write-only OSC 52 request to the terminal's system clipboard. The same integration works in ordinary Neovim files as well as scrollback. It requires Neovim 0.10 or newer. The installed `zellij-context` helper identifies the nearest multiplexer in Neovim's process ancestry: an inner Zellij enables this integration even when it inherits `TMUX`, while an inner tmux keeps its existing clipboard integration.

**`Ctrl-f p` or `Ctrl-f ]` reads the dedicated session buffer.** The buffer is shared by panes and tabs with the same session name, user, and host. It survives detach/reattach and lasts until another yank replaces it, `zellij-clipboard clear` removes it, or the operating system clears its temporary runtime files. A renamed session uses a different buffer. The private file lives under `$XDG_RUNTIME_DIR/zellij-clipboard-<uid>` when that directory is configured, otherwise the host's temporary directory. It has a 1 MiB limit. Mouse selection and Zellij's native command-copy actions update the terminal clipboard; they do not replace this Neovim buffer.

The local `lane-status` plugin runs one hidden clipboard receiver for the session and installs the paste binding separately for each attached client without changing the configuration file. Its native identity survives tab closure, so closing a status bar cannot leave the shortcut pointing at a deleted plugin. Each keypress reaches only the requesting client's receiver instance, including when the bar is hidden or on another tab. The receiver captures the terminal pane and its process ID before reading the buffer. It checks that process again and sends bracketed paste to that pane, even if focus changes while the read is pending. Text is never interpolated into a shell command. Missing buffers, invalid UTF-8, oversized copies, and terminal control characters are reported in that client's visible bars instead of pasted. Tabs, carriage returns, and newlines remain valid text.

Grant permissions through the visible bar's first-use dialog. **Write to standard input** and **Reconfigure** enable the paste and client-specific shortcut; **Message and launch other plugins** lets the bar initialize the already-running receiver after consent and lets the receiver return paste notices. The receiver then uses the same native permission cache, without a separate hidden prompt. Internal messages address existing instances and do not launch extra panes. Start a new session after installing this change: Zellij's live configuration reload does not add background plugins to an already-running session.

**The terminal's paste shortcut remains the path from the system clipboard.** The configuration does not enable clipboard reads. OSC 52 copying also carries the selected text through SSH to the local terminal when that terminal permits OSC 52 writes; its policy and size limits still apply. [Zellij's compatibility guide](https://zellij.dev/documentation/compatibility.html) documents this transport, and [Kitty's `clipboard_control`](https://sw.kovidgoyal.net/kitty/conf/#opt-kitty.clipboard_control) controls Kitty's clipboard access. There is no success acknowledgement from an OSC 52 write, so emitting the request does not establish that a particular terminal accepted it.

`make test-zellij-clipboard` opens ANSI scrollback using the production filetype detection and renderer with the locked Baleia dependency, then checks the actual OSC 52 payload and session-buffer bytes for one multiline rectangle containing Unicode and trailing spaces. With two attached clients it changes focus while a read is pending and verifies exactly one bracketed paste in the original pane and no text in the other client's pane. It runs against the repository's pinned Zellij 0.46.0 runtime and Neovim 0.12.5. Desktop clipboard acceptance on macOS/Linux and the supported terminal over SSH still require a terminal-level check: copy the same multiline Unicode selection, paste into a local editor, compare the exact text, then repeat from a remote Zellij session. Record the terminal name/version and both outcomes before treating [#101](https://github.com/lanej/dotfiles/issues/101) as fully verified.

## Smart pane navigation

Bare **Ctrl-h/j/k/l** move between Zellij panes from the shell and foreground applications, including Codex while a task is running. Zellij captures the key before the application receives it. Vim/Neovim receives the key instead, moving among editor splits first and crossing into the adjacent Zellij pane at an editor boundary. Neovim normal and insert modes are supported. Navigation preserves a partially typed shell command.

The Zellij installer builds the local [pane-navigation plugin](../zellij/navigation/README.md), and `make zellij` applies its configuration and required permissions. To add navigation to an existing runtime without rebuilding that runtime, run `python3 scripts/install-zellij-navigation.py` followed by `make zellij`. New sessions load the background plugin automatically. In an existing session, run `zellij action launch-plugin --no-focus "file:$HOME/.local/share/zellij/plugins/pane-navigation.wasm"` once. Its keys are registered separately for each attached client and restored after configuration reloads. A fresh editor installation also needs `make vim-config`; restart Neovim after installing its configuration.

Navigation stays in the current tab and does not leave a zoomed pane. Internal Neovim split movement continues while zoomed; use `Ctrl-f z` to restore the outer layout before crossing a pane boundary. Outside Zellij, Zsh keeps its normal Ctrl-h/backspace binding and Neovim keeps Navigator's existing tmux/WezTerm detection. The shared `zellij-context provider` helper identifies the nearest live multiplexer from process ancestry: Zellij inside tmux navigates its own panes, and tmux inside Zellij retains tmux navigation despite inherited outer environment variables.

The helper verifies one attached client's current source pane and tab, then rechecks the same client/pane immediately before moving focus. It rejects ambiguous multiple-client ownership; use `Ctrl-f h/j/k/l` with multiple clients attached. This fixes delayed navigation acting on another tab. Stable Zellij's CLI does not offer an atomic conditional focus action, so a small window between the final check and the action remains; it is not a strict server-side compare-and-focus guarantee. Missing helpers or failed ownership inspection leave pane crossing disabled rather than selecting an outer multiplexer from stale variables.

The background plugin uses the focused pane and foreground command for its own attached client, then rechecks that the pane and tab still match before acting. It passes the keys to Vim and nested tmux/Zellij, and moves focus for other terminal programs. The final check and focus action remain separate server requests. Other application shortcuts continue to pass through locked mode.

## Equalize layout

Use **Ctrl-f Space** or **Ctrl-f Ctrl-o** to cycle to the **equalize** layout. It places one full-height pane in the left half and divides the right half into equal rows for the remaining panes. An indivisible column or row goes to one pane, so dimensions can differ by one cell; the pane title and separator still consume their normal space. This is a native layout change: pane positions can change, while the original pane IDs, focused terminal, shell processes, and scrollback survive. Percentage sizing continues to fit when the outer terminal changes size.

Start a new session with the updated `tmux` layout after `make zellij`; existing sessions retain their loaded swap layouts. The preset uses the same one-row top bar as columns, rows, and stacked layouts. The native cycle explicitly rearranges panes; the pinned configuration’s `Ctrl-f =` helper instead balances an existing aligned group with approximate resize steps. The legacy configuration keeps the native cycle and leaves `=` unbound.

**Exact cell sizing and tmux’s timed resize-repeat window remain unavailable.** The pinned configuration’s `g/G` helper implements the golden-ratio skip and cap policy using nearest-reachable native percentage steps, as described above. Legacy `g/G` remain unbound. Layout overrides can create extra shells when launch metadata does not match, so the helper does not use them. Ctrl-f Ctrl-r remains an explicit resize mode that ends with Enter or Esc.

Upstream implementation references: [native resize step](https://github.com/zellij-org/zellij/blob/v0.45.1/zellij-server/src/panes/tiled_panes/tiled_pane_grid.rs), [layout reuse and overrides](https://github.com/zellij-org/zellij/blob/v0.45.1/zellij-server/src/tab/layout_applier.rs), and [CLI actions](https://github.com/zellij-org/zellij/blob/v0.45.1/zellij-utils/src/cli.rs).

## Shared popup and session shutdown

**Ctrl-f P** opens a floating view of the dedicated `dotfiles-popup` session. Press **Ctrl-f P** again inside the popup to detach that view. Reopening it from another tab or another Zellij session on the same host and socket namespace returns to the same live shell, including its working directory and unexported variables. Each opening attaches a client to that session; it does not move a working pane between sessions. The outer configuration automatically focuses nested sessions so the popup receives its own prefix keys.

The popup uses the installed regular configuration and `tmux` layout, including the selected modern or legacy bar, pane-navigation plugin, theme, history limit, and keybindings. Bare **Ctrl-h/j/k/l**, prefix splits and pane controls, tabs and pickers, resize, scroll/search modes, and **Ctrl-f e** scrollback editing work as in a regular window. Modern clipboard paste and client controls have the same visible bar and background receiver as regular sessions, with the same permission requirements. Legacy installations retain their ordinary legacy limitations. The launcher adds only a layout-level **Ctrl-f P** detach override and disables resurrection snapshots; it does not maintain another keymap. Splits are tiled panes inside the nested session, while the outer floating view remains one pane.

Prefix `P` or `d` hides the view without ending its shells. The popup stays alive after its view closes or its outer session shuts down. Closing its last shell or explicitly confirming shutdown inside the popup ends that scratch session; its in-memory state does not survive server exit or reboot. Keep `dotfiles-popup` reserved for this workflow. **Ctrl-f F** toggles other floating panes.

To apply, run `make zellij` after the normal runtime/plugin installation. A newly created popup gets the shared configuration and layout. An already-running popup retains its saved configuration and existing panes on reattach: updating the launcher does **not** reset it, replace shells, or inject a new layout. The retired `zellij/popup.kdl` is left unchanged because old servers may still watch it. Finish or save the work in that old popup and exit its shells when convenient; the next **Ctrl-f P** creates the new version. Do not kill the popup to apply this change while it contains live work. New-session layout/plugin startup and history capacity are not retroactively applied to an old session.

Automatic nesting focus applies to other compatible Zellij sessions too, including sessions reached over SSH. With these dotfiles in the guest, **Ctrl-f u** returns to its containing session without detaching; **Ctrl-f i** in the host enters its focused nested session again. A guest with another configuration uses its own `FocusHostSession` binding (upstream 0.45.1 defaults to Ctrl-o, then `]`). Detaching the guest also returns control to its host.

**Ctrl-f Ctrl-q** in the main configuration opens a confirmation naming the current session. Type `SHUTDOWN` to close its panes and disconnect its clients, or press Enter or Ctrl-c to cancel. The helper checks the owning server's Unix socket identity again before executing; development builds also check Zellij's session-ID index. It rejects a session that was renamed or replaced while confirmation was open. This ends one Zellij session and its server; other sessions, including a separately running popup, continue. **Ctrl-f d** still detaches the current client without shutting down its session.

**Ctrl-f D** opens a fuzzy chooser of clients attached to the current session, showing each client's native ID, focused tab, and pane title. Enter detaches the selected attachment; Esc or Ctrl-c cancels. The other clients, panes, and sessions keep running. The chooser waits up to five seconds for a complete list while newly attached clients become ready. Every attached client needs the status plugin's permissions; check its permission prompt on each client if the chooser times out. A missing receiver produces an error instead of falling back to detaching every other client.

The pinned Zellij 0.46.0 server assigns a new native ID to every attachment and removes detached plugin instances. Each selection includes that ID, the server and plugin identity, and a plugin-instance nonce. The receiver checks the token and current native focus before detaching its own client. An older server is rejected even if a newer executable is on PATH. Ordinary **Ctrl-f d** remains the direct current-client detach.

Implementation references: [native nesting options and focus behavior](https://github.com/zellij-org/zellij/blob/v0.45.1/zellij-integration-tests/tests/nested_session_handling_config.rs), [CLI session actions](https://github.com/zellij-org/zellij/blob/v0.45.1/zellij-utils/src/cli.rs), and [plugin client controls](https://github.com/zellij-org/zellij/blob/v0.45.1/zellij-tile/src/shim.rs).

## Native agent status and attention

Codex pane titles are configured in [`codex/zellij-title.json`](../codex/zellij-title.json) through the existing Codex lifecycle hooks and Zellij's pane-name command. Run `make codex-tmux-config` to install missing hooks, then review any new hooks in Codex's `/hooks` screen. The configuration produces `󰚩 01a19d8f  | .files`; `{id:.8}` selects eight characters from the thread ID, and the configured glyphs distinguish working, ready, attention, and interrupted states. These are event-driven glyphs rather than an animated spinner. The helper identifies the owning pane from Codex's native thread title, preserves that association while the compact title is displayed, and restores application-controlled titles on `SessionEnd`. It does not change the Zellij runtime or require restarting its server.

Claude pane titles use [`claude/zellij-title.json`](../claude/zellij-title.json), producing `✳ b4ae3f92  | .files` with an eight-character session ID and the same status glyphs, plus `` for failure. Run `make claude-config` to apply the managed hooks, then start a new Claude session. The helper uses Claude's process-local Zellij pane identity and nearest multiplexer, retains the full session ID for ownership checks, and restores application-controlled titles on `SessionEnd`. Nested tmux sessions keep their tmux title handling. These titles update on lifecycle events and require no Zellij server restart.

With the compiled bar installed, the Nord top bar shows zero-based tabs, native attention glyphs, host, clock, battery, prefix, and zoom state. `?` marks a question, `!` another request for attention, `×` failure, `✓` completion, and `●` work. The right-hand `!` count includes requests, failures, and completed results across local sessions; `●` counts working panes.

Zellij 0.46 owns these states and keeps tracking them while every client is detached. The bar reads native attention events; no broker, sampled terminal title, or custom conversation ownership is required. `Ctrl-f Ctrl-a` uses the existing status plugin to restore tmux's tab selection: exclude the current tab, prefer requests and failures, otherwise visit activity/bell tabs, and wrap in numeric tab order. Quiet completions are not candidates. The key is routed only to the invoking client; it does not switch other clients or jump to another session. Native bells remain useful for programs that do not publish richer state. Explicit native cross-session triage remains available through `Ctrl-f :` → `go-to-next-attention`.

The shared popup currently applies this key inside its own session. Returning to the host with `Ctrl-f u` and pressing `Ctrl-f Ctrl-a` there uses the host's tabs. Automatic popup-to-host triage remains a parity gap: the public plugin API does not provide a client-specific host action, and a broad host-focus message can affect other viewers. This configuration does not add an input interceptor or guess the host client.

Claude Code 2.1.295 and Codex 0.164.0 publish OSC 7501 program status; the installation catalog pins those versions. Other applications need to emit that protocol for detailed native states. The existing agent-status broker remains available for tmux. Configuration-only setup and the stable 0.45.1 runtime use the built-in bar and one-based tab keys until a compatible native-attention bar is available.

On first use, the bar asks to read application state, run its local host-metadata helper, and switch tabs. Focus the permission prompt with `Ctrl-f k`, then press `y`. The bar becomes unselectable after consent. Restart the session after changing the plugin/runtime; replacing an executable does not update an existing server.

## History and recovery

- **Live history:** at most 100,000 scrollback lines per pane.
- **Recovery history:** at most 10,000 saved scrollback lines per pane, with the viewport and session layout saved every 60 seconds.
- **Recovery behavior:** reattaching to an exited session reconstructs its layout and offers to rerun its commands. The native manager also lists these sessions. The fuzzy picker lists running sessions only.

These are line limits, **not a byte budget or a guarantee against memory exhaustion**. Recovery snapshots do not page live scrollback out of RAM. Detaching preserves live processes; restoring after server exit or reboot relaunches commands and does not restore their process memory. A crash can lose changes since the last snapshot.

## Differences that remain

| tmux behavior | This configuration |
| --- | --- |
| Agent status and attention | Native program status supplies the bar. `Ctrl-f Ctrl-a` restores local tmux-style tab selection; the command prompt retains explicit cross-session triage. Popup-to-host triage is still manual. |
| Exact Claude conversation restoration via saved session IDs | Zellij's native command restoration is enabled; the custom `claude --resume` session-ID integration remains tmux-specific. |
| Rex OSC 7501 delivery through the patched tmux server | No replacement transport in this configuration. Upstream development features are not assumed to exist in stable 0.45.1. |
| Smart bare Ctrl-h/j/k/l across Neovim and tmux panes | Supported in Neovim normal/insert modes, shells, and foreground applications such as Codex. Nested tmux/Zellij retains its own controls. |
| Moving live windows/panes across sessions, including parking in `later` | Unsupported by Zellij. `H` and `S` are not assigned a restart-based substitute. `m`, `M`, and `!` move live panes between tabs in the same session. |
| Vi visual/rectangle copy mode and shared paste buffers | Neovim provides keyboard selection. `Ctrl-f p` or `Ctrl-f ]` uses the session's private Neovim-yank buffer; the terminal shortcut pastes the system clipboard. |
| Zero-based windows | Tab labels, picker labels, and `0`–`9` keys are zero-based; Zellij's underlying CLI positions remain one-based. |
| Three-cell resizing and timed repeat bindings | Native Zellij resize steps; an explicit repeatable mode under prefix+Ctrl-r. |
| Golden-ratio helper (`g/G`) | Pinned runtime: jq helper preserves the width guard and cap using approximate native steps. Legacy bindings remain unbound. |
| Equalization (`=`) | Pinned runtime: balance one existing aligned group with approximate native steps. The separate native equalize preset remains available through layout cycling, including legacy configurations. |
| Dedicated shared `popup` session | `P` attaches to the live `dotfiles-popup` scratch session across tabs and sessions on the same host; `F` toggles other floating panes. |
| Custom clock, battery, host, and agent status segments | One bundled top tab bar, with no bottom status bar or additional plugin download. |
| Kill-server confirmation | `Ctrl-q` confirms shutdown of the current session's server. It does not shut down every Zellij session. |
| Client-detach chooser | `D` detaches one selected attachment and rejects observed stale choices. The pinned 0.46 runtime uses fresh attachment IDs; `d` directly detaches the current client. |

Reference: [Zellij 0.45.1](https://github.com/zellij-org/zellij/releases/tag/v0.45.1), [session resurrection](https://zellij.dev/documentation/session-resurrection.html), and [the upstream cross-session movement limitation](https://github.com/zellij-org/zellij/issues/5118).

## Check a change

```sh
zellij setup --check
make test-zellij
make test-zellij-codex-titles
make test-zellij-claude-titles
make test-zellij-navigation
make test-zellij-layout
make test-zellij-sessions
make test-zellij-auto-title
make test-zellij-tab-labels
```

The workflow check installs into a temporary home, sends real prefix keys to Zellij in a pseudo-terminal, exercises the actual fzf pickers, and verifies that detach/reattach keeps the panes and a shell's in-memory state. The navigation check uses the installed pane-navigation artifact, real Neovim, and the pinned Navigator plugin to exercise editor boundaries in both directions, insert mode, zoom, navigation from a raw-terminal foreground application, both multiplexer nesting directions, and a tab change during a delayed navigation query. It requires the installed navigation plugin, Neovim 0.12+, Zsh, tmux, git, and access to the public plugin repository. Both checks require local Unix sockets and PTYs and terminate only their own named sessions. Linux and macOS CI run them against the same pinned fork revision as bootstrap. Native Rust regressions live with the fixes in the fork. These checks do not establish performance under production agent output, a live Codex model task, or clipboard behavior in a particular terminal emulator.

The layout check cycles through the installed layout control with an explicit-command shell, observes equalize dimensions before and after a terminal resize, and checks stable pane IDs, focus, shell PIDs, unexported shell variables, and scrollback.

The agent title checks run configured lifecycle hooks against private native panes and observe the compact titles, ownership changes, and restoration of application-controlled titles. They use representative hook payloads and do not exercise a live Claude or Codex model task.

The session checks use two real attachments to exercise chooser cancellation, exact selected-client detach, rejection after reconnect, self-selection and helper cleanup, and ordinary detach while another session survives. They also observe host/guest focus control, splitting and bare navigation inside the popup, scroll/search and real Neovim scrollback editing, tab creation/rename with the visible bar, and preservation of both shells' PIDs, working directories, and unexported state across hiding, another tab, and another outer session. They exercise shutdown cancellation, reject an old confirmation after renaming its session and recreating the original name, and verify that other sessions and the original popup shell survive a valid targeted shutdown. All servers use a private temporary socket directory. Run `python3 scripts/test-zellij-sessions.py --popup-only` to check the popup without the unrelated client chooser and shutdown workflows.
