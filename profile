#!/usr/bin/env sh

# if running bash
if [ -n "$BASH_VERSION" ]; then
    # include .bashrc if it exists
    if [ -f "$HOME/.bashrc" ]; then
        . "$HOME/.bashrc"
    fi
fi

## set PATH so it includes user's private bin if it exists
if [[ -d "$HOME/bin" ]] ; then
    PATH="$HOME/bin:$PATH"
fi

if [[ -d "$HOME/.files/bin" ]] ; then
    PATH="$HOME/.files/bin:$PATH"
fi

export PATH="$HOME/sbin:/usr/local/bin:$PATH:/usr/local/git/bin:/usr/local/sbin"

## Editor
if [[ -s $(which mvim) ]]; then
  export EDITOR=mvim
  export VISUAL=mvim
else
  export EDITOR=vim
  export VISUAL=vim
fi

export HISTFILESIZE=9999
export HISTSIZE=9999

source "$HOME/.alias"

export JAVA_HOME="/Library/Internet Plug-Ins/JavaAppletPlugin.plugin/Contents/Home"
export PATH=/usr/local/redis/bin:$PATH
export GOPATH=$HOME/go
export PATH=$HOME/bin:$PATH # shift in custom bins
export PATH=$GOPATH/bin:$PATH # shiftin GOPATH bins
export GIT_SSH="$HOME/bin/git-ssh"
export GO15VENDOREXPERIMENT=1

# added by travis gem
[ -f /Users/jlane/.travis/travis.sh ] && source /Users/jlane/.travis/travis.sh

# chruby
source /usr/local/opt/chruby/share/chruby/chruby.sh
source /usr/local/opt/chruby/share/chruby/auto.sh

chruby 2.3

export GPG_TTY=`tty`
