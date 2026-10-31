#!/usr/bin/env bash
# Install configuration for the named Make target.
set -euo pipefail

target=$1
dotfiles=$2
setup_home=$3
uv=$4
os=$5
make_scripts=${BASH_SOURCE[0]%/*}

check_command() {
    bash "$make_scripts/require.sh" command "$1"
}

check_os() {
    bash "$make_scripts/require.sh" os "$1" "$os" "$target"
}

case "$target" in
    treehouse-config)
        mkdir -p "${setup_home}/.config/treehouse"
        ln -fs "${dotfiles}/treehouse/config.toml" "${setup_home}/.config/treehouse/config.toml"
        ;;
    firstmate-config)
        test -x "${setup_home}/src/firstmate/bin/fm-session-start.sh" || { printf '%s\n' 'Missing Firstmate checkout. Run bootstrap.sh first.' >&2; exit 1; }
        mkdir -p "${setup_home}/.local/bin" "${setup_home}/.config/firstmate" "${setup_home}/src/firstmate/config"
        ln -fs "${dotfiles}/bin/firstmate" "${setup_home}/.local/bin/firstmate"
        ln -fs "${dotfiles}/firstmate/tmux.conf" "${setup_home}/.config/firstmate/tmux.conf"
        ln -fs "${dotfiles}/firstmate/backend" "${setup_home}/src/firstmate/config/backend"
        ln -fs "${dotfiles}/firstmate/crew-harness" "${setup_home}/src/firstmate/config/crew-harness"
        ln -fs "${dotfiles}/firstmate/codex-approval-mode" "${setup_home}/src/firstmate/config/codex-approval-mode"
        ;;
    dev)
        mkdir -p "${setup_home}/src"
        ;;
    shell)
        mkdir -p "${setup_home}/.local/bin"
        for source in "${dotfiles}"/bin/*; do
            if [ "${source##*/}" != ep-direnv ]; then
                ln -fs "$source" "${setup_home}/.local/bin/"
            fi
        done
        ln -fs "${dotfiles}/sh/alias" "${setup_home}/.alias"
        ln -fs "${dotfiles}/sh/profile" "${setup_home}/.profile"
        mkdir -p "${setup_home}/.config/htop"
        ln -fs "${dotfiles}/sh/htoprc" "${setup_home}/.config/htop/htoprc"
        mkdir -p "${setup_home}/.config/bottom"
        ln -fs "${dotfiles}/sh/bottom.toml" "${setup_home}/.config/bottom/bottom.toml"
        mkdir -p "${setup_home}/.config/btop"
        ln -fs "${dotfiles}/btop/btop.conf" "${setup_home}/.config/btop/btop.conf"
        mkdir -p "${setup_home}/.local/share/z"
        touch "${setup_home}/.z"
        ln -fs "${dotfiles}/share/z.sh" "${setup_home}/.local/share/z/z.sh"
        ln -fs "${dotfiles}/sh/starship.toml" "${setup_home}/.config/starship.toml"
        mkdir -p "${setup_home}/.config/atuin"
        ln -fs "${dotfiles}/sh/atuin.toml" "${setup_home}/.config/atuin/config.toml"
        ln -fs "${dotfiles}/sh/dircolors" "${setup_home}/.dir_colors"
        ln -fs "${dotfiles}/bash/bashrc" "${setup_home}/.bashrc"
        ln -fs "${dotfiles}/bash/bashenv" "${setup_home}/.bashenv"
        ln -fs "${dotfiles}/bash/bashrc" "${setup_home}/.bashrc"
        ln -fs "${dotfiles}/bash/bashprofile" "${setup_home}/.bash_profile"
        ln -fns "${dotfiles}/bat" "${setup_home}/.config/bat"
        ln -fs "${setup_home}/.alias" "${setup_home}/.bashalias"
        mkdir -p "${setup_home}/.config/glow"
        ln -fs "${dotfiles}/sh/glow.yml" "${setup_home}/.config/glow/glow.yml"
        ln -fs "${dotfiles}/sh/glow.nord.json" "${setup_home}/.config/glow/nord.json"
        ;;
    zsh-config)
        ln -fs "${dotfiles}/zsh/zshrc" "${setup_home}/.zshrc"
        ln -fs "${dotfiles}/zsh/zlogout" "${setup_home}/.zlogout"
        ln -fs "${dotfiles}/zsh/zlogin" "${setup_home}/.zlogin"
        ln -fs "${dotfiles}/zsh/zshenv" "${setup_home}/.zshenv"
        mkdir -p "${setup_home}/.config/zsh/"
        mkdir -p "${setup_home}/.local/share/zsh/"
        mkdir -p "${setup_home}/.local/share/zsh/site-functions"
        mkdir -p "${setup_home}/.zsh/completions"
        mkdir -p "${setup_home}/.zsh/cache"
        ln -fs "${dotfiles}/zsh/zshenv" "${setup_home}/.zshenv"
        ln -fns "${dotfiles}/zsh/zsh-autosuggestions" "${setup_home}/.local/share/zsh/autosuggestions"
        ln -fns "${dotfiles}/zsh/zsh-syntax-highlighting" "${setup_home}/.local/share/zsh/zsh-syntax-highlighting"
        ln -fns "${dotfiles}/zsh/zsh-github-copilot.plugin.zsh" "${setup_home}/.local/share/zsh/zsh-github-copilot.zsh"
        ln -fs "${dotfiles}/zsh/tmux-auto-title.zsh" "${setup_home}/.local/share/zsh/tmux-auto-title.zsh"
        ;;
    zsh-plugins)
        check_command "git"
        [ -e "${setup_home}/.local/share/fzf-tab/.git" ] ||
        git clone -q https://github.com/Aloxaf/fzf-tab "${setup_home}/.local/share/fzf-tab"
        ;;
    tmux-config)
        mkdir -p "${setup_home}/.config/tmux/"
        ln -fs "${dotfiles}/rc/tmux.conf" "${setup_home}/.config/tmux"
        ln -fs "${dotfiles}/rc/tmux.conf" "${setup_home}/.tmux.conf"
        ;;
    zellij-config)
        mkdir -p "$setup_home/.config/zellij/layouts" "$setup_home/.local/bin"
        ln -fs "$dotfiles/zellij/config.kdl" "$setup_home/.config/zellij/config.kdl"
        for source in "$dotfiles"/zellij/layouts/*.kdl; do
            [ -f "$source" ] || continue
            ln -fs "$source" "$setup_home/.config/zellij/layouts/"
        done
        for source in "$dotfiles"/bin/zellij-*; do
            if [ -f "$source" ] && [ -x "$source" ]; then
                ln -fs "$source" "$setup_home/.local/bin/"
            fi
        done
        ;;
    sql-formatters)
        mkdir -p "${setup_home}/.local/bin"
        ln -fs "${dotfiles}/rc/sql-formatter.json" "${setup_home}/.sql-formatter.json"
        ln -fs "${dotfiles}/rc/sqlfluff" "${setup_home}/.sqlfluff"
        ln -fs "${dotfiles}/bin/sql-format-bigquery" "${setup_home}/.local/bin/sql-format-bigquery"
        check_command "${uv}"
        "${uv}" run --script "${dotfiles}/bin/sql-format-bigquery" --help >/dev/null
        ;;
    vim-config)
        touch "${setup_home}/.netrc"
        mkdir -p "${setup_home}/.cache/nvim/undo"
        mkdir -p "${setup_home}/.config/"
        ln -fns "${dotfiles}/vim" "${setup_home}/.vim"
        ln -fs "${dotfiles}/vim/init.vim" "${setup_home}/.vimrc"
        ln -fns "${dotfiles}/nvim" "${setup_home}/.config/nvim"
        ln -fs "${dotfiles}/.lua-format" "${setup_home}/.lua-format"
        mkdir -p "${setup_home}/.local/share/nvim/site/autoload"
        mkdir -p "${setup_home}/.local/share/nvim/min"
        ln -fns "${dotfiles}/ctags" "${setup_home}/.ctags.d"
        ;;
    nvim-gh-review)
        mkdir -p "${setup_home}/.local/bin"
        ln -fs "${dotfiles}/bin/nvim-gh-review" "${setup_home}/.local/bin/nvim-gh-review"
        ;;
    X)
        check_os "Linux"
        ln -fs "${dotfiles}/rc/Xresources" "${setup_home}/.Xresources"
        ln -fs "${dotfiles}/rc/Xresources" "${setup_home}/.Xdefaults"
        ln -fs "${dotfiles}/rc/xinitrc" "${setup_home}/.xinitrc"
        ln -fs "${dotfiles}/rc/xsessionrc" "${setup_home}/.xsessionrc"
        ln -fs "${dotfiles}/rc/xscreensaver" "${setup_home}/.xscreensaver"
        ;;
    ruby)
        ln -fs "${dotfiles}/ruby/irbrc" "${setup_home}/.irbrc"
        ln -fs "${dotfiles}/ruby/pryrc" "${setup_home}/.pryrc"
        ln -fs "${dotfiles}/ruby/rdebugrc" "${setup_home}/.rdebugrc"
        ln -fs "${dotfiles}/ruby/gemrc" "${setup_home}/.gemrc"
        ln -fs "${dotfiles}/ruby/rspec" "${setup_home}/.rspec"
        ;;
    git)
        ln -fs "${dotfiles}/git/gitconfig" "${setup_home}/.gitconfig"
        ln -fs "${dotfiles}/git/gitignore" "${setup_home}/.gitignore"
        ln -fs "${dotfiles}/git/gitcommit" "${setup_home}/.gitcommit"
        ln -fs "${dotfiles}/git/gitattributes" "${setup_home}/.gitattributes"
        ln -fs "${dotfiles}/git/hooks/pre-commit" "${dotfiles}/.git/hooks/pre-commit"
        ln -fs "${dotfiles}/git/hooks/commit-msg" "${dotfiles}/.git/hooks/commit-msg"
        ;;
    gpg)
        mkdir -p "${setup_home}/.gnupg"
        ln -fs "${dotfiles}/rc/gpg.conf" "${setup_home}/.gnupg/gpg.conf"
        ln -fs "${dotfiles}/rc/gpg-agent.conf" "${setup_home}/.gnupg/gpg-agent.conf"
        chmod 700 "${setup_home}/.gnupg"
        ;;
    yabai)
        check_os "Darwin"
        mkdir -p "${setup_home}/.config/skhd"
        ln -fs "${dotfiles}/yabai/skhdrc" "${setup_home}/.config/skhd/skhdrc"
        mkdir -p "${setup_home}/.config/yabai"
        ln -fs "${dotfiles}/yabai/yabairc" "${setup_home}/.config/yabai/yabairc"
        mkdir -p "${setup_home}/.config/borders"
        ln -fs "${dotfiles}/yabai/bordersrc" "${setup_home}/.config/borders/bordersrc"
        ;;
    polybar)
        check_os "Linux"
        mkdir -p "${setup_home}/.config"
        ln -fns "${dotfiles}/polybar" "${setup_home}/.config/polybar"
        ;;
    bspwm)
        check_os "Linux"
        mkdir -p "${setup_home}/.config/bspwm"
        mkdir -p "${setup_home}/.config/sxhkd"
        mkdir -p "${setup_home}/.config/rofi"
        touch "${setup_home}/.xsession"
        ln -fs "${dotfiles}/bspwm/bspwmrc" "${setup_home}/.config/bspwm/bspwmrc"
        ln -fs "${dotfiles}/bspwm/sxhkdrc" "${setup_home}/.config/sxhkd/sxhkdrc"
        ln -fs "${dotfiles}/rc/config.rasi" "${setup_home}/.config/rofi/config.rasi"
        ;;
    kitty-config)
        mkdir -p "${setup_home}/.config/kitty"
        ln -fs "${dotfiles}/kitty/kittyconf" "${setup_home}/.config/kitty/kitty.conf"
        ln -fs "${dotfiles}/kitty/close_tab_with_confirmation.py" "${setup_home}/.config/kitty/close_tab_with_confirmation.py"
        ln -fs "${dotfiles}/kitty/open_last_url.py" "${setup_home}/.config/kitty/open_last_url.py"
        ;;
    python)
        mkdir -p "${setup_home}/.config/"
        ln -fs "${dotfiles}/python/pycodestyle" "${setup_home}/.config/pycodestyle"
        ;;
    wezterm)
        mkdir -p "${setup_home}/.config/wezterm"
        ln -fs "${dotfiles}/wezterm.lua" "${setup_home}/.wezterm.lua"
        ln -fs "${dotfiles}/wezterm.lua" "${setup_home}/.config/wezterm/wezterm.lua"
        ;;
    go)
        mkdir -p "${setup_home}/.config/go"
        ln -fs "${dotfiles}/go/env" "${setup_home}/.config/go/env"
        ;;
    cargo)
        mkdir -p "${setup_home}/.cargo"
        ln -fs "${dotfiles}/cargo/config.toml" "${setup_home}/.cargo/config.toml"
        ;;
    dev-cache-config)
        mkdir -p "${setup_home}/.local/bin" "${setup_home}/.config"
        ln -fs "${dotfiles}/bin/dev-cache-prune" "${setup_home}/.local/bin/dev-cache-prune"
        test -f "${setup_home}/.config/dev-cache-budgets.json" || cp "${dotfiles}/rc/dev-cache-budgets.json" "${setup_home}/.config/dev-cache-budgets.json"
        ;;
    claude-config)
        mkdir -p "${setup_home}/.claude"
        mkdir -p "${setup_home}/.claude/local"
        ln -fs "${dotfiles}/.claude/settings.json" "${setup_home}/.claude/settings.json"
        ln -fs "${dotfiles}/claude/CLAUDE.md" "${setup_home}/.claude/CLAUDE.md"
        ln -fs "${dotfiles}/claude/CONSTITUTION.md" "${setup_home}/.claude/CONSTITUTION.md"
        for d in commands workflows; do
            if [ -L "${setup_home}/.claude/$d" ]; then
                rm "${setup_home}/.claude/$d"
            fi
            mkdir -p "${setup_home}/.claude/$d"
            for link in "${setup_home}/.claude/$d/"*; do
                if [ -L "$link" ] && [ ! -e "$link" ]; then
                    case "$(readlink "$link")" in
                        "${dotfiles}/claude/$d/"*) rm "$link" ;;
                    esac
                fi
            done
            for f in "${dotfiles}/claude/$d/"*; do
                [ -e "$f" ] || continue
                ln -fs "$f" "${setup_home}/.claude/$d/"
            done
        done
        ln -fs "${dotfiles}/bin/claude-wrapper" "${setup_home}/.claude/local/claude-wrapper"
        check_command "git"
        git -C "${dotfiles}" config filter.claude-settings.clean 'jq --indent 2 "del(.feedbackSurveyState)"'
        git -C "${dotfiles}" config filter.claude-settings.smudge cat
        check_command "jq"
        ;;
    codex-env)
        mkdir -p "${setup_home}/.codex"
        if [ ! -e "${setup_home}/.codex/.env" ] && [ ! -L "${setup_home}/.codex/.env" ] ||
            [ "$(readlink "${setup_home}/.codex/.env")" = "${dotfiles}/codex/env" ]; then
            if [ -f "${setup_home}/.config/bedrock/env" ]; then
                ln -fs "${setup_home}/.config/bedrock/env" "${setup_home}/.codex/.env"
            else
                ln -fs "${dotfiles}/codex/env" "${setup_home}/.codex/.env"
            fi
        fi
        ;;
    codex-guidance)
        if [ ! -e "${setup_home}/.codex/bedrock.config.toml" ] && [ ! -L "${setup_home}/.codex/bedrock.config.toml" ] &&
            [ -f "${dotfiles}/codex/bedrock.config.toml" ]; then
            ln -fs "${dotfiles}/codex/bedrock.config.toml" "${setup_home}/.codex/bedrock.config.toml"
        fi
        cat "${dotfiles}/codex/AGENTS.md" "${dotfiles}/codex/AGENTS.local.md" > "${setup_home}/.codex/AGENTS.md" 2>/dev/null || cp "${dotfiles}/codex/AGENTS.md" "${setup_home}/.codex/AGENTS.md"
        ;;
    quarto)
        mkdir -p "${setup_home}/.config/quarto"
        ln -fns "${dotfiles}/quarto/styles" "${setup_home}/.config/quarto/styles"
        ln -fs "${dotfiles}/quarto/_quarto.yml" "${setup_home}/.config/quarto/_quarto.yml"
        echo "✓ Quarto configuration linked"
        ;;
    presenterm)
        mkdir -p "${setup_home}/.config/presenterm/themes"
        ln -fs "${dotfiles}/presenterm/config.toml" "${setup_home}/.config/presenterm/config.toml"
        ln -fs "${dotfiles}/presenterm/themes/nord.yaml" "${setup_home}/.config/presenterm/themes/nord.yaml"
        ;;
    mail)
        echo "Setting up email configuration..."
        mkdir -p "${setup_home}/.config/neomutt"
        mkdir -p "${setup_home}/.cache/neomutt/headers"
        mkdir -p "${setup_home}/.cache/neomutt/bodies"
        mkdir -p "${setup_home}/.local/share/msmtp"
        ln -fs "${dotfiles}/mail/mbsyncrc" "${setup_home}/.mbsyncrc"
        ln -fs "${dotfiles}/mail/notmuch-config" "${setup_home}/.notmuch-config"
        ln -fs "${dotfiles}/mail/msmtprc" "${setup_home}/.msmtprc"
        ln -fs "${dotfiles}/mail/neomuttrc" "${setup_home}/.config/neomutt/neomuttrc"
        echo "✓ Email configuration files linked"
        echo ""
        echo "Next steps:"
        echo "  1. Run: bash ${dotfiles}/mail/setup-email.sh"
        echo "  2. Follow the prompts to configure your Gmail account"
        echo "  3. Launch neomutt when done"
        ;;
    ui-review)
        check_command "node"
        check_command "npm"
        python3 "${dotfiles}/scripts/install-viewrule.py"
        mkdir -p "${setup_home}/.local/bin"
        ln -fs "${dotfiles}/bin/ui-review" "${setup_home}/.local/bin/ui-review"
        ln -fs "${dotfiles}/bin/ui-review" "${setup_home}/.local/bin/viewrule"
        echo "Viewrule installed. Use /ui-review in Claude Code or viewrule --help."
        ;;
    epenv)
        destination="${setup_home}/.local/bin/epenv"
        source="${dotfiles}/bin/epenv"
        if [ -e "$destination" ] || [ -L "$destination" ]; then
            if [ ! -L "$destination" ] || [ "$(readlink "$destination")" != "$source" ]; then
                printf 'epenv: preserving existing destination: %s\n' "$destination" >&2
                exit 1
            fi
        else
            mkdir -p "${setup_home}/.local/bin"
            ln -s "$source" "$destination"
        fi
        ;;
    undercurl)
        printf '\e[4:3mUndercurled?\n'
        ;;
    *) printf 'Unknown configuration target: %s\n' "$target" >&2; exit 1 ;;
esac
