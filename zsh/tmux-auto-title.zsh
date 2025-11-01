#!/usr/bin/env zsh
# Automatically set tmux window titles to directory name + git branch

# Auto-set tmux window title to match status bar format (dir [branch])
if [[ -n "$TMUX" ]]; then
	function _tmux_auto_window_title() {
		# Get current window name
		local current_window_name=$(tmux display-message -p '#W' 2>/dev/null)

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

		# Only update if:
		# 1. Window name is empty/default (like "zsh", "bash", etc.)
		# 2. Current window name looks like an auto-generated title
		# 3. Current window name contains git branch notation [...]
		if [[ -z "$current_window_name" ]] || \
		   [[ "$current_window_name" =~ ^(zsh|bash|sh)$ ]] || \
		   [[ "$current_window_name" =~ \[.*\] ]] || \
		   [[ "$current_window_name" =~ [~/] ]]; then
			# Set tmux window name
			tmux rename-window "$title" 2>/dev/null
		fi
	}

	# Add to precmd hooks
	autoload -Uz add-zsh-hook
	add-zsh-hook chpwd _tmux_auto_window_title
	add-zsh-hook precmd _tmux_auto_window_title
fi