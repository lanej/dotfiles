#!/bin/zsh
zkp() {
	local pid
	pid=$(ps -ef | sed 1d | fzf -m | awk '{print $2}')

	if [ "x$pid" != "x" ]
	then
		echo $pid | xargs kill -${1:-9}
	fi
}

# CTRL-R - Paste the selected command from history into the command line
fzf-history-widget() {
	local selected num
	setopt localoptions noglobsubst noposixbuiltins pipefail 2> /dev/null
	selected=( $(fc -rl 1 |
		FZF_DEFAULT_OPTS="--height ${FZF_TMUX_HEIGHT:-30%} $FZF_DEFAULT_OPTS -n2..,.. --tiebreak=index --bind=ctrl-r:toggle-sort $FZF_CTRL_R_OPTS --query=${(qqq)LBUFFER} +m --reverse" $(__fzfcmd)) )
	local ret=$?
	if [ -n "$selected" ]; then
		num=$selected[1]
		if [ -n "$num" ]; then
			zle vi-fetch-history -n $num
		fi
	fi
	zle redisplay
	typeset -f zle-line-init >/dev/null && zle zle-line-init
	return $ret
}
zle     -N   fzf-history-widget
bindkey '^R' fzf-history-widget

# fco_preview - checkout git branch/tag, with a preview showing the commits between the tag/branch and HEAD
zgo() {
	local tags branches target
	tags=$(
	git tag | awk '{print "\x1b[31;1mtag\x1b[m\t" $1}') || return
	branches=$(
	git branch --all | grep -v HEAD |
		sed "s/.* //" | sed "s#remotes/[^/]*/##" |
		sort -u | awk '{print "\x1b[34;1mbranch\x1b[m\t" $1}') || return
	target=$(
	(echo "$tags"; echo "$branches") |
		fzf --no-hscroll --no-multi --delimiter="\t" -n 2 \
		--ansi --preview="git log -200 --pretty=format:%s $(echo {+2..} |  sed 's/$/../' )" ) || return
	git checkout $(echo "$target" | awk '{print $2}')
}

export FZF_COMPLETION_TRIGGER=''
bindkey '^T' fzf-completion
bindkey '^I' $fzf_default_completion
# Wow the world is not ready for this
# bindkey '^I' fzf-completion
