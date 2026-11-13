# Keyboard jump plugin

This dotfiles-owned WASM plugin adds Hop-style character jumps to native Zellij copy mode. Enter copy mode with `Ctrl-f [`, press `s`, type a character, then choose its label. An active `v` or `V` selection extends to the target; `y` uses Zellij's clipboard. Tab pages through dense matches. Escape cancels the jump while preserving native selection. Matching is case-sensitive and targets the visible viewport.

The fork supplies frozen cell positions, native cursor/selection operations, temporary overlays, and ordered keyboard capture. The plugin owns matching, label assignment, paging, and interaction state. Its SDK and the runtime installer are pinned to the same native API revision. The fork contains no copy of this plugin.

With `zellij.source = "patched"`, run `make zellij-runtime zellij-copy-hop` to install the compatible runtime and plugin, then start a fresh Zellij session using the dotfiles config. The plugin requests pane reading, application-state changes, input interception, and mode updates. It does not run an editor or copy terminal text through Neovim. Ordinary copy motions remain native during this first migration step.

`make test-zellij-copy-hop` checks formatting and Clippy, then runs the installed plugin through the real terminal acceptance path. For a candidate build, use `uv run --script scripts/test-zellij-copy-hop.py --binary /absolute/path/to/zellij --plugin /absolute/path/to/dotfiles-copy-hop.wasm`. uv supplies the pinned pyte decoder; the detector uses an isolated HOME, session, permissions, and sockets. It checks original-text OSC 52 output, not host clipboard acceptance. Build a candidate plugin with `cargo build --locked --target wasm32-wasip1 --manifest-path zellij/copy-hop/Cargo.toml`.
