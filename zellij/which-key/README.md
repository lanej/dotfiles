# Zellij WhichKey

Live keybinding reference for the configured `Ctrl-f` prefix.

Press **Ctrl-f** and pause for 350 ms to see the passive overlay. The next
native shortcut still runs directly through Zellij; it dismisses the guide.
**Ctrl-f ?** pins a focused, scrollable reference guide; use **j/k** or the
arrow keys to scroll and **Esc** to dismiss. Bindings are obtained from Zellij's
`InitialKeybinds` event, rather than maintaining a duplicate list of keys.
Descriptions are annotated next to each `bind` in `zellij/config.kdl` as
`// which-key: ...` comments. The plugin embeds those labels at build time,
then joins them to the *active* bindings reported by Zellij. This prevents a
second, drifting label map in Rust. Rebuild after changing the KDL labels.
Unannotated bindings fall back to Zellij's action representation.

The passive overlay intentionally does **not** intercept or replay keys.
Zellij remains the authority for binding execution, including private plugin
messages and nested sessions. A monotonic deadline prevents stale timer events
from opening the overlay early after a cancelled prefix.

Install with `make zellij-which-key`. Built for the pinned patched Zellij.
Run `make test-zellij-which-key` against the pinned runtime. CI uploads
terminal captures from the actual Zellij PTY as SVG and plain text.
