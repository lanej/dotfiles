#!/usr/bin/env bash
set -eu

dotfiles=$1
preferences=$2
if [ "$3" != Darwin ]; then
    echo "Amphetamine settings require macOS." >&2
    exit 1
fi
status=0
pgrep -x Amphetamine >/dev/null || status=$?
if [ "$status" -eq 0 ]; then
    echo "Quit Amphetamine before restoring its settings." >&2
    exit 1
elif [ "$status" -ne 1 ]; then
    exit "$status"
fi
plutil -lint "$dotfiles/amphetamine/settings.plist" >/dev/null
defaults write "$preferences" "Trigger Data" "$(plutil -extract 'Trigger Data' xml1 -o - "$dotfiles/amphetamine/settings.plist")"
defaults write "$preferences" "Enable Triggers" -bool "$(plutil -extract 'Enable Triggers' raw -o - "$dotfiles/amphetamine/settings.plist")"
echo "Amphetamine trigger settings restored. Reopen Amphetamine."
