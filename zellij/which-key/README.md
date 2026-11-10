# Zellij WhichKey

Live keybinding reference for the configured `Ctrl-f` prefix.

Press **Ctrl-f ?** to open the floating guide. Use **j/k** or the arrow
keys to scroll and **Esc** to dismiss. Bindings are obtained from Zellij's
`InitialKeybinds` event, rather than maintaining a duplicate list of keys.
Descriptions are annotated next to each `bind` in `zellij/config.kdl` as
`// which-key: ...` comments. The plugin embeds those labels at build time,
then joins them to the *active* bindings reported by Zellij. This prevents a
second, drifting label map in Rust. Rebuild after changing the KDL labels.
Unannotated bindings fall back to Zellij's action representation.

This first iteration intentionally does **not** intercept or replay keys.
The floating guide is read-only: existing prefix bindings keep their native
execution, including private plugin messages and nested Zellij sessions.

Install with `make zellij-which-key`. Built for the pinned patched Zellij.
Automatic delayed appearance after the prefix is a separate follow-up,
requiring lossless interception, client scoping and cancellation tests.
