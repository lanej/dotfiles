# Lazy loading functions for expensive shell integrations
# Source this early in .zshrc to defer expensive initialization

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
        if [[ -f .envrc ]] || [[ -f .env ]]; then
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
