DOTFILES := $(shell pwd)
all: shell tmux screen ruby X vim git _atom
shell:
	ln -fs $(DOTFILES)/bash/bashrc ${HOME}/.bashrc
	ln -fs $(DOTFILES)/bash/bashenv ${HOME}/.bashenv
	ln -fs $(DOTFILES)/bash/bashrc ${HOME}/.bashrc
	ln -fs $(DOTFILES)/profile ${HOME}/.bash_profile
	ln -fs $(DOTFILES)/profile ${HOME}/.zprofile
	ln -fs $(DOTFILES)/bash/homebrew_profile ${HOME}/.homebrew.profile
	ln -fns $(DOTFILES)/bin/ ${HOME}/bin
	sh ${DOTFILES}/zsh/oh_my_zsh ${DOTFILES}
	ln -fs $(DOTFILES)/zsh/zshrc ${HOME}/.zshrc
	ln -fs $(DOTFILES)/zsh/zlogout ${HOME}/.zlogout
	ln -fs $(DOTFILES)/zsh/zshenv ${HOME}/.zshenv
	ln -fs $(DOTFILES)/friends ${HOME}/.friends
	ln -fs $(DOTFILES)/ack/ackrc ${HOME}/.ackrc
	ln -fs $(DOTFILES)/ctags ${HOME}/.ctags
	ln -fns $(DOTFILES)/etc/ ${HOME}/etc
	ln -fs ${DOTFILES}/bash/alias ${HOME}/.alias
	sh ${DOTFILES}/bash/ssh-config ${DOTFILES}
screen:
	ln -fs $(DOTFILES)/rc/screenrc ${HOME}/.screenrc
tmux:
	ln -fs $(DOTFILES)/rc/tmux.conf ${HOME}/.tmux.conf
vim:
	ln -fns $(DOTFILES)/vim ${HOME}/.vim
	ln -fs $(DOTFILES)/vim/vimrc ${HOME}/.vimrc
	ln -fs $(DOTFILES)/vim/vimrc.bundles ${HOME}/.vimrc.bundles
	ln -fs $(DOTFILES)/vim/vimrc.neocomplete ${HOME}/.vimrc.neocomplete
	ln -fs $(DOTFILES)/vim/gvimrc ${HOME}/.gvimrc
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
_atom:
	mkdir -p $(HOME)/.atom
	ln -fs $(DOTFILES)/atom/keymap.cson ${HOME}/.atom/keymap.cson
	ln -fs $(DOTFILES)/atom/config.cson ${HOME}/.atom/config.cson
	apm install --packages-file $(DOTFILES)/atom/package-list.txt
atom_freeze:
	apm list --installed --bare > $(DOTFILES)/atom/package-list.txt
