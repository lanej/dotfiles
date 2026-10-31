#!/usr/bin/env bash
set -eu

dotfiles=$1
shellcheck -x \
    "$dotfiles"/scripts/make/*.sh \
    "$dotfiles/bootstrap.sh" \
    "$dotfiles/claude/evals/skill-maintenance/check_size.sh" \
    "$dotfiles/scripts/setup-checklist.sh" \
    "$dotfiles/scripts/install-tmux-plugins.sh" \
    "$dotfiles/scripts/install-ep-direnv.sh" \
    "$dotfiles/scripts/install-agent-status-broker" \
    "$dotfiles/bin/ac-awake-service" \
    "$dotfiles/bin/sync-codex-mcp-servers"
