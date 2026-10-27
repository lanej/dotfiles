#!/bin/sh
# Preserve foreign destinations. Uninstall removes only our exact symlinks.
set -eu
action=$1
source_dir=$2
target_home=$3
if [ "$action" = install ] && ! command -v withenv >/dev/null 2>&1; then
    action=uninstall
fi
bin_target="$target_home/.local/bin/ep-direnv"
lib_target="$target_home/.config/direnv/lib/easypost_legacy.sh"
check_target() {
    if [ -e "$1" ] || [ -L "$1" ]; then
        [ -L "$1" ] && [ "$(readlink "$1")" = "$2" ] || {
            printf 'ep-direnv: preserving existing destination: %s\n' "$1" >&2
            return 1
        }
    fi
}
case "$action" in
    install)
        check_target "$bin_target" "$source_dir/bin/ep-direnv"
        check_target "$lib_target" "$source_dir/direnv/easypost_legacy.sh"
        mkdir -p "$(dirname "$bin_target")" "$(dirname "$lib_target")"
        [ -L "$bin_target" ] || ln -s "$source_dir/bin/ep-direnv" "$bin_target"
        [ -L "$lib_target" ] || ln -s "$source_dir/direnv/easypost_legacy.sh" "$lib_target"
        ;;
    uninstall)
        for target in "$bin_target" "$lib_target"; do
            case "$target" in
                "$bin_target") expected="$source_dir/bin/ep-direnv" ;;
                *) expected="$source_dir/direnv/easypost_legacy.sh" ;;
            esac
            if [ -L "$target" ] && [ "$(readlink "$target")" = "$expected" ]; then
                rm "$target"
            fi
        done
        ;;
    *) printf 'usage: install-ep-direnv.sh install|uninstall source-dir home\n' >&2; exit 1 ;;
esac
