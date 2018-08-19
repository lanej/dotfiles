.PHONY: fish shell screen tmux vim nvim X ruby git chunk awesome i3 polybar oni
all: .PHONY

DOTFILES := $(shell pwd)

fish:
	mkdir -p ${HOME}/.config/fish/functions
	ln -fs $(DOTFILES)/fish/config ${HOME}/.config/fish/config.fish
	$(shell for f in $(DOTFILES)/fish/functions/*; do ln -fs $$f ~/.config/fish/functions/; done)
shell:
	touch ${HOME}/.keys.env
	ln -fs $(DOTFILES)/bash/bashrc ${HOME}/.bashrc
	ln -fs $(DOTFILES)/bash/bashenv ${HOME}/.bashenv
	ln -fs $(DOTFILES)/bash/bashrc ${HOME}/.bashrc
	ln -fs $(DOTFILES)/bash/bashprofile ${HOME}/.bash_profile
	ln -fs $(DOTFILES)/zsh/zprofile ${HOME}/.zprofile
	ln -fs $(DOTFILES)/sh/homebrew.profile ${HOME}/.homebrew.profile
	ln -fs $(DOTFILES)/sh/rc ${HOME}/.rc
	ln -fs $(DOTFILES)/sh/profile ${HOME}/.profile
	ln -fns $(DOTFILES)/bin/ ${HOME}/bin
	sh ${DOTFILES}/zsh/oh_my_zsh ${DOTFILES}
	ln -fs $(DOTFILES)/zsh/zshrc ${HOME}/.zshrc
	ln -fs $(DOTFILES)/zsh/zlogout ${HOME}/.zlogout
	ln -fs $(DOTFILES)/zsh/zshenv ${HOME}/.zshenv
	ln -fs $(DOTFILES)/ctags ${HOME}/.ctags
	ln -fns $(DOTFILES)/etc/ ${HOME}/etc
	ln -fs ${DOTFILES}/bash/alias ${HOME}/.alias
screen:
	ln -fs $(DOTFILES)/rc/screenrc ${HOME}/.screenrc
tmux:
	ln -fs $(DOTFILES)/rc/tmux.conf ${HOME}/.tmux.conf
vim:
	touch ${HOME}/.netrc
	ln -fns $(DOTFILES)/vim ${HOME}/.vim
	ln -fns $(DOTFILES)/vim ${HOME}/.nvim
	ln -fs $(DOTFILES)/vim/vimrc ${HOME}/.vimrc
	ln -fs $(DOTFILES)/vim/vimrc.bundles ${HOME}/.vimrc.bundles
	ln -fs $(DOTFILES)/vim/vimrc.neocomplete ${HOME}/.vimrc.neocomplete
	ln -fs $(DOTFILES)/vim/gvimrc ${HOME}/.gvimrc
nvim:
	mkdir -p ${HOME}/.cache/nvim/undo
	mkdir -p ${HOME}/.config/nvim/
	ln -fs $(DOTFILES)/nvim/init.vim ${HOME}/.config/nvim/init.vim
	mkdir -p $(HOME)/.local/share/nvim/site/autoload
	ln -fs $(DOTFILES)/vim/autoload/plug.vim ${HOME}/.local/share/nvim/site/autoload/plug.vim
	mkdir -p $(HOME)/.local/share/nvim/plugged
	nvim --headless +PlugInstall +qa || echo 'no nvim installed'
X:
	ln -fns $(DOTFILES)/rc/Xresources ${HOME}/.Xresources
	ln -fs $(DOTFILES)/rc/Xresources ${HOME}/.Xdefaults
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
