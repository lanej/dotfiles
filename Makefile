DOTFILES := $(shell pwd)
all: shell screen perl ruby X mail vimfiles
shell:
	ln -fs $(DOTFILES)/bash/bashrc ${HOME}/.bashrc
	ln -fs $(DOTFILES)/bash/bashenv ${HOME}/.bashenv
	ln -fs $(DOTFILES)/bash/bashrc ${HOME}/.bashrc
	ln -fs $(DOTFILES)/bash/bash_profile ${HOME}/.profile
	ln -fs $(DOTFILES)/bash/bash_profile ${HOME}/.bash_profile
	ln -fs $(DOTFILES)/bash/git_completion.sh ${HOME}/.git_completion.sh
	ln -fs $(DOTFILES)/zshrc ${HOME}/.zshrc
	ln -fs $(DOTFILES)/zlogout ${HOME}/.zlogout
	ln -fs $(DOTFILES)/zshenv ${HOME}/.zshenv
	ln -fs $(DOTFILES)/friends ${HOME}/.friends
	#ln -fs $(DOTFILES)/gpg.conf ${HOME}/.gnupg/gpg.conf
	ln -fs $(DOTFILES)/ack/ackrc ${HOME}/.ackrc
screen:
	ln -fs $(DOTFILES)/screenrc ${HOME}/.screenrc
perl:
	ln -fs $(DOTFILES)/perltidyrc ${HOME}/.perltidyrc
vimfiles:
	ln -fns $(DOTFILES)/vim ${HOME}/.vim
	ln -fs $(DOTFILES)/vim/vimrc ${HOME}/.vimrc
	ln -fs $(DOTFILES)/vim/gvimrc ${HOME}/.gvimrc
X:
	ln -fns $(DOTFILES)/Xresources ${HOME}/.Xresources
	ln -fs $(DOTFILES)/Xresources ${HOME}/.Xdefaults
mail:
	ln -fs $(DOTFILES)/muttrc ${HOME}/.muttrc
ruby:
	ln -fs $(DOTFILES)/ruby/irbrc ${HOME}/.irbrc
	ln -fs $(DOTFILES)/ruby/rdebugrc ${HOME}/.rdebugrc
