#!/usr/bin/env bash
# Initialize a machine configuration without requiring the TOML runtime.
set -euo pipefail

setup_home=$1
native_set=$2
config_home=${XDG_CONFIG_HOME-"$setup_home/.config"}
config_file=${DOTFILES_CONFIG-"$config_home/dotfiles/config.toml"}
case "$config_file" in
    \~) config_file=$setup_home ;;
    \~/*) config_file=$setup_home/${config_file:2} ;;
    \~*) printf 'Use an absolute DOTFILES_CONFIG path for another user home.\n' >&2; exit 1 ;;
esac

# Preserve user choices and existing links, including dangling symlinks.
if [[ -e "$config_file" || -L "$config_file" ]]; then
    exit 0
fi
mkdir -p "$(dirname "$config_file")"
# Also prevent replacement if another process creates the file after the check.
set -o noclobber
printf '# Add tool and work-context sets alongside this native baseline.\nsets = ["%s"]\n' \
    "$native_set" > "$config_file"
printf 'Initialized dotfiles configuration: %s\n' "$config_file"
