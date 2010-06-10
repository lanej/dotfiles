" display settings
set t_Co=256
colorscheme wombat256

set vb t_vb=
set background=dark
syntax on
set ruler
set hlsearch

" Text Handling
set nowrap
set nocompatible
set ts=4
set sw=4
set expandtab
set ai

" Status Line
set statusline=%F%m%r%h%w\ [f:%{&ff}\ t:%Y]\ [A:\%03.3b\ H:\%02.2B]\ [P:%04l,%04v][%p%%]\ [LEN=%L]
set laststatus=2

" file schtuff
set fileformat=unix
set nobackup
filetype plugin indent on

" navigation
map <silent><A-Right> :tabnext<CR>
map <silent><A-Left> :tabprevious<CR>

" NT bindings
map nt :NERDTree<CR>
map ntm :NERDTreeMirror<CR>
map ntc :NERDTreeClose<CR>

nnoremap <F2> :set nonumber!<CR>:set foldcolumn=0<CR>
