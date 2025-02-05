.PHONY: banner shell git fish screen tmux vim nvim X ruby chunk awesome i3 polybar oni bspwm kitty bash
.PHONY: zsh qute alacritty yabai spotify_player python purs
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
.PHONY: zsh
zsh: shell
	@ln -fs $(DOTFILES)/zsh/zshrc $(HOME)/.zshrc
	@ln -fs $(DOTFILES)/zsh/zlogout $(HOME)/.zlogout
	@ln -fs $(DOTFILES)/zsh/zlogin $(HOME)/.zlogin
	@ln -fs $(DOTFILES)/zsh/zshenv $(HOME)/.zshenv
	@mkdir -p $(HOME)/.config/zsh/
	@mkdir -p $(HOME)/.local/share/zsh/
	@ln -fs $(DOTFILES)/zsh/zshenv $(HOME)/.zshenv
	@ln -fns $(DOTFILES)/zsh/zsh-autosuggestions $(HOME)/.local/share/zsh/autosuggestions
	@git -C $(HOME)/.local/share/fzf-tab pull 2>/dev/null -q || \
		git clone -q https://github.com/Aloxaf/fzf-tab $(HOME)/.local/share/fzf-tab
	@ln -fns $(DOTFILES)/zsh/zsh-syntax-highlighting $(HOME)/.local/share/zsh/zsh-syntax-highlighting
powerlevel10k:
	@git -C $(HOME)/.oh-my-zsh pull 2>/dev/null -q || \
		git clone -q https://github.com/robbyrussell/oh-my-zsh.git $(HOME)/.oh-my-zsh
	@git -C $(HOME)/.oh-my-zsh/custom/themes/powerlevel10k pull -q || \
		git clone -q https://github.com/romkatv/powerlevel10k.git $(HOME)/.oh-my-zsh/custom/themes/powerlevel10k
	@ln -fns $(DOTFILES)/zsh/zsh-autosuggestions $(HOME)/.oh-my-zsh/custom/plugins/zsh-autosuggestions
	@ln -fs $(DOTFILES)/zsh/p10k.zsh $(HOME)/.p10k.zsh
screen:
	@ln -fs $(DOTFILES)/rc/screenrc $(HOME)/.screenrc
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
chunk:
	@ln -fs $(DOTFILES)/chunk/chunkwmrc $(HOME)/.chunkwmrc
yabai:
	@mkdir -p $(HOME)/.config/skhd
	@ln -fs $(DOTFILES)/yabai/skhdrc $(HOME)/.config/skhd/skhdrc
	@mkdir -p $(HOME)/.config/yabai
	@ln -fs $(DOTFILES)/yabai/yabairc $(HOME)/.config/yabai/yabairc
	@mkdir -p $(HOME)/.config/borders
	@ln -fs $(DOTFILES)/yabai/bordersrc $(HOME)/.config/borders/bordersrc
i3:
	@mkdir -p $(HOME)/.config/i3
	@ln -fs $(DOTFILES)/i3/config $(HOME)/.config/i3/config
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
python:
	@mkdir -p $(HOME)/.config/
	@ln -fs $(DOTFILES)/python/pycodestyle $(HOME)/.config/pycodestyle
alacritty:
	@mkdir -p $(HOME)/.config/alacritty
	@ln -fs $(DOTFILES)/alacritty/alacritty.yml $(HOME)/.config/alacritty
spotify_player:
	@ln -fns $(DOTFILES)/spotify-player $(HOME)/.config/spotify-player
powerline:
	@ln -fns $(DOTFILES)/powerline $(HOME)/.config/powerline
purs:
	@git -C $(HOME)/.local/share/purs pull -q || \
		git clone -q git@github.com:lanej/purs.git --single-branch $(HOME)/.local/share/purs
	@command -v cargo >/dev/null && cargo install -q --path $(HOME)/.local/share/purs
.PHONY: undercurl
undercurl:
	/bin/bash -c "printf '\e[4:3mUndercurled?\n'"

.PHONY: chatgpt
chatgpt:
	@git -C $(HOME)/.local/share/chatgpt pull -q || \
		git clone -q git@github.com:0xacx/chatGPT-shell-cli.git $(HOME)/.local/share/chatgpt
	@ln -s $(HOME)/.local/share/chatgpt/chatgpt.sh ~/.local/bin/chatgpt
ifeq ($(OS),OSX)
qute:
	@mkdir -p $(HOME)/.qutebrowser
	@ln -fs $(DOTFILES)/qute/config.py $(HOME)/.qutebrowser/config.py
else
qute:
	@mkdir -p $(HOME)/.config/qutebrowser
	@ln -fs $(DOTFILES)/qute/config.py $(HOME)/.config/qutebrowser/config.py
endif
