# Prompt-only navigation: foreground programs keep their own Ctrl-h/j/k/l.
# Select the actual owner in either nesting direction; outer variables survive.
if [[ -n $ZELLIJ && -n $ZELLIJ_PANE_ID ]] &&
   (( $+commands[zellij-navigate] && $+commands[zellij-context] )) &&
   [[ $(command zellij-context provider 2>/dev/null) == zellij ]]; then
	_zellij_navigate() {
		local direction=${WIDGET#zellij-}
		local message
		if ! message=$(command zellij-navigate "$direction" 2>&1); then
			zle -M "$message"
		fi
	}
	zle -N zellij-left _zellij_navigate
	zle -N zellij-down _zellij_navigate
	zle -N zellij-up _zellij_navigate
	zle -N zellij-right _zellij_navigate
	for _zellij_keymap in viins vicmd emacs; do
		bindkey -M "$_zellij_keymap" '^H' zellij-left
		bindkey -M "$_zellij_keymap" '^J' zellij-down
		bindkey -M "$_zellij_keymap" '^K' zellij-up
		bindkey -M "$_zellij_keymap" '^L' zellij-right
	done
	unset _zellij_keymap
fi
