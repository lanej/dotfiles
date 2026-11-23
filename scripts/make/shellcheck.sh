#!/usr/bin/env bash
set -eu

dotfiles=$1
shellcheck -x \
	"$dotfiles"/scripts/make/*.sh \
	"$dotfiles/.github/scripts/install-file-selection-tools.sh" \
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
	"$dotfiles/scripts/install-worktree-policy" \
	"$dotfiles/scripts/install-pi" \
	"$dotfiles/scripts/install-worktree-manager" \
	"$dotfiles/scripts/install-shfmt.sh" \
	"$dotfiles/scripts/build-worktree-policy.sh" \
	"$dotfiles/tools/worktree-policy/scripts/check-go.sh" \
	"$dotfiles/scripts/lib/git-worktree-runtime.sh" \
	"$dotfiles/scripts/pull-git-worktree-source.sh" \
	"$dotfiles/scripts/install-git-worktree-hooks.sh" \
	"$dotfiles/scripts/extract-git-runtime.sh" \
	"$dotfiles/scripts/test-install-git-worktree-hooks.sh" \
	"$dotfiles/scripts/worktree-manager-update.sh" \
	"$dotfiles/scripts/build-git-worktree-hooks.sh" \
	"$dotfiles/bin/ac-awake-service" \
	"$dotfiles/bin/paseo-pi" \
	"$dotfiles/bin/pi-driver" \
	"$dotfiles/bin/fix-ssh" \
	"$dotfiles/bin/zellij-image-hints" \
	"$dotfiles/scripts/build-zellij-helpers.sh" \
	"$dotfiles/sh/ssh-rc" \
	"$dotfiles/bin/fzf-path-preview" \
	"$dotfiles/bin/git-ssh" \
	"$dotfiles/bin/git-worktree-policy-hook" \
	"$dotfiles/bin/git-worktree-policy" \
	"$dotfiles/bin/dotfiles-fzf" \
	"$dotfiles/bin/sync-codex-mcp-servers"
