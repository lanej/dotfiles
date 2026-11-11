# Tech Radar

Tool and technology decisions, organized by ring.

| Ring | Meaning |
|---|---|
| **Adopt** | In active use; recommended |
| **Trial** | Being evaluated; promising enough to run in real workflows |
| **Assess** | Worth watching; not yet trialed |
| **Hold** | Not adopted; rationale documented |

<!-- Entry conventions: use a ### heading under the current ring, explain the tool and
placement briefly, link related entries where useful, and state any revisit condition.
Update only the requested decisions; preserve unrelated entries. -->

---

## Adopt

### Kitty

Terminal emulator. Implements tabs entirely within a single OS window — yabai sees exactly one window per Kitty instance, so tiling and focus work correctly.

### yabai

Tiling window manager via the macOS Accessibility API. Manages all windows at the OS level.

---

## Trial

### Mergiraf

[Mergiraf](mergiraf.md): selected by the `shell` set, with a machine-level `tools.mergiraf = false` opt-out. Installation activates syntax-aware Git merging for its supported file types. Runnable TOML, Lua, and JSON examples demonstrate combined independent edits and retained disagreements. Revisit the trial after reviewing resolutions during normal branch integration; Zsh remains outside the installed binary's advertised language coverage.

### Pi

[Pi](pi.md): an opt-in composable agent runtime that reuses the existing shared skills, Builder guidance, and role instructions. Start with bounded workflows and keep the established coding clients available. Revisit adoption after exercising supervision, review results, and status reporting in normal work.
### Zellij

[Zellij](zellij.md): an opt-in terminal multiplexer trial with tmux-style bindings and a compact layout in Kitty. Bootstrap installs version 0.45.1 or newer; `zj main` attaches to or creates a named session. Tmux remains available for existing agent-status integrations.

Revisit adoption after validating long-running sessions, scrollback-heavy workloads, and the documented integration gaps.

### Viewrule

[Viewrule](ui-review.md): my tool for rendered UI checks, screenshot references, and a feedback-to-rule workflow. Trial task-specific density rules against actual rejected and accepted screens before promoting them globally.


---

## Assess

### AeroSpace

[AeroSpace](https://github.com/nikitabobko/AeroSpace) is a tiling WM that operates at the app level rather than hooking into the macOS window server. It may handle Ghostty's native `NSWindowTabGroup` tab grouping without the window-jumping issue that currently blocks a Ghostty migration (see **Hold: Ghostty**).

---

## Hold

### Firstmate through Paseo and GitHub

[Firstmate mobile workflow](firstmate-mobile.md): former mobile coordination workflow through Paseo, Pi, and GitHub. Retired from my workflow; no longer being evaluated.

### Superpowers

Claude Code workflow plugin. Removed from the shared settings at the owner's
request in favor of the remaining official plugins and custom skills. Skill
maintenance uses the official Anthropic skill-creator workflow.

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

Revisit if AeroSpace (see **Assess**) proves able to handle native tab groups transparently.

### andrej-karpathy-skills

A Claude Code plugin packaging four behavioral principles (think before coding, simplicity, surgical edits, goal-driven execution) attributed to Karpathy's coding agent guidelines. Evaluated and skipped — the global CLAUDE.md already covers all four principles, often more precisely and with harder edges. No executable tooling, MCP servers, or commands; purely policy text.

### sccache

Rust compiler cache. Grows unboundedly on disk — even with `max_cache_size` set, the cache frequently bloats to tens of gigabytes across multiple projects and toolchain versions. The disk pressure outweighs the incremental build-time savings for typical dotfiles/personal project usage.

Revisit if Mozilla ships more aggressive eviction or if a per-project cache isolation story emerges.
