#!/usr/bin/env bash
set -eu

dotfiles=$1
preferences=$2
if [ "$3" != Darwin ]; then
    echo "MenuBar Stats settings require macOS." >&2
    exit 1
fi
status=0
pgrep -x "MenuBar Stats" >/dev/null || status=$?
if [ "$status" -eq 0 ]; then
    echo "Quit MenuBar Stats before restoring its settings." >&2
    exit 1
elif [ "$status" -ne 1 ]; then
    exit "$status"
fi
python3 "$dotfiles/scripts/restore-menubar-stats.py" "$dotfiles/menubar-stats/settings.plist" "$preferences"
