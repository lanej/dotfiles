# Why Not…

Tools that are configured or explored but deliberately not adopted, with rationale.

## Ghostty

Ghostty is configured (`ghostty/`) but not used as the default terminal. Ghostty implements tabs as native macOS `NSWindowTabGroup` windows — `tabbingMode` is set to `.preferred`/`.automatic` in the source regardless of `macos-titlebar-style`. Yabai sees each tab as a separate managed window, causing the active window to jump and resize on every tab switch. There is no config option to set `tabbingMode = .disallowed`.

Kitty implements tabs entirely within a single window; yabai sees only one window per kitty instance.

See [evaluated.md](evaluated.md) for tools that may unblock a Ghostty migration.
