# Zellij command prompt

`Ctrl-f :` opens the pinned runtime's native centered text-entry popup. Type a
Zellij action without the `zellij action` prefix, for example:

- `rename-tab "work notes"`
- `new-pane --direction right`
- `new-pane --floating -- htop`
- `move-focus left`
- `resize increase right`
- `rename-pane "build"`

Enter runs the command; Esc or clicking outside cancels. An empty command also
closes the prompt. `help` opens a searchable list of supported actions, selecting
one fills the input for editing. Add `--help` to an action to see its native
options. `history` picks from this client's last 32 submitted commands and asks
you to review the selected command before running it. History is in memory only,
and goes away when the plugin or session restarts. There is no inline completion
or tmux command compatibility layer.

Arguments use shell-style quoting but are not evaluated by a shell. `$HOME`,
`$(...)`, wildcards, pipes and semicolons have no shell expansion. To start a
program, use the explicit `new-pane -- PROGRAM ARG...` action. Names and action
options come from the pinned Zellij CLI parser. `go-to-tab` uses Zellij's
one-based position, even though the configured bar labels tabs starting at zero.

The prompt handles pane/tab/session actions, not stdout-producing queries such
as `list-panes`, layout-file loading or external plugin installation. Use a
normal terminal for those. Command parse errors keep the input available to
correct. Zellij's action API does not return the CLI's stdout or all runtime
errors; a closed/changed original pane or tab is rejected before dispatch.
Some explicit pane/tab-ID variants are CLI-only in the pinned plugin protocol;
the prompt reports those as unsupported before dispatch.
Pane-relative creation flags (`--near-current-pane`, `--stacked`, `--in-place`
and `--no-focus` on `new-pane`/`edit`) also stay in the terminal: the plugin API
otherwise treats the hidden plugin itself as their source pane.

The implementation calls the built-in `zellij:prompt` plugin, not an ordinary
floating terminal. Opening it does not reveal other hidden floating panes and
does not change the persistent `Ctrl-f P` popup. Each attached client has its own
private binding, prompt, action dispatcher and history. No action is sent
through the CLI's last-active-client fallback.

`Ctrl-f C` uses the same client-private routing to create a session immediately,
without opening a prompt. It passes the focused pane’s directory and explicitly
selects the installed `tmux` layout, so a popup’s detach override is not inherited.
The original session and its processes remain live.

## Install and verify

The selected patched/main runtime installation includes this plugin. For an
existing pinned installation, run `make zellij-command-prompt` then `make zellij`
and restart the session. Default configuration never invokes Cargo. The legacy
0.45.1 configuration does not enable this feature.

On first use of a fresh session configuration, Zellij asks for permission to
read pane state, switch sessions, open the built-in popup, run Zellij actions, and install the
client-specific runtime binding. The plugin does not request full disk access,
environment reads, network access or a separate host-command permission.
The action permission can still start programs through an explicitly entered
`new-pane -- PROGRAM` command.

`make test-zellij-command-prompt` installs into a temporary home and exercises
the production prefix binding with two real attached clients. It requires the
pinned runtime, Python with pyte 0.8.2, and the Rust 1.95.0 WASM toolchain. Sessions,
permission grants and configuration are isolated from the user's running sessions.

After building the status bar with `make zellij-status`, run
`make test-zellij-session-keys` independently to exercise direct creation and
rename with two clients, the real draft banner, and popup layout boundaries.
