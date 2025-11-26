# claude-tail Dotfiles

Custom themes for [claude-tail](https://github.com/yourusername/claude-tail), a colorful log viewer for Claude Code sessions.

## Themes

### Nord Theme
- **File**: `themes/Nord.tmTheme`
- **Source**: [Nord Sublime Text (Community Port)](https://github.com/fjlaubscher/Nord-Sublime-Text)
- **Colors**: Arctic, north-bluish clean and elegant palette
  - Polar Night (backgrounds): #2e3440, #3b4252, #434c5e, #4c566a
  - Snow Storm (foregrounds): #d8dee9, #e5e9f0, #eceff4
  - Frost (blues): #8fbcbb, #88c0d0, #81a1c1, #5e81ac
  - Aurora (accents): #bf616a, #d08770, #ebcb8b, #a3be8c, #b48ead

## Installation

The claude-tail project should symlink to these themes:

```bash
ln -s ~/.files/claude-tail/themes/Nord.tmTheme ~/src/claude-tail/themes/Nord.tmTheme
```

This allows the theme to be:
- Backed up with dotfiles
- Version controlled
- Shared across claude-tail installations
