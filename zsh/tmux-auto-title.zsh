#!/usr/bin/env zsh
# Automatically set tmux window titles to shortened directory paths

# Auto-set tmux window title to shortened directory path
if [[ -n "$TMUX" ]]; then
	function _tmux_auto_window_title() {
		# Get current window name
		local current_window_name=$(tmux display-message -p '#W' 2>/dev/null)
		
		# Get current directory and replace $HOME with ~
		local current_dir="${PWD/#$HOME/~}"
		
		# Generate what the shortened path should be
		local shortened_dir=""
		
		# Handle special case: if we're exactly at home directory
		if [[ "$current_dir" == "~" ]]; then
			shortened_dir="~"
		elif [[ ${#current_dir} -le 32 ]]; then
			# If path is 32 characters or less, don't shorten it
			shortened_dir="$current_dir"
		else
			# Shorten path: keep last 2 components full, abbreviate others
			local parts
			IFS='/' read -rA parts <<< "$current_dir"
			local num_parts=${#parts[@]}
			
			# Filter out empty parts
			local filtered_parts=()
			for part in "${parts[@]}"; do
				if [[ -n "$part" ]]; then
					filtered_parts+=("$part")
				fi
			done
			parts=("${filtered_parts[@]}")
			num_parts=${#parts[@]}
			
			for ((i=0; i<num_parts; i++)); do
				if [[ "${parts[i]}" == "~" ]]; then
					# Keep ~ as is
					shortened_dir="~"
				elif [[ $i -lt $((num_parts - 2)) ]]; then
					# Abbreviate components, using more chars for common names
					local abbrev="${parts[i]:0:1}"
					
					# Use 3 chars for common directory names that often have siblings
					# or when the name starts with common prefixes
					if [[ "${parts[i]}" =~ ^(src|lib|bin|usr|var|opt|tmp|dev|prod|test|spec|docs?|dist|build|node|config|public|private|client|server|backend|frontend|components?|packages?|modules?) ]]; then
						abbrev="${parts[i]:0:3}"
					elif [[ "${parts[i]}" =~ ^(com|org|net|edu|gov) ]]; then
						# Common domain-style prefixes
						abbrev="${parts[i]:0:3}"
					elif [[ ${#parts[i]} -ge 8 ]]; then
						# For longer directory names, use 2 chars for better uniqueness
						abbrev="${parts[i]:0:2}"
					fi
					
					if [[ -n "$shortened_dir" ]]; then
						shortened_dir="${shortened_dir}/${abbrev}"
					else
						shortened_dir="${abbrev}"
					fi
				else
					# Keep last 2 components full
					if [[ -n "$shortened_dir" ]]; then
						shortened_dir="${shortened_dir}/${parts[i]}"
					else
						shortened_dir="${parts[i]}"
					fi
				fi
			done
			
			# Fallback in case shortened_dir is still empty
			if [[ -z "$shortened_dir" ]]; then
				shortened_dir="$current_dir"
			fi
		fi
		
		# Only update if:
		# 1. Window name is empty/default (like "zsh", "bash", etc.)
		# 2. Current window name looks like a path (contains ~ or /)
		# 3. Current window name matches pattern of shortened paths (like ~/s/d/foo/bar)
		if [[ -z "$current_window_name" ]] || \
		   [[ "$current_window_name" =~ ^(zsh|bash|sh)$ ]] || \
		   [[ "$current_window_name" =~ [~/] ]] || \
		   [[ "$current_window_name" =~ ^~(/[^/])*(/[^/]+){0,2}$ ]]; then
			# Set tmux window name
			tmux rename-window "$shortened_dir" 2>/dev/null
		fi
	}
	
	# Add to precmd hooks
	autoload -Uz add-zsh-hook
	add-zsh-hook chpwd _tmux_auto_window_title
	add-zsh-hook precmd _tmux_auto_window_title
fi