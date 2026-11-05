# Keep a native title on this shell's own terminal, never the focused tab.
# Zellij's explicit pane names override OSC titles; explicit tab names are left
# alone by the bar/picker. This also lets applications own the title while running.
if [[ -n $ZELLIJ && -n $ZELLIJ_PANE_ID ]] &&
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
	autoload -Uz add-zsh-hook
	add-zsh-hook chpwd _zellij_auto_title
	add-zsh-hook precmd _zellij_auto_title
fi
