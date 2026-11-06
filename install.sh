#!/bin/sh
# Downloadable entrypoint: clone once, then use the checkout's existing bootstrap.
# Keep effects inside a complete function so a truncated download cannot start setup.
install_dotfiles() (
    set -eu
    if [ "$#" -ne 0 ]; then
        printf 'Usage: curl -fsSL <install.sh URL> | sh\n' >&2
        exit 2
    fi
    case "$(uname -s)" in
        Darwin|Linux) ;;
        *) printf 'Dotfiles supports macOS and Linux.\n' >&2; exit 1 ;;
    esac
    for dependency in git make bash; do
        if ! command -v "$dependency" >/dev/null 2>&1; then
            printf 'Install %s before running dotfiles setup.\n' "$dependency" >&2
            exit 1
        fi
    done
    : "${HOME:?HOME must point to your home directory}"
    checkout=$HOME/.files
    repository=https://github.com/lanej/dotfiles.git
    if [ -e "$checkout" ] || [ -L "$checkout" ]; then
        if [ ! -d "$checkout/.git" ] && [ ! -f "$checkout/.git" ]; then
            printf 'Refusing to replace %s: it is not a Git checkout.\n' "$checkout" >&2
            exit 1
        fi
        checkout_root=$(cd "$checkout" && pwd -P)
        git_root=$(git -C "$checkout" rev-parse --show-toplevel)
        if [ "$checkout_root" != "$(cd "$git_root" && pwd -P)" ]; then
            printf 'Refusing to run setup from a different repository root.\n' >&2
            exit 1
        fi
        origin=$(git -C "$checkout" config --get remote.origin.url)
        case "$origin" in
            https://github.com/lanej/dotfiles|https://github.com/lanej/dotfiles.git|git@github.com:lanej/dotfiles|git@github.com:lanej/dotfiles.git|ssh://git@github.com/lanej/dotfiles|ssh://git@github.com/lanej/dotfiles.git) ;;
            *) printf 'Refusing to run setup: %s is not a lanej/dotfiles checkout.\n' "$checkout" >&2; exit 1 ;;
        esac
        printf 'Using existing checkout at %s without pulling or switching branches.\n' "$checkout"
    else
        git clone -- "$repository" "$checkout"
    fi
    if [ ! -f "$checkout/Makefile" ] || [ ! -f "$checkout/bootstrap.sh" ]; then
        printf 'The checkout is missing its Makefile or bootstrap.sh.\n' >&2
        exit 1
    fi
    # Children must not consume unread script bytes from the curl pipe.
    make -C "$checkout" bootstrap </dev/null
    printf '\nNative configuration and Python bootstrap complete.\n'
    printf 'Choose tool sets in %s, then run:\n' "${DOTFILES_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/dotfiles/config.toml}"
    printf "  cd \"\$HOME/.files\" && make plan\n  cd \"\$HOME/.files\" && make install\n"
)
install_dotfiles "$@"
