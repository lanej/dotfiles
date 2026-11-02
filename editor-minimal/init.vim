" Shared Vim/Neovim configuration for hosts with an existing editor.
set nocompatible

" Use only the editor's bundled runtime, even after a workstation install.
set noloadplugins
let &runtimepath = $VIMRUNTIME
if exists('+packpath')
  let &packpath = ''
endif
filetype plugin indent on
syntax enable

let mapleader = ','
set number
set hidden
set expandtab
set tabstop=2
set softtabstop=2
set shiftwidth=2
set autoindent
set backspace=indent,eol,start
set ignorecase
set smartcase
set incsearch
set hlsearch
set scrolloff=5
set sidescrolloff=5
set splitbelow
set splitright
set wildmenu
set wildmode=list:longest,full
set laststatus=2
set nomodeline
set noexrc
set mouse=

nnoremap <silent> <Leader>w :write<CR>
nnoremap <silent> <Leader>x :xit<CR>
nnoremap <silent> <Leader><Space> :nohlsearch<CR>
nnoremap <silent> <Leader>bo :bprevious<CR>
nnoremap <silent> <Leader>bi :bnext<CR>
nnoremap <silent> [q :cprevious<CR>
nnoremap <silent> ]q :cnext<CR>
nnoremap j gj
nnoremap k gk
nnoremap <C-h> <C-w>h
nnoremap <C-j> <C-w>j
nnoremap <C-k> <C-w>k
nnoremap <C-l> <C-w>l
