# Keybinding registry

The registry owns all 30 configured Kitty shortcuts and all 26 active skhd window shortcuts, and checks them against any new native bindings. Both configurations generate their owned shortcuts from `config/keybindings.toml`. Initial coverage is explicit root-mode mappings in `kitty/kittyconf` and default-mode hotkeys in `yabai/skhdrc`. A shortcut free in Kitty can still be consumed globally by skhd: Cmd+Shift+L, for example, is bound there to move a window east.

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
