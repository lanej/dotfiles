.PHONY: banner shell git fish screen tmux vim nvim X ruby chunk awesome i3 polybar oni bspwm kitty bash
.PHONY: zsh qute alacritty yabai powerline
DOTFILES := $(shell pwd)

all: .PHONY

banner:
	@cat banner.txt
dev:
	@mkdir -p $(HOME)/src
fish:
	@mkdir -p $(HOME)/.config/fish/functions
	@ln -fs $(DOTFILES)/fish/config $(HOME)/.config/fish/config.fish
	@$(shell for f in $(DOTFILES)/fish/functions/*; do ln -fs $$f ~/.config/fish/functions/; done)
shell:
	@mkdir -p $(HOME)/.local/bin
	@ln -fs $(DOTFILES)/bin/* $(HOME)/.local/bin/
	@ln -fs $(DOTFILES)/sh/alias $(HOME)/.alias
	@ln -fs $(DOTFILES)/sh/profile $(HOME)/.profile
	@mkdir -p $(HOME)/.config/htop
	@ln -fs $(DOTFILES)/sh/htoprc $(HOME)/.config/htop/htoprc
	@mkdir -p $(HOME)/.local/share/z
	@ln -fs $(DOTFILES)/share/z.sh $(HOME)/.local/share/z/z.sh
	@ln -fs $(DOTFILES)/sh/starship.toml $(HOME)/.config/starship.toml
bash: shell
	@ln -fs $(DOTFILES)/bash/bashrc $(HOME)/.bashrc
	@ln -fs $(DOTFILES)/bash/bashenv $(HOME)/.bashenv
	@ln -fs $(DOTFILES)/bash/bashrc $(HOME)/.bashrc
	@ln -fs $(DOTFILES)/bash/bashprofile $(HOME)/.bash_profile
	@ln -fs $(HOME)/.alias $(HOME)/.bashalias
zsh: shell
	@ln -fs $(DOTFILES)/zsh/zshrc $(HOME)/.zshrc
	@ln -fs $(DOTFILES)/zsh/zlogout $(HOME)/.zlogout
	@ln -fs $(DOTFILES)/zsh/zshenv $(HOME)/.zshenv
	@mkdir -p $(HOME)/.config/zsh/
	@ln -fs $(DOTFILES)/zsh/zshenv $(HOME)/.zshenv
	@git -C $(HOME)/.oh-my-zsh pull 2>/dev/null -q || \
		git clone -q https://github.com/robbyrussell/oh-my-zsh.git $(HOME)/.oh-my-zsh
	@git -C $(HOME)/.oh-my-zsh/custom/themes/powerlevel10k pull -q || \
		git clone -q https://github.com/romkatv/powerlevel10k.git $(HOME)/.oh-my-zsh/custom/themes/powerlevel10k
	@ln -fns $(DOTFILES)/zsh/zsh-autosuggestions $(HOME)/.oh-my-zsh/custom/plugins/zsh-autosuggestions
screen:
	@ln -fs $(DOTFILES)/rc/screenrc $(HOME)/.screenrc
tmux:
	@mkdir -p $(HOME)/.config/tmux/
	@ln -fs $(DOTFILES)/rc/tmux.conf $(HOME)/.config/tmux
vim:
	@touch $(HOME)/.netrc
	@mkdir -p $(HOME)/.cache/nvim/undo
	@mkdir -p $(HOME)/.config/nvim/
	@ln -fns $(DOTFILES)/vim $(HOME)/.vim
	@ln -fs $(DOTFILES)/nvim/init.vim $(HOME)/.config/nvim/init.vim
	@ln -fs $(DOTFILES)/nvim/init.vim $(HOME)/.vimrc
	@mkdir -p $(HOME)/.local/share/nvim/site/autoload
	@ln -fs $(DOTFILES)/vim/autoload/plug.vim $(HOME)/.local/share/nvim/site/autoload/plug.vim
	@mkdir -p $(HOME)/.local/share/nvim/plugged
	@mkdir -p $(HOME)/.local/share/nvim/min
	@ln -fs $(DOTFILES)/nvim/min.vim $(HOME)/.config/nvim/min.vim
	@ln -fs $(DOTFILES)/nvim/coc-settings.json $(HOME)/.config/nvim/coc-settings.json
	@nvim --headless +PlugInstall +qa || echo ''
	@vim -E -s -c "PlugInstall" -c "qa" || echo ''
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
	@cp -n git/gitconfig $(HOME)/.gitconfig
	@git config --global --get user.email 1>/dev/null || sh set-git-email.sh
	@ln -fs $(DOTFILES)/git/gitignore $(HOME)/.gitignore
	@ln -fs $(DOTFILES)/git/gitcommit $(HOME)/.gitcommit
	@ln -fs $(DOTFILES)/git/gitattributes $(HOME)/.gitattributes
chunk:
	@ln -fs $(DOTFILES)/chunk/chunkwmrc $(HOME)/.chunkwmrc
yabai:
	@mkdir -p $(HOME)/.config/skhd
	@ln -fs $(DOTFILES)/yabai/skhdrc $(HOME)/.config/skhd/skhdrc
	@mkdir -p $(HOME)/.config/yabai
	@ln -fs $(DOTFILES)/yabai/yabairc $(HOME)/.config/yabai/yabairc
i3:
	@mkdir -p $(HOME)/.config/i3
	@ln -fs $(DOTFILES)/i3/config $(HOME)/.config/i3/config
polybar:
	@mkdir -p $(HOME)/.config/polybar
	@ln -fs $(DOTFILES)/polybar/config $(HOME)/.config/polybar/config
	@ln -fs $(DOTFILES)/polybar/launch.sh $(HOME)/.config/polybar/launch.sh
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
alacritty:
	@mkdir -p $(HOME)/.config/alacritty
	@ln -fs $(DOTFILES)/alacritty/alacritty.yml $(HOME)/.config/alacritty
powerline:
	@ln -fns $(DOTFILES)/powerline $(HOME)/.config/powerline
ifeq ($(OS),OSX)
qute:
	@mkdir -p $(HOME)/.qutebrowser
	@ln -fs $(DOTFILES)/qute/config.py $(HOME)/.qutebrowser/config.py
else
qute:
	@mkdir -p $(HOME)/.config/qutebrowser
	@ln -fs $(DOTFILES)/qute/config.py $(HOME)/.config/qutebrowser/config.py
endif
