#!/usr/bin/env zsh
# Match tmux's directory/branch titles without taking over explicitly named tabs.

if [[ -n "$ZELLIJ" && -n "$ZELLIJ_SESSION_NAME" ]] &&
   (( $+commands[zellij-auto-title] && $+commands[zellij-context] )) &&
   [[ $(command zellij-context provider 2>/dev/null) == zellij ]]; then

	_zellij_auto_tab_title() {
		# Like tmux, preserve the editor's title when returning to the shell.
		if [[ "$_zellij_last_cmd" != nvim && "$_zellij_last_cmd" != vim ]]; then
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
