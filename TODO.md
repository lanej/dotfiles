# Dotfiles TODO

## Keybind Management

**TODO: Create per-OS keybind mapping system**

Currently, keybinds are hardcoded in shell scripts and config files, which can cause conflicts across different operating systems and tools.

**The Problem:**
- macOS uses Alt/Option keys for yabai window management
- Linux may use different keybinds for window managers (i3, bspwm, etc)
- Terminal emulators interpret key combinations differently
- tmux, fzf, zsh, and vim all have their own keybind systems

**Proposed Solution:**
Create a centralized keybind mapping that:
1. Defines semantic actions (e.g., "narrow_filter", "preview_down", "accept")
2. Maps actions to OS-specific keys
3. Sources keybinds from a single config file
4. Generates bindings for different tools (fzf, tmux, vim, etc.)

**Example Structure:**
```bash
# ~/.config/keybinds/keybinds.conf
[macos]
narrow_filter = "ctrl-slash"
preview_down = "ctrl-j"
preview_up = "ctrl-k"

[linux]
narrow_filter = "alt-n"
preview_down = "ctrl-j"
preview_up = "ctrl-k"
```

**Current Conflicts:**
- Alt-N/Alt-P: Used by yabai on macOS (changed to Ctrl-/ for now)

**References:**
- zsh keybinds: `~/.files/sh/alias` (zz function)
- tmux keybinds: `~/.files/rc/tmux.conf`
- yabai keybinds: `~/.files/yabai/skhdrc`
