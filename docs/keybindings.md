# Keybinding registry

The registry owns all 32 configured Kitty shortcuts and all 26 active skhd window shortcuts, and checks them against any new native bindings. Both configurations generate their owned shortcuts from `config/keybindings.toml`. Initial coverage is explicit root-mode mappings in `kitty/kittyconf` and default-mode hotkeys in `yabai/skhdrc`. A shortcut free in Kitty can still be consumed globally by skhd: Cmd+Shift+L, for example, is bound there to move a window east.

```sh
make keybindings
uv run --no-project scripts/keybindings.py list --chord cmd+shift+l
uv run --no-project scripts/keybindings.py list --chord cmd+shift+l --json
make check-keybindings
```

Reports identify both actions and their source locations. Modifier order and aliases such as `super`/`cmd`, `opt`/`alt`, and `return`/`enter` normalize to the same chord. A `global-overlap` means skhd may intercept a Kitty shortcut; a `duplicate` means two bindings claim the same chord within an application. These are conflicts to inspect, even when an override was intentional. The tool does not automatically change keys or decide whether skhd is running.

Every report states coverage. Includes, application defaults, macOS system shortcuts, tmux, Zellij, Neovim, and live runtime state are outside the initial scan. An empty query means no matching binding in this inventory; it does not establish that a shortcut is globally available. Unsupported binding syntax, including modes, process maps, forwarding, and key sequences, produces an error with a source location. Add an adapter with the relevant scope semantics before adding those forms to scanned files. Future tmux or editor adapters must retain prefix tables and modes rather than treating sibling application shortcuts as conflicts.

## Own a binding

To backfill from existing native configuration, extract unmanaged bindings as TOML records:

```sh
uv run --no-project scripts/keybindings.py extract skhd > /tmp/skhd-bindings.toml
uv run --no-project scripts/keybindings.py extract kitty > /tmp/kitty-bindings.toml
```

Extraction reads only the selected native source file and works before a registry or generated markers exist. It prints registry table fragments, with original source locations as comments, but does not modify files. Review the suggested chord-based IDs and placeholder descriptions, give them descriptive names, and append the records to `config/keybindings.toml` under its existing version header. Remove the corresponding native mappings and add the generated marker pair before generation. Duplicate chords or unsupported syntax fail without partial TOML output. Bindings already in a generated section are excluded, so extraction after a complete backfill produces no records. Commented-out examples are not imported.

Edit [the registry](../config/keybindings.toml) for an owned shortcut:

```toml
[[binding]]
id = "kitty.open-last-web-link"
app = "kitty"
chord = "cmd+shift+o"
action = "kitten open_last_url.py"
description = "Open the last web link."
```

