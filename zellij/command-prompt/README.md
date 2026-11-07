# Zellij command palette

`Ctrl-f :` opens a centered native popup. Type a Zellij action directly, or search the suggestions by name or description. Tab accepts the highlighted suggestion; Enter runs the command you entered. Suggestions never execute a command. Esc or clicking outside closes the popup.

| Input | Suggestions |
| --- | --- |
| `rename-ta` | Matching actions and their descriptions |
| `new-pane --dir` | Native flags, including `--direction` |
| `new-pane --direction ` | Accepted directions |
| `rename-tab ` | The current name, quoted for editing |
| `go-to-tab-name ` | Live tab names, including names containing spaces |
| `focus-pane-id ` | Live pane IDs, titles, and tabs |
| `switch-session ` | Running session names and client counts |

Arrow keys select suggestions. Ctrl-u clears before the cursor, Ctrl-k clears after it, and Ctrl-w deletes the previous word. Up from an empty command recalls history; Ctrl-p/Ctrl-n recall older/newer commands and restore the unsubmitted draft. Ctrl-r or `history` opens searchable history. It retains the last 32 distinct submitted commands in memory for each attached client, until the plugin/session restarts. Recent actions rank ahead of other equally matching commands.

`help` opens the command list. An action's `--help` displays its native documentation; Enter or Esc returns to the editable command. Parse errors retain the command and display the error inline. The completion engine uses metadata from the pinned Zellij CLI parser; unsupported variants are excluded from flag suggestions. Program arguments after `--` are left to that program.

## Search and jump

| Command | Result |
| --- | --- |
| `list-panes` | Searchable table of selectable panes, titles, commands, and tab positions |
| `list-tabs` | Searchable table of tab names, display positions, and stable IDs |
| `list-sessions` | Searchable table of running sessions and counts |

Type to filter the table; arrows select a row; Enter jumps to it. Esc returns to the original command. Tables refresh when the live state changes. Pane and tab selections carry stable IDs, which are checked again at dispatch. Session selection switches only to an existing running session. Query commands take no flags; use the terminal for CLI JSON output and the wider CLI query interface.

The header shows the original session, tab, and pane. Tab labels match the bar's zero-based positions. The native `go-to-tab` command retains its one-based syntax, with that index shown in its completion details. `go-to-tab-by-id` selects a stable tab ID.

## Command scope

Arguments use shell-style quoting without shell evaluation. `$HOME`, `$(...)`, wildcards, pipes and semicolons have no shell expansion. To start a program, use an explicit action such as `new-pane -- PROGRAM ARG...`.

The existing supported pane/tab actions retain Zellij's syntax. `focus-pane-id`, `go-to-tab-by-id` and `switch-session` accept one live target. Layout-file loading and external plugin installation remain terminal operations. Some explicit pane/tab-ID variants are CLI-only in the pinned plugin protocol; the palette reports those as unsupported. Pane-relative creation flags (`--near-current-pane`, `--stacked`, `--in-place`, `--no-focus` on `new-pane`/`edit`) require a terminal-pane origin and remain terminal operations.

The native action API does not return CLI stdout or all runtime errors. Submitting an action is not a guarantee of its eventual runtime result. Parse failures are shown inline; an origin that changed or closed is rejected before dispatch.

## Installation and permissions

For an existing pinned installation, run `make zellij-command-prompt`, then `make zellij` and restart the session. Default configuration never invokes Cargo. The legacy 0.45.1 configuration does not enable the palette. No additional runtime patch or shell dependency is required.

The background dispatcher opens the same WASM as a client-local native popup. The popup edits and renders suggestions; the dispatcher retains history, checks the original pane/tab, and applies accepted commands for that client. Opening the palette leaves hidden floating panes and the persistent `Ctrl-f P` popup hidden.

The plugin requests application-state reads, native popups and actions, client-specific runtime binding updates, target/session changes, and private messages between its popup and dispatcher. Existing installations may need to accept the expanded permissions. It requests no filesystem, environment, network or host-command access. An explicit `new-pane -- PROGRAM` action can still start a program.

## Verification

`make test-zellij-command-prompt` installs into a temporary home and exercises the production prefix binding with two real attached clients. It checks completion, editable errors, target queries, live updates, private history, hidden floats, reloads and origin lifecycle. It requires the pinned runtime, Python with pyte 0.8.2, and the Rust 1.95.0 WASM toolchain. Sessions, grants and sockets are isolated from existing sessions. CI retains decoded terminal grids for visual review.

For focused native model checks, run `RUST_MIN_STACK=16777216 cargo test --locked --manifest-path zellij/command-prompt/Cargo.toml`. The generated upstream CLI parser requires a larger stack in unoptimized Rust test threads.
