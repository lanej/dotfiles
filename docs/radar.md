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

### OpenCode

AI coding assistant with a TUI interface. Put on hold due to memory leaks during long sessions and persistent lag in supporting new model releases — discovered while working around a Vertex AI 1M context window bug that required a [upstream PR](https://github.com/anomalyco/opencode/pull/14055) to fix.

Revisit if memory stability improves and model support keeps pace with provider releases.

### Ghostty

Ghostty implements tabs as native macOS `NSWindowTabGroup` windows — `tabbingMode` is set to `.preferred`/`.automatic` in the source regardless of `macos-titlebar-style`. Yabai sees each tab as a separate managed window, causing the active window to jump and resize on every tab switch. There is no config option to set `tabbingMode = .disallowed`.

A workaround was attempted using Yabai signals to force BSP layout on each Ghostty window event, but it did not resolve the jumping behaviour:

```sh
yabai -m signal --add app='^Ghostty$' event=window_created action='yabai -m space --layout bsp'
yabai -m signal --add app='^Ghostty$' event=window_destroyed action='yabai -m space --layout bsp'
```

Revisit if AeroSpace (see **Trial**) proves able to handle native tab groups transparently.

### sccache

Rust compiler cache. Grows unboundedly on disk — even with `max_cache_size` set, the cache frequently bloats to tens of gigabytes across multiple projects and toolchain versions. The disk pressure outweighs the incremental build-time savings for typical dotfiles/personal project usage.

Revisit if Mozilla ships more aggressive eviction or if a per-project cache isolation story emerges.
