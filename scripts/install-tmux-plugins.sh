#!/usr/bin/env bash
set -euo pipefail

dotfiles=$1
tpm="$HOME/.tmux/plugins/tpm"
[[ -d $tpm ]] || git clone --depth=1 https://github.com/tmux-plugins/tpm "$tpm"
[[ -x $tpm/bin/install_plugins ]] || {
    printf 'TPM installer is missing or not executable: %s/bin/install_plugins\n' "$tpm" >&2
    exit 1
}

# Only clean up the session created by this invocation; leave user sessions alone.
session="__tpm_bootstrap_$$"
created=0
cleanup() {
    if ((created)); then
        tmux kill-session -t "$session" 2>/dev/null || true
    fi
}
trap cleanup EXIT
if ! tmux list-sessions >/dev/null 2>&1; then
    tmux new-session -d -s "$session"
    created=1
fi
if "$tpm/bin/install_plugins"; then
    :
else
    status=$?
    printf 'TPM installation failed; existing plugin directories were preserved.\n' >&2
    exit "$status"
fi
mkdir -p "$HOME/.config/tmux/plugins/tmux-resurrect/strategies"
ln -fs "$dotfiles/bin/tmux-resurrect-claude" "$HOME/.config/tmux/plugins/tmux-resurrect/strategies/claude.sh"
