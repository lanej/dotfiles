#!/usr/bin/env bash
set -eu

dotfiles=$1
shellcheck -x \
    "$dotfiles"/scripts/make/*.sh \
    "$dotfiles/bootstrap.sh" \
    "$dotfiles/install.sh" \
    "$dotfiles/claude/evals/skill-maintenance/check_size.sh" \
    "$dotfiles/scripts/setup-checklist.sh" \
    "$dotfiles/scripts/firstmate-feedback-native.sh" \
    "$dotfiles/ai/skills/go/assets/check-go.sh" \
    "$dotfiles/scripts/install-tmux-plugins.sh" \
    "$dotfiles/scripts/install-ep-direnv.sh" \
    "$dotfiles/scripts/install-agent-status-broker" \
    "$dotfiles/scripts/install-zellij" \
    "$dotfiles/bin/ac-awake-service" \
    "$dotfiles/bin/firstmate" \
    "$dotfiles/bin/paseo-pi" \
    "$dotfiles/bin/zellij-attach" \
    "$dotfiles/bin/zellij-agent" \
    "$dotfiles/bin/zellij-balance" \
    "$dotfiles/bin/fix-ssh" \
    "$dotfiles/bin/git-ssh" \
    "$dotfiles/bin/dotfiles-fzf" \
    "$dotfiles/bin/sync-codex-mcp-servers"
