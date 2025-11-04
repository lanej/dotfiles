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

		# Only set the window name if this is the active pane
		# This prevents inactive panes from overwriting the title
		tmux rename-window "$title" 2>/dev/null
	}

	# Add to precmd hooks
	autoload -Uz add-zsh-hook
	add-zsh-hook chpwd _tmux_auto_window_title
	add-zsh-hook precmd _tmux_auto_window_title
fi