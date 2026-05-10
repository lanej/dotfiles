# Tech Radar

Tool and technology decisions, organized by ring.

| Ring | Meaning |
|---|---|
| **Adopt** | In active use; recommended |
| **Trial** | Being evaluated; promising enough to run in real workflows |
| **Assess** | Worth watching; not yet trialed |
| **Hold** | Not adopted; rationale documented |

---

## Adopt

### Kitty

Terminal emulator. Implements tabs entirely within a single OS window — yabai sees exactly one window per Kitty instance, so tiling and focus work correctly.

### yabai

Tiling window manager via the macOS Accessibility API. Manages all windows at the OS level.

---

## Trial

### AeroSpace

[AeroSpace](https://github.com/nikitabobko/AeroSpace) is a tiling WM that operates at the app level rather than hooking into the macOS window server. It may handle Ghostty's native `NSWindowTabGroup` tab grouping without the window-jumping issue that currently blocks a Ghostty migration (see **Hold: Ghostty**).

---

## Assess

_Nothing here yet._

---

## Hold

### Ghostty

Configured (`ghostty/`) but not used as the default terminal. Ghostty implements tabs as native macOS `NSWindowTabGroup` windows — `tabbingMode` is set to `.preferred`/`.automatic` in the source regardless of `macos-titlebar-style`. Yabai sees each tab as a separate managed window, causing the active window to jump and resize on every tab switch. There is no config option to set `tabbingMode = .disallowed`.

Revisit if AeroSpace (see **Trial**) proves able to handle native tab groups transparently.
