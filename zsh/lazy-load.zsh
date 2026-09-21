# Lazy loading functions for expensive shell integrations
# Source this early in .zshrc to defer expensive initialization

# Cache the stdout of a slow shell-integration generator ($@, e.g. `starship
# init zsh`) to a file and source the file instead of re-running the
# generator every startup. Reuses zshrc's own compinit staleness window
# (regenerate at most once per 24h) so a tool upgrade is picked up without
# needing a version-string subprocess check on every shell.
_cache_shell_init() {
	local cache_file=$1
	shift
	if [[ ! -r "$cache_file" ]] || [[ -n ${cache_file}(#qN.mh+24) ]]; then
		mkdir -p "${cache_file:h}"
		"$@" >| "$cache_file" 2>/dev/null
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

# Lazy load direnv (only when entering directory with .envrc)
if command -v direnv >/dev/null; then
    _direnv_lazy_load() {
        # .env is unrelated to direnv (it's the plain secrets file .profile
        # sources directly); it lives in $HOME, so matching it here fired
        # this hook on every single shell start regardless of directory.
        if [[ -f .envrc ]]; then
            eval "$(direnv hook zsh)"
            add-zsh-hook -d chpwd _direnv_lazy_load
            _direnv_hook
        fi
    }
    
    # Check on directory change
    autoload -U add-zsh-hook
    add-zsh-hook chpwd _direnv_lazy_load
    
    # Check current directory on startup (async)
    _direnv_lazy_load &!
fi
