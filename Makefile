.PHONY: banner shell git fish screen tmux vim nvim X ruby chunk awesome i3 polybar oni bspwm kitty bash
.PHONY: zsh qute alacritty yabai spotify_player python go claude gpg-restore
DOTFILES := $(shell pwd)

all: .PHONY

banner:
	@cat banner.txt
dev:
	@mkdir -p $(HOME)/src
shell:
	@mkdir -p $(HOME)/.local/bin
	@ln -fs $(DOTFILES)/bin/* $(HOME)/.local/bin/
	@ln -fs $(DOTFILES)/sh/alias $(HOME)/.alias
	@ln -fs $(DOTFILES)/sh/profile $(HOME)/.profile
	@mkdir -p $(HOME)/.config/htop
	@ln -fs $(DOTFILES)/sh/htoprc $(HOME)/.config/htop/htoprc
	@mkdir -p $(HOME)/.config/bottom
	@ln -fs $(DOTFILES)/sh/bottom.toml $(HOME)/.config/bottom/bottom.toml
	@mkdir -p $(HOME)/.local/share/z
	@ln -fns $(DOTFILES)/ghostty $(HOME)/.config/ghostty
	@ln -fs $(DOTFILES)/share/z.sh $(HOME)/.local/share/z/z.sh
	@ln -fs $(DOTFILES)/sh/starship.toml $(HOME)/.config/starship.toml
	@mkdir -p $(HOME)/.config/atuin
	@ln -fs $(DOTFILES)/sh/atuin.toml $(HOME)/.config/atuin/config.toml
	@ln -fs $(DOTFILES)/sh/dir_colors $(HOME)/.dir_colors
	@ln -fs $(DOTFILES)/bash/bashrc $(HOME)/.bashrc
	@ln -fs $(DOTFILES)/bash/bashenv $(HOME)/.bashenv
	@ln -fs $(DOTFILES)/bash/bashrc $(HOME)/.bashrc
	@ln -fs $(DOTFILES)/bash/bashprofile $(HOME)/.bash_profile
	@ln -fns $(DOTFILES)/bat $(HOME)/.config/bat
	@ln -fs $(HOME)/.alias $(HOME)/.bashalias
	@mkdir -p $(HOME)/.config/glow
	@ln -fs $(DOTFILES)/sh/glow.yml $(HOME)/.config/glow/glow.yml
	@ln -fs $(DOTFILES)/sh/glow.nord.json $(HOME)/.config/glow/nord.json
.PHONY: zsh
zsh: shell
	@ln -fs $(DOTFILES)/zsh/zshrc $(HOME)/.zshrc
	@ln -fs $(DOTFILES)/zsh/zlogout $(HOME)/.zlogout
	@ln -fs $(DOTFILES)/zsh/zlogin $(HOME)/.zlogin
	@ln -fs $(DOTFILES)/zsh/zshenv $(HOME)/.zshenv
	@mkdir -p $(HOME)/.config/zsh/
	@mkdir -p $(HOME)/.local/share/zsh/
	@mkdir -p $(HOME)/.local/share/zsh/site-functions
	@mkdir -p $(HOME)/.zsh/completions
	@mkdir -p $(HOME)/.zsh/cache
	@ln -fs $(DOTFILES)/zsh/zshenv $(HOME)/.zshenv
	@ln -fns $(DOTFILES)/zsh/zsh-autosuggestions $(HOME)/.local/share/zsh/autosuggestions
	@if [ -d $(HOME)/.local/share/fzf-tab ]; then \
		git -C $(HOME)/.local/share/fzf-tab pull -q; \
	else \
		git clone -q https://github.com/Aloxaf/fzf-tab $(HOME)/.local/share/fzf-tab; \
	fi
	@ln -fns $(DOTFILES)/zsh/zsh-syntax-highlighting $(HOME)/.local/share/zsh/zsh-syntax-highlighting
	@ln -fns $(DOTFILES)/zsh/zsh-github-copilot.plugin.zsh $(HOME)/.local/share/zsh/zsh-github-copilot.zsh
	@ln -fs $(DOTFILES)/zsh/tmux-auto-title.zsh $(HOME)/.local/share/zsh/tmux-auto-title.zsh
tmux:
	@mkdir -p $(HOME)/.config/tmux/
	@ln -fs $(DOTFILES)/rc/tmux.conf $(HOME)/.config/tmux
	@ln -fs $(DOTFILES)/rc/tmux.conf $(HOME)/.tmux.conf
vim:
	@touch $(HOME)/.netrc
	@mkdir -p $(HOME)/.cache/nvim/undo
	@mkdir -p $(HOME)/.config/
	@ln -fns $(DOTFILES)/vim $(HOME)/.vim
	@ln -fs $(DOTFILES)/vim/init.vim $(HOME)/.vimrc
	@ln -fns $(DOTFILES)/nvim $(HOME)/.config/nvim
	@ln -fs $(DOTFILES)/.lua-format $(HOME)/.lua-format
	@mkdir -p $(HOME)/.local/share/nvim/site/autoload
	@mkdir -p $(HOME)/.local/share/nvim/min
	@ln -fns $(DOTFILES)/ctags $(HOME)/.ctags.d
X:
	@ln -fs $(DOTFILES)/rc/Xresources $(HOME)/.Xresources
	@ln -fs $(DOTFILES)/rc/Xresources $(HOME)/.Xdefaults
	@ln -fs $(DOTFILES)/rc/xinitrc $(HOME)/.xinitrc
	@ln -fs $(DOTFILES)/rc/xsessionrc $(HOME)/.xsessionrc
	@ln -fs $(DOTFILES)/rc/xscreensaver $(HOME)/.xscreensaver
ruby:
	@ln -fs $(DOTFILES)/ruby/irbrc $(HOME)/.irbrc
	@ln -fs $(DOTFILES)/ruby/pryrc $(HOME)/.pryrc
	@ln -fs $(DOTFILES)/ruby/rdebugrc $(HOME)/.rdebugrc
	@ln -fs $(DOTFILES)/ruby/gemrc $(HOME)/.gemrc
	@ln -fs $(DOTFILES)/ruby/rspec $(HOME)/.rspec
git:
	@ln -fs $(DOTFILES)/git/gitconfig $(HOME)/.gitconfig
	@ln -fs $(DOTFILES)/git/gitignore $(HOME)/.gitignore
	@ln -fs $(DOTFILES)/git/gitcommit $(HOME)/.gitcommit
	@ln -fs $(DOTFILES)/git/gitattributes $(HOME)/.gitattributes
gpg:
	@mkdir -p $(HOME)/.gnupg
	@ln -fs $(DOTFILES)/rc/gpg.conf $(HOME)/.gnupg/gpg.conf
	@ln -fs $(DOTFILES)/rc/gpg-agent.conf $(HOME)/.gnupg/gpg-agent.conf
	@chmod 700 $(HOME)/.gnupg
yabai:
	@mkdir -p $(HOME)/.config/skhd
	@ln -fs $(DOTFILES)/yabai/skhdrc $(HOME)/.config/skhd/skhdrc
	@mkdir -p $(HOME)/.config/yabai
	@ln -fs $(DOTFILES)/yabai/yabairc $(HOME)/.config/yabai/yabairc
	@mkdir -p $(HOME)/.config/borders
	@ln -fs $(DOTFILES)/yabai/bordersrc $(HOME)/.config/borders/bordersrc
polybar:
	@ln -fns $(DOTFILES)/polybar $(HOME)/.config/polybar
oni:
	@mkdir -p $(HOME)/.config/oni
	@ln -fs $(DOTFILES)/oni/config.js $(HOME)/.config/oni/config.js
	@ln -fs $(DOTFILES)/oni/config.tsx $(HOME)/.config/oni/config.tsx
bspwm:
	@mkdir -p $(HOME)/.config/bspwm
	@mkdir -p $(HOME)/.config/sxhkd
	@mkdir -p $(HOME)/.config/rofi
	@touch $(HOME)/.xsession
	@ln -fs $(DOTFILES)/bspwm/bspwmrc $(HOME)/.config/bspwm/bspwmrc
	@ln -fs $(DOTFILES)/bspwm/sxhkdrc $(HOME)/.config/sxhkd/sxhkdrc
	@ln -fs $(DOTFILES)/rc/config.rasi $(HOME)/.config/rofi/config.rasi
kitty:
	@mkdir -p $(HOME)/.config/kitty
	@ln -fs $(DOTFILES)/kitty/kittyconf $(HOME)/.config/kitty/kitty.conf
	@ln -fs $(DOTFILES)/kitty/close_tab_with_confirmation.py $(HOME)/.config/kitty/close_tab_with_confirmation.py
python:
	@mkdir -p $(HOME)/.config/
	@ln -fs $(DOTFILES)/python/pycodestyle $(HOME)/.config/pycodestyle
alacritty:
	@mkdir -p $(HOME)/.config/alacritty
	@ln -fs $(DOTFILES)/alacritty/alacritty.yml $(HOME)/.config/alacritty
spotify_player:
	@ln -fns $(DOTFILES)/spotify-player $(HOME)/.config/spotify-player
undercurl:
	/bin/bash -c "printf '\e[4:3mUndercurled?\n'"
go:
	@mkdir -p $(HOME)/.config/go
	@ln -fs $(DOTFILES)/go/env $(HOME)/.config/go/env
claude:
	@mkdir -p $(HOME)/.claude
	@ln -fns $(DOTFILES)/claude/commands $(HOME)/.claude/commands
	@ln -fns $(DOTFILES)/claude/agents $(HOME)/.claude/agents
gpg-restore:
	@if gpg --list-secret-keys 6DAE70CE5C232C03 >/dev/null 2>&1; then \
		echo "✓ GPG key 6DAE70CE5C232C03 already present"; \
		exit 0; \
	fi
	@echo "Restoring GPG key from 1Password..."
	@if ! command -v op >/dev/null 2>&1; then \
		echo "Error: 1Password CLI (op) not found"; \
		exit 1; \
	fi
	@op read "op://Personal/d4xe37k5vnkkjmx5hk3vxiinn4/private_key" --account my.1password.com | gpg --import
	@echo "✓ GPG key imported"
	@echo ""
	@echo "Now setting key trust level..."
	@echo "Run the following commands:"
	@echo "  gpg --edit-key 6DAE70CE5C232C03"
	@echo "  trust"
	@echo "  5 (ultimate)"
	@echo "  y"
	@echo "  quit"
