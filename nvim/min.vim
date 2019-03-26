"
"   ██╗███╗   ██╗██╗████████╗██╗   ██╗██╗███╗   ███╗
"   ██║████╗  ██║██║╚══██╔══╝██║   ██║██║████╗ ████║
"   ██║██╔██╗ ██║██║   ██║   ██║   ██║██║██╔████╔██║
"   ██║██║╚██╗██║██║   ██║   ╚██╗ ██╔╝██║██║╚██╔╝██║
"   ██║██║ ╚████║██║   ██║██╗ ╚████╔╝ ██║██║ ╚═╝ ██║
"   ╚═╝╚═╝  ╚═══╝╚═╝   ╚═╝╚═╝  ╚═══╝  ╚═╝╚═╝     ╚═╝

" ================ General Config ====================
set autoread                   " Reload files changed outside vim
set backspace=indent,eol,start " Allow backspace in insert mode
set cmdheight=2
set cursorline
set encoding=utf-8
set exrc
set fileformats+=mac
set guicursor=a:blinkon0       " Disable cursor blink
set hidden                     " Better buffer management
set history=10000              " Store lots of :cmdline history
set hlsearch
set ignorecase                 " Ignore case when searching
if (has("nvim"))
  set inccommand=nosplit       " live replace
endif
set incsearch                  " Makes search act like search in modern browsers
set lazyredraw                 " Don't redraw while executing macros (good performance config)
set magic                      " For regular expressions turn magic on
set matchtime=2                " How many tenths of a second to blink when matching brackets
set modelines=5
set nobackup
set nocursorline               " Highlight current line !!! disabled, runs slow
set number                     " Line numbers are good
set scrolloff=7                " Set 7 lines to the cursor - when moving vertically using j/k
set secure
set shell=$SHELL
set showcmd                    " Show incomplete cmds down the bottom
set showmatch                  " Show matching brackets when text indicator is over them
set showmode                   " Show current mode down the bottom
set smartcase                  " When searching try to be smart about cases
set smarttab
set tabpagemax=15              " Only show 15 tabs
set title                      " Set the title in xterm
set ttimeout
set ttimeoutlen=100
set visualbell                 " No sounds

if $OS != "Linux"
  set termguicolors
endif

" ================ Turn Off Swap Files ==============
set noswapfile
set nobackup
set nowritebackup

" Trailing spaces and tabs
set list
set listchars=tab:>-,trail:*,nbsp:*

let mapleader = ','

" Enable filetype plugins to handle indents
filetype plugin indent on

" plugins:begin
let g:plug_url_format="git://github.com/%s"

" allow separate plugins per editor
call plug#begin('~/.local/share/nvim/min')

" show git diffs in left gutter
Plug 'airblade/vim-gitgutter'
" colorscheme
Plug 'jacoborus/tender.vim'
" syntax highlighting
Plug 'sheerun/vim-polyglot', { 'do': './build' }
" git integration
Plug 'tpope/vim-fugitive'
" additional editing commands
Plug 'tpope/vim-surround'

" Add plugins to &runtimepath
call plug#end()

" plugins:end

" plugin-config start

" vim-plug
map <leader>pi :PlugInstall<CR>
map <leader>pc :PlugClean<CR>
map <leader>pu :PlugUpdate<CR>

" plugin-config end

" =============== UI ================
syntax enable      " turn syntax highlighting on
colorscheme tender " set that smooth smooth color scheme
set guioptions-=T  " remove Toolbar
set guioptions-=r  " remove right scrollbar
set guioptions-=L  " remove left scrollbar
set number         " show line numbers
set laststatus=2   " Prevent the ENTER prompt more frequently

" contrasting visual selection
hi Visual guifg=#ffffff guibg=DarkGrey gui=none
hi Visual ctermfg=LightGray ctermbg=DarkGrey cterm=none

highlight clear LineNr     " Current line number row will have same background color in relative mode
highlight clear SignColumn " SignColumn should match background

set completeopt=noinsert,noselect

" ================ Scrolling ========================
set scrolloff=8         "Start scrolling when we're 8 lines away from margins
set sidescrolloff=15
set sidescroll=1

" ================ Status Line ======================
if has('cmdline_info')
  set showcmd " Show partial commands in status line and selected characters/lines in visual mode
endif

" disable ex mode
:map Q <Nop>

" Set minimum window height
set winheight=10

" Wrapped lines goes down/up to next row, rather than next line in file.
noremap j gj
noremap k gk

" If I don't let off the shift key quick enough
command! Q :q
command! W :w
command! Wa :wa
command! Wqa :wqa
command! E :e
