#!/usr/bin/env bash
set -e

task=$1
dotfiles=$2
# NOTE: The checkout path is supplied by Make and may refer to a worktree.
# shellcheck source-path=SCRIPTDIR source=../../bootstrap.sh
source "$dotfiles/bootstrap.sh"
case "$task" in
    zellij-runtime)
        prepare_bootstrap_environment
        install_zellij_runtime
        ;;
    bedrock-router)
        prepare_bootstrap_environment
        setup_bedrock_router
        ;;
    kitty-terminfo) setup_kitty_terminfo ;;
    *) printf 'Unknown bootstrap task: %s\n' "$task" >&2; exit 1 ;;
esac
