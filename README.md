```text
██╗      █████╗ ███╗   ██╗███████╗     ██╗
██║     ██╔══██╗████╗  ██║██╔════╝     ██║
██║     ███████║██╔██╗ ██║█████╗       ██║
██║     ██╔══██║██║╚██╗██║██╔══╝  ██   ██║
███████╗██║  ██║██║ ╚████║███████╗╚█████╔╝
╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝ ╚════╝

██████╗  ██████╗ ████████╗███████╗██╗██╗     ███████╗███████╗
██╔══██╗██╔═══██╗╚══██╔══╝██╔═══╝ ██║██║     ██╔════╝██╔════╝
██║  ██║██║   ██║   ██║   █████╗  ██║██║     █████╗  ███████╗
██║  ██║██║   ██║   ██║   ██╔══╝  ██║██║     ██╔══╝  ╚════██║
██████╔╝╚██████╔╝   ██║   ██║     ██║███████╗███████╗███████║
╚═════╝  ╚════╝    ╚═╝   ╚═╝     ╚═╝╚══════╝╚══════╝╚══════╝

```

Personal dotfiles managed via `make` + symlinks, cross-platform (macOS and Linux).

## Installation

```sh
$ git clone https://github.com/lanej/dotfiles.git ~/.files && cd ~/.files
$ make          # symlink configuration files
$ bash bootstrap.sh # install packages and tools
```

## Stack

| Tool | Description |
|---|---|
| [zsh](https://www.zsh.org/) | Shell with autosuggestions and syntax highlighting |
| [starship](https://starship.rs/) | Cross-shell prompt |
| [neovim](https://neovim.io/) | Editor (Lua config) |
| [tmux](https://github.com/tmux/tmux) | Terminal multiplexer |
| [kitty](https://sw.kovidgoyal.net/kitty/) | GPU-accelerated terminal |
| [fzf](https://github.com/junegunn/fzf) | Fuzzy finder |
| [skim](https://github.com/skim-rs/skim) | Rust-native fuzzy finder |

See [docs/stack-darwin.md](docs/stack-darwin.md) and [docs/stack-linux.md](docs/stack-linux.md) for platform-specific tools.

## Key Makefile Targets

| Target | Description |
|---|---|
| `make` | Symlink all configuration files |
| `make claude` | Set up Claude commands/agents symlinks |
| `make opencode` | Generate `~/.config/opencode/opencode.json` |
| `make git` | Symlink git configuration |
| `make tmux` | Symlink tmux configuration |
| `make zsh` | Symlink zsh configuration |
| `make cargo` | Symlink Cargo/Rust configuration |

## Directory Layout

```
~/.files/
├── nvim/          # Neovim config (Lua)
├── zsh/           # Zsh config and plugins
├── git/           # Git config and global gitignore
├── kitty/         # Kitty terminal config
├── ghostty/       # Ghostty terminal config (not default; see docs/why-not.md)
├── tmux/          # Tmux config
├── yabai/         # macOS tiling WM config
├── claude/        # Claude commands and agents (selectively versioned)
├── bin/           # Utility scripts (selectively versioned)
├── bootstrap/     # Bootstrap helpers
├── docs/          # Tool-specific notes and decision rationale
└── Makefile       # Symlink and setup targets
```

## Machine Migration

```sh
$ sh transfer.sh
```

---

See [docs/](docs/) for tool-specific notes and decision rationale.
