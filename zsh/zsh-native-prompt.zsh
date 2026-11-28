autoload -Uz add-zsh-hook add-zle-hook-widget
setopt prompt_subst

local prompt_theme_dir="${DOTFILES_THEME_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/dotfiles/theme}"
(( ${+DOTFILES_BRANCH_SYMBOL} )) || [[ ! -r $prompt_theme_dir/shell-symbols.sh ]] || source "$prompt_theme_dir/shell-symbols.sh"
[[ ! -r $prompt_theme_dir/zsh-prompt.sh ]] || source "$prompt_theme_dir/zsh-prompt.sh"
unset prompt_theme_dir

typeset -g _dotfiles_prompt_context='' _dotfiles_prompt_color='' _dotfiles_prompt_character='$'
typeset -gi _dotfiles_prompt_initialized=0
typeset -g _dotfiles_prompt_full='%$(( COLUMNS > 8 ? COLUMNS - 1 : 8 ))<…<${_dotfiles_prompt_context}%<<
${_dotfiles_prompt_color}%B${_dotfiles_prompt_character}%b%f '

_dotfiles_prompt_git_group() {
	local count glyph color
	REPLY=''
	for count glyph color in "$@"; do
		[[ $count == <-> && $count != 0 ]] || continue
		REPLY+=" %F{$color}${count}${glyph//\%/%%}%f"
	done
	return 0
}

_dotfiles_prompt_read_git() {
	local snapshot entry branch oid ahead behind branch_label REPLY
	local -a tracking
	local -i staged=0 changed=0 untracked=0 conflicted=0
	snapshot=$(command git --no-optional-locks status --porcelain=v2 --branch --ahead-behind --untracked-files=all 2>/dev/null) || return 1
	for entry in ${(f)snapshot}; do
		case $entry in
			'# branch.head '*) branch=${entry#'# branch.head '} ;;
			'# branch.oid '*) oid=${entry#'# branch.oid '} ;;
			'# branch.ab '*)
				tracking=(${(s: :)entry})
				ahead=${tracking[3]#+} behind=${tracking[4]#-}
				;;
			[12]' '*)
				[[ $entry[3] == . ]] || (( ++staged ))
				[[ $entry[4] == . ]] || (( ++changed ))
				;;
			'u '*) (( ++conflicted )) ;;
			'? '*) (( ++untracked )) ;;
		esac
	done
	if [[ $branch == '(detached)' ]]; then
		branch_label="%F{12}@${oid[1,7]}%f"
	elif [[ -n $branch ]]; then
		local branch_symbol=${DOTFILES_BRANCH_SYMBOL:-@}
		branch_label="%F{12}${branch_symbol//\%/%%} ${branch//\%/%%}%f"
	else
		return 1
	fi
	_dotfiles_prompt_git_group "$ahead" "${DOTFILES_AHEAD_SYMBOL:->}" 10 "$behind" "${DOTFILES_BEHIND_SYMBOL:-<}" 11
	branch_label+=$REPLY
	_dotfiles_prompt_git_group "$conflicted" '!' 9 "$staged" "${DOTFILES_STAGED_SYMBOL:-+}" 10 \
		"$changed" "${DOTFILES_CHANGED_SYMBOL:-~}" 11 "$untracked" "${DOTFILES_UNTRACKED_SYMBOL:-?}" 12
	_dotfiles_prompt_chevrons "$branch_label" "${REPLY# }" "$1"
}

_dotfiles_prompt_chevrons() {
	local branch=$1 files=$2 outline=$3 background=${DOTFILES_PROMPT_SELECTED-} files_background=${DOTFILES_PROMPT_RAISED-}
	local chevron=${DOTFILES_PROMPT_CHEVRON:-›}
	chevron=${chevron//\%/%%}
	if [[ -z $background || -z $files_background ]]; then
		_dotfiles_prompt_context+="$outline $branch${files:+ $chevron $files}"
		return 0
	fi
	_dotfiles_prompt_context+="%F{$background}%S$chevron%s%f%K{$background} $branch "
	if [[ -n $files ]]; then
		_dotfiles_prompt_context+="%K{$files_background}%F{$background}$chevron%f $files "
		background=$files_background
	fi
	_dotfiles_prompt_context+="%k%F{$background}$chevron%f"
}

_dotfiles_prompt_cwd() {
	local input=$PWD shortened prefix=''
	REPLY='%~'
	(( $+commands[shortpath] )) && [[ $PWD != "$HOME" ]] || return 0
	if [[ $input == "$HOME/"* ]]; then
		input=${input#"$HOME/"}
		prefix='~/'
	fi
	shortened=$(
		if [[ -n $prefix ]]; then
			builtin cd -q -- "$HOME" || exit 1
		fi
		command shortpath --null -- "$input"
	) 2>/dev/null || return 0
	shortened=${shortened%$'\0'}
	[[ -n $shortened ]] || return 0
	shortened=${(V)shortened}
	REPLY="$prefix${shortened//\%/%%}"
}

_dotfiles_prompt_precmd() {
	local last_status=$? outline=${DOTFILES_PROMPT_OUTLINE:-›} REPLY
	_dotfiles_prompt_color=''
	if (( _dotfiles_prompt_initialized && last_status != 0 )); then
		_dotfiles_prompt_color='%F{9}'
	fi
	_dotfiles_prompt_initialized=1
	_dotfiles_prompt_character='$'
	_dotfiles_prompt_cwd
	_dotfiles_prompt_context="%F{14}${REPLY}%f "
	outline="%F{${DOTFILES_PROMPT_BORDER:-8}}${outline//\%/%%}%f"
	PROMPT=$_dotfiles_prompt_full
	_dotfiles_prompt_read_git "$outline" || _dotfiles_prompt_context+=$outline
}

_dotfiles_prompt_keymap() {
	[[ $CONTEXT == start ]] || return 0
	if [[ $KEYMAP == vicmd ]]; then
		_dotfiles_prompt_character=''
	else
		_dotfiles_prompt_character='$'
	fi
	zle reset-prompt
}

_dotfiles_prompt_finish() {
	[[ $CONTEXT == start && -n ${BUFFER//[[:space:]]/} && -z ${ZLE_LINE_ABORTED-} ]] || return 0
	PROMPT='${_dotfiles_prompt_color}%B$%b%f '
	zle reset-prompt
}

PROMPT=$_dotfiles_prompt_full
RPROMPT=''

add-zsh-hook precmd _dotfiles_prompt_precmd
add-zle-hook-widget keymap-select _dotfiles_prompt_keymap
add-zle-hook-widget line-finish _dotfiles_prompt_finish
