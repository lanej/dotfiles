#!/usr/bin/env zsh
# Match tmux's directory/branch titles without taking over explicitly named tabs.

if [[ -n "$ZELLIJ" && -n "$ZELLIJ_SESSION_NAME" ]] &&
   (( $+commands[zellij-context] )) &&
   [[ $(command zellij-context provider 2>/dev/null) == zellij ]]; then

	_zellij_auto_title() {
		# Redirected shell output must not leak terminal control sequences.
		[[ -t 1 ]] || return 0
		local title=${PWD:t} branch
		[[ -n $title ]] || title=/
		if git rev-parse --git-dir >/dev/null 2>&1; then
			branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
			[[ -z $branch ]] || title+=" [$branch]"
		fi
		# Directory names can contain BEL/ESC/newlines. Keep them title data.
		title=${title//[[:cntrl:]]/ }
		printf '\e]2;%s\a' "$title"
	}

	_zellij_auto_tab_title() {
		# Like tmux, preserve the editor's title when returning to the shell.
		if [[ "$_zellij_last_cmd" != nvim && "$_zellij_last_cmd" != vim ]]; then
			_zellij_auto_title
			command zellij-auto-title >/dev/null 2>&1
		fi
		return 0
	}

	_zellij_title_precmd() {
		_zellij_auto_tab_title
		_zellij_last_cmd=""
	}

	_zellij_title_preexec() {
		_zellij_last_cmd="${1%% *}"
	}

	typeset -g _zellij_last_cmd=""
	autoload -Uz add-zsh-hook
	add-zsh-hook chpwd _zellij_auto_tab_title
	add-zsh-hook precmd _zellij_title_precmd
	add-zsh-hook preexec _zellij_title_preexec
fi