IDs must be unique. `app` is `kitty` or `skhd`; actions remain native configuration strings, owned by their application. Chords accept letters, digits, F1–F20, Enter, Tab, Space, Backspace, Escape, Delete, Home, End, Page Up/Down, Insert, and arrow keys with explicit Ctrl/Alt/Shift/Cmd modifiers. Kitty also supports Equal and Minus. Unknown names, skhd punctuation, hardware keycodes, side-specific modifiers, and layout-dependent shifted-symbol equivalence are outside this adapter. Supported names follow [Kitty's key aliases](https://github.com/kovidgoyal/kitty/blob/master/kitty/key_names.py) and [skhd's literal names](https://github.com/koekeishiya/skhd/blob/master/src/tokenize.h); generation translates canonical Enter and Page Up/Down back to the application's spelling. A record has exactly one chord and one action. Give multiple shortcuts separate IDs. Registry records describe intended configuration; native parsers remain authoritative for action validity.

Actions preserve native backslash-newline continuations and tabs, including indentation inside quoted shell arguments. The TOML export encodes them with string escapes; generation restores them without flattening commands. Other fields remain single-line strings, and bare action newlines or other control characters are rejected.

Run `make generate-keybindings`, inspect the diff, then run `make test-keybindings` and the affected application's native check. For link shortcuts, run `make test-kitty-last-url`. Commit the registry and its generated output together. The CI check rejects conflicts and stale generated content.

Generation changes only the section between `# BEGIN generated keybindings (scripts/keybindings.py)` and `# END generated keybindings` in each source file. Everything outside that section remains native configuration. To migrate an existing binding, add its registry record, remove its unmanaged mapping, and place one marker pair where its generated section belongs. Preserve mapping order when application override rules matter. A missing or malformed marker pair is an error; the tool does not append or relocate sections automatically.

```sh
uv run --no-project scripts/keybindings.py generate --check
make generate-keybindings
```

Generation refuses detected conflicts before writing. It does not reload applications or change installed symlinks. `list` and `check` combine desired registry records with unmanaged source bindings, excluding the generated section to avoid counting owned entries twice. When the generated section differs, `drift` names the affected file; repair it before relying on installed behavior. Owned records point to the TOML declaration, and unmanaged bindings point to their native file and line.

The CLI exits 0 for a successful inventory or clean check, 1 for check conflicts/drift, and 2 for invalid input or I/O errors. `generate --check` exits 1 on drift without writing; generation conflicts exit 2. JSON reports contain `coverage`, `bindings`, `conflicts`, and `drift`. `--root` before the subcommand inspects a different checkout.

## Close Kitty windows and tabs

| Shortcut | Action |
|---|---|
| Cmd+Q | Close the active Kitty window with confirmation. |
| Cmd+Shift+D | Close the active Kitty window with confirmation. |
| Ctrl+Shift+W | Close the active Kitty window with confirmation. |
| Cmd+W | Close the active tab with confirmation; Enter defaults to No. |

A Kitty window is a terminal pane within a tab. Cmd+Q is mapped to close that window rather than quit the entire application. Closing the last window also quits Kitty on macOS.

`confirm_os_window_close 0` disables the global close guard, allowing OS-window closes and application quit requests during system restarts to proceed without a Kitty prompt. Cmd+W uses `close_tab_with_confirmation.py` to always ask before closing the tab, including at an idle shell prompt. Press **Y** to close or **N**, **Escape**, or **Enter** to keep the tab. The other three shortcuts use `close_window_with_confirmation` and also ask before closing. Reload configuration with **Cmd+Shift+R** after changing this setting.

## Open a file from a Zellij pane

Focus the agent pane containing the filename and press **Cmd+Shift+U**. Pick a home-row hint to open the file. Text opens in an existing Neovim in the same Zellij tab, with keyboard focus moving to the editor. If several registered editors exist, choose one with the keyboard; Escape cancels. If none exists, Neovim opens in a split on the right. Unsaved buffers are preserved.

References such as `src/main.rs:42:7` open at line 42, column 7. Absolute paths, `~/` paths, quoted paths with spaces, and `file://` hyperlinks work too. File-link fragments accept `#42`, `#L42`, `#L42C7`, and line ranges such as `#L42-L50`, which open at their first line. Common extensionless names such as `README` and `Makefile` are recognized.

Images open in a preview split on the right. From a floating source pane, a new editor or preview opens in another floating pane. Press **Enter** to close an image preview. The same picker opens ordinary hyperlinks with Kitty.

Relative filenames resolve in the source pane's working directory. A wrapped `docs/screenshots/plan-viewer/fixture-running-overview.png` opens from that worktree. Over `zssh`, the remote host resolves files, routes them, and streams image previews to Kitty. Other files use the associated application on that host; a missing application produces an error without downloading the file.

Run `make kitty-config zellij-helpers zellij-config vim-config` and reload Kitty with **Cmd+Shift+R**. On the machine running Zellij, use the managed 0.46 runtime and install Neovim, `file`, and `kitten`. Restart existing Neovim instances to register them for reuse. For a remote session, apply the helper, Zellij, and Neovim configuration on that host too. Older image-only helpers retain image hints until updated. Standalone Kitty retains its ordinary hyperlink behavior.

### File routing

Edit [the extension-routing table](../zellij/file-routes.toml), installed as `~/.config/zellij/file-routes.toml`. It is read on every selection. Extension matching ignores case and prefers the longest suffix, so `tar.gz` takes precedence over `gz`. Assign each extension once. Built-in handlers are `neovim`, `image`, and `system`; the last uses `open` on macOS or `xdg-open` on Linux. Unmatched files use MIME detection: text opens in Neovim, supported images use the preview, and other files use the system opener.

Custom programs use separate arguments and run without a shell. `launch = "pane"` opens an interactive pane beside the source; `launch = "background"` starts the program without a pane. The placeholders `{path}`, `{line}`, and `{column}` expand once, with missing positions defaulting to 1. For example:

```toml
[[routes]]
extensions = ["drawio"]
handler = "command"
command = ["drawio", "{path}"]
launch = "background"
```

Missing files, invalid routes, unavailable programs, and immediate application failures leave an error in the temporary hint pane until Enter. A successful background launch confirms that the program started; it does not confirm that an application displayed the file.

## Kitty hint selection

Cmd+Shift+U selects hyperlinks and file references; Ctrl+Shift+E selects visible URLs. Both use `asdfghjkl` labels ordered from top to bottom. Unmatched text dims to Nord gray, link text turns Nord white, and labels use Nord purple with dark lettering. Escape cancels and restores the original pane colors.
