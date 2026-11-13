#!/usr/bin/env zsh
# Match tmux's directory/branch titles without taking over explicitly named tabs.

if [[ -n "$ZELLIJ" && -n "$ZELLIJ_SESSION_NAME" ]] &&
   (( $+commands[zellij-context] )) &&
   _zellij_title_context=$(command zellij-context title-context 2>/dev/null); then

	_zellij_auto_tab_title() {
		# Like tmux, preserve the editor's title when returning to the shell.
		if [[ "$_zellij_last_cmd" != nvim && "$_zellij_last_cmd" != vim ]]; then
			ZELLIJ_TITLE_CONTEXT="$_zellij_title_context" command zellij-auto-title --shell "$@" 2>/dev/null
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
