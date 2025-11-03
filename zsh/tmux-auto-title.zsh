#!/usr/bin/env zsh
# Automatically set tmux window titles to directory name + git branch

# Auto-set tmux window title to match status bar format (dir [branch])
if [[ -n "$TMUX" ]]; then
	function _tmux_auto_window_title() {
		# Get directory name
		local dir_name=$(basename "$PWD")

		# Check if we're in a git repository and get the branch
		local title="$dir_name"
		if git rev-parse --git-dir >/dev/null 2>&1; then
			local branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
			if [[ -n "$branch" ]]; then
				title="$dir_name [$branch]"
			fi
		fi

		# Always set the window name to current directory
		# This will be overridden by applications like nvim when they start
		tmux rename-window "$title" 2>/dev/null
	}

	# Add to precmd hooks
	autoload -Uz add-zsh-hook
	add-zsh-hook chpwd _tmux_auto_window_title
	add-zsh-hook precmd _tmux_auto_window_title
fi