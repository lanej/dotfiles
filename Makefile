.PHONY: dev git fish shell screen tmux vim nvim X ruby chunk awesome i3 polybar oni bspwm kitty bash zsh qute
all: .PHONY

DOTFILES := $(shell pwd)

dev:
	mkdir -p $(HOME)/src
fish:
	mkdir -p ${HOME}/.config/fish/functions
	ln -fs $(DOTFILES)/fish/config ${HOME}/.config/fish/config.fish
	$(shell for f in $(DOTFILES)/fish/functions/*; do ln -fs $$f ~/.config/fish/functions/; done)
shell:
	ln -fs ${DOTFILES}/env ${HOME}/.env
	ln -fns $(DOTFILES)/bin/ ${HOME}/bin
	ln -fs $(DOTFILES)/ctags ${HOME}/.ctags
	ln -fs ${DOTFILES}/bash/alias ${HOME}/.alias
	ln -fns $(DOTFILES)/etc/ ${HOME}/etc
	ln -fs $(DOTFILES)/sh/profile ${HOME}/.profile
bash: shell
	ln -fs $(DOTFILES)/bash/bashrc ${HOME}/.bashrc
	ln -fs $(DOTFILES)/bash/bashenv ${HOME}/.bashenv
	ln -fs $(DOTFILES)/bash/bashrc ${HOME}/.bashrc
	ln -fs $(DOTFILES)/bash/bashprofile ${HOME}/.bash_profile
zsh: shell
	ln -fs $(DOTFILES)/zsh/zshrc ${HOME}/.zshrc
	ln -fs $(DOTFILES)/zsh/zlogout ${HOME}/.zlogout
	ln -fs $(DOTFILES)/zsh/zshenv ${HOME}/.zshenv
	git -C ${HOME}/.oh-my-zsh pull || \
		git clone https://github.com/robbyrussell/oh-my-zsh.git ${HOME}/.oh-my-zsh
	git -C ${HOME}/.oh-my-zsh/custom/themes/powerlevel9k pull || \
		git clone https://github.com/bhilburn/powerlevel9k.git ${HOME}/.oh-my-zsh/custom/themes/powerlevel9k
	git -C ${HOME}/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting pull || \
		git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${HOME}/.oh-my-zsh/custom/plugins/zsh-syntax-highlighting
screen:
	ln -fs $(DOTFILES)/rc/screenrc ${HOME}/.screenrc
tmux:
	ln -fs $(DOTFILES)/rc/tmux.conf ${HOME}/.tmux.conf
vim:
	touch ${HOME}/.netrc
	mkdir -p ${HOME}/.cache/nvim/undo
	mkdir -p ${HOME}/.config/nvim/
	ln -fns $(DOTFILES)/vim ${HOME}/.vim
	ln -fs $(DOTFILES)/nvim/init.vim ${HOME}/.config/nvim/init.vim
	ln -fs $(DOTFILES)/nvim/init.vim ${HOME}/.vimrc
	mkdir -p $(HOME)/.local/share/nvim/site/autoload
	ln -fs $(DOTFILES)/vim/autoload/plug.vim ${HOME}/.local/share/nvim/site/autoload/plug.vim
	mkdir -p $(HOME)/.local/share/nvim/plugged
	nvim --headless +PlugInstall +qa || echo 'no nvim installed or command failed'
	vim -E -c "PlugInstall" -c "qa" || echo 'no vim installed or command failed'
X:
	ln -fns $(DOTFILES)/rc/Xresources ${HOME}/.Xresources
	ln -fns $(DOTFILES)/rc/Xresources ${HOME}/.Xdefaults
	ln -fns $(DOTFILES)/rc/xinitrc ${HOME}/.xinitrc
	ln -fns $(DOTFILES)/rc/xsessionrc ${HOME}/.xsessionrc
	ln -fns $(DOTFILES)/rc/xscreensaver ${HOME}/.xscreensaver
ruby:
	ln -fs $(DOTFILES)/ruby/irbrc ${HOME}/.irbrc
	ln -fs $(DOTFILES)/ruby/pryrc ${HOME}/.pryrc
	ln -fs $(DOTFILES)/ruby/rdebugrc ${HOME}/.rdebugrc
	ln -fs ${DOTFILES}/ruby/gemrc ${HOME}/.gemrc
	ln -fs ${DOTFILES}/ruby/rspec ${HOME}/.rspec
git:
	ln -fs $(DOTFILES)/git/gitconfig ${HOME}/.gitconfig
	ln -fs $(DOTFILES)/git/gitignore ${HOME}/.gitignore
	ln -fs $(DOTFILES)/git/gitcommit ${HOME}/.gitcommit
chunk:
	ln -fs $(DOTFILES)/chunk/skhdrc ${HOME}/.skhdrc
	ln -fs $(DOTFILES)/chunk/chunkwmrc ${HOME}/.chunkwmrc
i3:
	mkdir -p ${HOME}/.config/i3
	ln -fs $(DOTFILES)/i3/config ${HOME}/.config/i3/config
polybar:
	mkdir -p ${HOME}/.config/polybar
	ln -fs $(DOTFILES)/polybar/config ${HOME}/.config/polybar/config
	ln -fs $(DOTFILES)/polybar/launch.sh ${HOME}/.config/polybar/launch.sh
oni:
	mkdir -p ${HOME}/.config/oni
	ln -fs $(DOTFILES)/oni/config.js ${HOME}/.config/oni/config.js
	ln -fs $(DOTFILES)/oni/config.tsx ${HOME}/.config/oni/config.tsx
bspwm:
	mkdir -p ${HOME}/.config/bspwm
	mkdir -p ${HOME}/.config/sxhkd
	ln -fs $(DOTFILES)/bspwm/bspwmrc ${HOME}/.config/bspwm/bspwmrc
	ln -fs $(DOTFILES)/bspwm/sxhkdrc ${HOME}/.config/sxhkd/sxhkdrc
kitty:
	mkdir -p ${HOME}/.config/kitty
	ln -fs $(DOTFILES)/kitty/kittyconf ${HOME}/.config/kitty/kitty.conf
qute:
	mkdir -p ${HOME}/.config/qutebrowser
	ln -fs $(DOTFILES)/qute/config.py ${HOME}/.config/qutebrowser/config.py
