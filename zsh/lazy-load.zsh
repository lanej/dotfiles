# Lazy loading functions for expensive shell integrations
# Source this early in .zshrc to defer expensive initialization

# Cache the stdout of a slow shell-integration generator ($@, e.g. `starship
# init zsh`) to a file and source the file instead of re-running the
# generator every startup. Reuses zshrc's own compinit staleness window
# (regenerate at most once per 24h) so a tool upgrade is picked up without
# needing a version-string subprocess check on every shell.
_cache_shell_init() {
	local cache_file=$1 temporary
	shift
	command -v "$1" >/dev/null 2>&1 || return 1
	if [[ ! -r "$cache_file" ]] || [[ -n ${cache_file}(#qN.mh+24) ]]; then
		mkdir -p "${cache_file:h}" 2>/dev/null || return 1
		temporary=$(mktemp "${cache_file}.XXXXXX" 2>/dev/null) || return 1
		if "$@" >| "$temporary" 2>/dev/null && [[ -s $temporary ]]; then
			mv -f "$temporary" "$cache_file" 2>/dev/null || { rm -f "$temporary"; return 1; }
		else
			rm -f "$temporary"
			return 1
		fi
	fi
	source "$cache_file"
}

# Lazy load Google Cloud SDK
gcloud() {
    unfunction gcloud gsutil bq 2>/dev/null
    if [[ -f /opt/homebrew/share/google-cloud-sdk/path.zsh.inc ]]; then
        source /opt/homebrew/share/google-cloud-sdk/path.zsh.inc
        source /opt/homebrew/share/google-cloud-sdk/completion.zsh.inc
    fi
    gcloud "$@"
}

gsutil() {
    unfunction gcloud gsutil bq 2>/dev/null
    if [[ -f /opt/homebrew/share/google-cloud-sdk/path.zsh.inc ]]; then
        source /opt/homebrew/share/google-cloud-sdk/path.zsh.inc
        source /opt/homebrew/share/google-cloud-sdk/completion.zsh.inc
    fi
    gsutil "$@"
}

bq() {
    unfunction gcloud gsutil bq 2>/dev/null
    if [[ -f /opt/homebrew/share/google-cloud-sdk/path.zsh.inc ]]; then
        source /opt/homebrew/share/google-cloud-sdk/path.zsh.inc
        source /opt/homebrew/share/google-cloud-sdk/completion.zsh.inc
    fi
    bq "$@"
}

# Detect legacy applications before evaluating direnv, including after initialization.
if command -v direnv >/dev/null; then
    eval "$(direnv hook zsh)"
fi
if command -v direnv >/dev/null && command -v withenv >/dev/null; then
    _ep_direnv_enter() {
        if command -v ep-direnv >/dev/null; then
            ep-direnv ensure "$PWD" || return
        fi
        _direnv_hook
    }
    autoload -U add-zsh-hook
    add-zsh-hook -d chpwd _direnv_hook
    add-zsh-hook chpwd _ep_direnv_enter
    _ep_direnv_enter
fi
