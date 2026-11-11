#!/usr/bin/env bash
set -eu

dotfiles=$1
shellcheck -x \
    "$dotfiles"/scripts/make/*.sh \
    "$dotfiles/bootstrap.sh" \
    "$dotfiles/install.sh" \
    "$dotfiles/claude/evals/skill-maintenance/check_size.sh" \
    "$dotfiles/scripts/setup-checklist.sh" \
    "$dotfiles/ai/skills/go/assets/check-go.sh" \
    "$dotfiles/scripts/install-tmux-plugins.sh" \
    "$dotfiles/scripts/install-ep-direnv.sh" \
    "$dotfiles/scripts/install-agent-status-broker" \
    "$dotfiles/scripts/install-zellij" \
    "$dotfiles/scripts/install-treehouse" \
    "$dotfiles/scripts/build-git-worktree-hooks.sh" \
    "$dotfiles/bin/ac-awake-service" \
    "$dotfiles/bin/paseo-pi" \
    "$dotfiles/bin/fix-ssh" \
    "$dotfiles/bin/fzf-path-preview" \
    "$dotfiles/bin/git-ssh" \
    "$dotfiles/bin/git-worktree-policy-hook" \
    "$dotfiles/bin/dotfiles-fzf" \
    "$dotfiles/bin/sync-codex-mcp-servers"
