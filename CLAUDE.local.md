# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation and Setup
- `make` - Install configuration files by creating symbolic links from dotfiles to home directory
- `bash bootstrap.sh` - Install packages and dependencies for the development environment
- `sh transfer.sh` - Transfer configuration (see README for details)

### Building and Linting
This repository doesn't have traditional build/test commands as it's a dotfiles configuration repository. However, for development workflow:
- `make <target>` - Install specific configuration sets (e.g., `make zsh`, `make nvim`, `make git`)
- `bash bootstrap.sh` - Reinstall all dependencies with version checking

## Architecture and Structure

This is a comprehensive dotfiles repository that manages development environment configuration across multiple platforms (macOS and Linux). The architecture is organized by tool/application:

### Core Structure
- **Makefile**: Central configuration manager that creates symbolic links from dotfiles to proper locations
- **bootstrap.sh**: Dependency installer with version management for development tools
- **Platform-specific configs**: Separate directories for different tools and environments

### Key Configuration Areas

#### Shell Environment
- **zsh/**: ZSH shell configuration with history, autosuggestions, and syntax highlighting
- **bash/**: Bash configuration files (bashrc, bashprofile, bashenv)
- **sh/**: Shared shell utilities (aliases, profile, starship prompt, atuin history)

#### Editors and Development Tools
- **nvim/**: Neovim configuration with Lua-based setup and plugin management
- **vim/**: Vim configuration and session management
- **git/**: Git configuration (gitconfig, gitignore, gitattributes)

#### Terminal and UI
- **kitty/**: Kitty terminal emulator configuration
- **alacritty/**: Alacritty terminal configuration
- **tmux/**: Terminal multiplexer configuration (rc/tmux.conf)
- **yabai/**: macOS tiling window manager with skhd hotkeys and borders
- **polybar/**: Linux status bar configuration
- **bspwm/**: Linux window manager configuration

#### Language-Specific Tools
- **ruby/**: Ruby development environment (irbrc, pryrc, gemrc, rspec)
- **python/**: Python code style configuration
- **go/**: Go environment configuration

### Package Management Strategy
The bootstrap.sh script implements sophisticated version management:
- Supports multiple package managers (brew, yay, pacman, dnf, apt-get)
- Fallback to source/release installation for specific versions
- Cargo-based Rust tool installation
- Custom installation functions for language servers and development tools

### Platform Support
- **macOS**: Uses yabai for window management, homebrew for packages
- **Linux**: Supports Arch (yay/pacman), Ubuntu (apt-get), CentOS (dnf) with bspwm/polybar

## Workflow Integration
- Configurations are linked, not copied, allowing easy version control
- Bootstrap script checks versions before installing to avoid unnecessary updates  
- Modular Makefile targets allow installing specific tool configurations independently

## Git Workflow Guidelines
- Don't mention claude when writing git commit messages and use the commitzen format with the appropriate line lengths