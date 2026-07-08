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
				local lock_mtime
				lock_mtime=$(stat -f %m "$lock_dir" 2>/dev/null || stat -c %Y "$lock_dir" 2>/dev/null)
				if [[ -z "$lock_mtime" ]]; then
					# Lock dir vanished between the -d check and stat (race with
					# another shell's cleanup) -- just retry
					continue
				fi
				local lock_age=$(( $(date +%s) - lock_mtime ))
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

		# If Claude named this window, re-apply its title and leave it alone
		local claude_name
		claude_name=$(tmux show-options -w -v @claude_named 2>/dev/null)
		if [[ -n "$claude_name" ]]; then
			tmux rename-window -t ":$window_index" "$claude_name" 2>/dev/null
			_release_lock "$lock_dir"
			return
		fi

		# If we just returned from nvim/vim, preserve the window name
		if [[ "$_tmux_last_cmd" == "nvim" || "$_tmux_last_cmd" == "vim" ]]; then
			_release_lock "$lock_dir"
			return
		fi

		# Only rename if we own this window's title or it's still the shell default.
		# @auto_titled_name stores the last title we set. If the current name no longer
		# matches it, something else renamed the window — leave it alone.
		local current_name
		current_name=$(tmux display-message -p '#{window_name}' 2>/dev/null)
		local auto_titled_name
		auto_titled_name=$(tmux show-options -w -v @auto_titled_name 2>/dev/null)

		if [[ -n "$auto_titled_name" && "$current_name" != "$auto_titled_name" ]]; then
			# Another tool renamed this window since we last set it
			_release_lock "$lock_dir"
			return
		fi

		if [[ -z "$auto_titled_name" && "$current_name" != "zsh" && "$current_name" != "bash" && "$current_name" != "sh" ]]; then
			# We've never named this window and it's not the shell default
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
			tmux rename-window -t ":$window_index" "$title" 2>/dev/null
			tmux set-option -w @auto_titled_name "$title" 2>/dev/null
		fi

		_release_lock "$lock_dir"
	}

	typeset -g _tmux_last_cmd=""

	function _tmux_on_preexec() {
		_tmux_last_cmd="${1%% *}"
		tmux set-option -w -u @claude_named 2>/dev/null
	}

	autoload -Uz add-zsh-hook
	add-zsh-hook chpwd _tmux_auto_window_title
	add-zsh-hook precmd _tmux_auto_window_title
	add-zsh-hook preexec _tmux_on_preexec
fi
