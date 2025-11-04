#!/usr/bin/env zsh
# Automatically set tmux window titles to directory name + git branch

# Auto-set tmux window title to match status bar format (dir [branch])
if [[ -n "$TMUX" ]]; then
	function _tmux_auto_window_title() {
		# Only update if this pane is active
		local is_active=$(tmux display-message -p '#{pane_active}' 2>/dev/null)
		if [[ "$is_active" != "1" ]]; then
			return
		fi

		# Get the window index for this pane
		local window_index=$(tmux display-message -p '#{window_index}' 2>/dev/null)

		# DEBUG: Log window index being updated (temporary)
		# Uncomment to debug: echo "DEBUG: Updating window $window_index" >> /tmp/tmux-title-debug.log

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

		# Explicitly target this pane's window to avoid race conditions
		# when switching windows quickly
		# Use :index syntax to target specific window
		tmux rename-window -t ":$window_index" "$title" 2>/dev/null
	}

	# Add to precmd hooks
	autoload -Uz add-zsh-hook
	add-zsh-hook chpwd _tmux_auto_window_title
	add-zsh-hook precmd _tmux_auto_window_title
fi