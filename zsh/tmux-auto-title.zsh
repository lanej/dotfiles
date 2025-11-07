#!/usr/bin/env zsh
# Automatically set tmux window titles to directory name + git branch
# Fixed version with proper race condition handling (macOS compatible)

if [[ -n "$TMUX" ]]; then
	# Lock directory for preventing concurrent updates
	TMUX_TITLE_LOCK_DIR="${TMPDIR:-/tmp}/tmux-auto-title-locks"
	mkdir -p "$TMUX_TITLE_LOCK_DIR"

	# Portable lock acquire function (works on macOS and Linux)
	_acquire_lock() {
		local lock_dir="$1"
		local max_wait="$2"
		local waited=0

		# Try to create lock directory atomically
		while ! mkdir "$lock_dir" 2>/dev/null; do
			# Lock exists, check if it's stale (older than 5 seconds)
			if [[ -d "$lock_dir" ]]; then
				local lock_age=$(($(date +%s) - $(stat -f %m "$lock_dir" 2>/dev/null || stat -c %Y "$lock_dir" 2>/dev/null)))
				if [[ $lock_age -gt 5 ]]; then
					# Stale lock, remove it
					rmdir "$lock_dir" 2>/dev/null
					continue
				fi
			fi

			# Wait a bit and retry
			if (( waited >= max_wait )); then
				return 1
			fi
			sleep 0.01
			waited=$((waited + 10))
		done
		return 0
	}

	# Release lock
	_release_lock() {
		local lock_dir="$1"
		rmdir "$lock_dir" 2>/dev/null
	}

	function _tmux_auto_window_title() {
		# Get window index early - we'll use this for locking
		local window_index=$(tmux display-message -p '#{window_index}' 2>/dev/null) || return
		local lock_dir="$TMUX_TITLE_LOCK_DIR/window-${window_index}.lock"

		# Try to acquire lock with 100ms timeout
		if ! _acquire_lock "$lock_dir" 100; then
			# Another update is in progress, skip this one
			return
		fi

		# Ensure we release the lock on exit
		trap "_release_lock '$lock_dir'" EXIT INT TERM

		# Double-check pane is still active after acquiring lock
		local is_active=$(tmux display-message -p '#{pane_active}' 2>/dev/null)
		if [[ "$is_active" != "1" ]]; then
			_release_lock "$lock_dir"
			return
		fi

		# Verify window index hasn't changed
		local current_window=$(tmux display-message -p '#{window_index}' 2>/dev/null)
		if [[ "$current_window" != "$window_index" ]]; then
			_release_lock "$lock_dir"
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

		# Final check before renaming - ensure we're still in the right window
		is_active=$(tmux display-message -p '#{pane_active}' 2>/dev/null)
		current_window=$(tmux display-message -p '#{window_index}' 2>/dev/null)

		if [[ "$is_active" == "1" ]] && [[ "$current_window" == "$window_index" ]]; then
			# Use -t to target specific window, not current
			tmux rename-window -t ":$window_index" "$title" 2>/dev/null
		fi

		_release_lock "$lock_dir"
	}

	# Debounced version using async job control
	# This prevents rapid-fire updates when switching windows quickly
	typeset -g _tmux_title_update_pending=0

	function _tmux_auto_window_title_debounced() {
		# If an update is already pending, don't schedule another
		if (( _tmux_title_update_pending )); then
			return
		fi

		_tmux_title_update_pending=1

		# Schedule the actual update to run after a short delay
		# This coalesces multiple rapid calls into a single update
		{
			sleep 0.05
			_tmux_auto_window_title
			_tmux_title_update_pending=0
		} &!
	}

	# Add to precmd hooks - use debounced version
	autoload -Uz add-zsh-hook
	add-zsh-hook chpwd _tmux_auto_window_title_debounced
	add-zsh-hook precmd _tmux_auto_window_title_debounced
fi
