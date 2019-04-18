zz() {
	cd "$(_z -l 2>&1 | sed 's/^[0-9,.]* *//' | fzf --reverse --height=30% -q "$_last_z_args")" || exit
}
