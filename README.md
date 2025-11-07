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

# Installation

```sh
$ git clone https://github.com/lanej/dotfiles.git ~/.files && cd ~/.files
$ make # install configuration files
$ bash bootstrap.sh # install packages
```

## Transfer

```sh
$ sh transfer.sh
```

# Stack

* [kitty](https://sw.kovidgoyal.net/kitty/)
* [tmux](https://github.com/tmux/tmux)
* [neovim](https://neovim.io/)
* [fzf](https://github.com/junegunn/fzf)
* [skim](https://github.com/skim-rs/skim)

## Linux

Arch, Ubuntu, CentOS 8

* [bspwm](https://github.com/baskerville/bspwm)
* [polybar](https://github.com/polybar/polybar)
* [rofi](https://github.com/davatorium/rofi)

## Darwin

* [yabai](https://github.com/koekeishiya/yabai)
* [Menubar Stats](https://seense.com/menubarstats/)

## Rust Development

Disk space management for Rust projects:

**Configuration:**
- `sccache` enabled in `~/.cargo/config.toml` for shared compilation caching
- Optimized debug builds with reduced debug info (`debug = 1`)
- Split debug info on macOS to reduce binary sizes

**Cleanup Aliases:**
```sh
cargo-clean-all      # Remove ALL target/ directories
cargo-clean-debug    # Remove only debug builds, keep release
cargo-clean-old      # Clean builds older than 30 days
cargo-cache-clean    # Clean ~/.cargo cache
rust-disk           # Show top 20 largest target dirs
sccache-stats       # Show sccache hit/miss stats
```

**Maintenance:**
- Run `cargo-clean-debug` monthly
- Use `cargo-clean-old` for automatic cleanup
- Check `sccache-stats` to monitor cache effectiveness
