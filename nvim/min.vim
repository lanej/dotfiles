" 888b     d888 8888888 888b    888    888     888 8888888 888b     d888 
" 8888b   d8888   888   8888b   888    888     888   888   8888b   d8888 
" 88888b.d88888   888   88888b  888    888     888   888   88888b.d88888 
" 888Y88888P888   888   888Y88b 888    Y88b   d88P   888   888Y88888P888 
" 888 Y888P 888   888   888 Y88b888     Y88b d88P    888   888 Y888P 888 
" 888  Y8P  888   888   888  Y88888      Y88o88P     888   888  Y8P  888 
" 888   "   888   888   888   Y8888 d8b   Y888P      888   888   "   888 
" 888       888 8888888 888    Y888 Y8P    Y8P     8888888 888       888 

set autoread                   " Reload files changed outside vim
set autoindent
set backspace=indent,eol,start " Allow backspace in insert mode
set cmdheight=2
set cursorline
set encoding=utf-8
set exrc
set fileformats+=mac
set guicursor=n-v-c:block-Cursor
set guicursor+=i:ver100-iCursor
set guicursor+=n-v-c:blinkon0
set hidden                     " Better buffer management
set history=10000              " Store lots of :cmdline history
set hlsearch
set ignorecase                 " Ignore case when searching
set incsearch                  " Makes search act like search in modern browsers
" set lazyredraw                 " Don't redraw while executing macros (good performance config)
set completeopt=menu,menuone,noselect,preview,noinsert
set magic                      " For regular expressions turn magic on
set modelines=5
set nobackup
set scrolloff=7                " Set 7 lines to the cursor - when moving vertically using j/k
set shell=$SHELL
set showcmd                    " Show incomplete cmds down the bottom
set showmatch                  " Show matching brackets when text indicator is over them
set matchtime=2                " How many tenths of a second to blink when matching brackets
set showmode                   " Show current mode down the bottom
set smartcase                  " When searching try to be smart about cases
set smarttab
set tabpagemax=15              " Only show 15 tabs
set title                      " Set the title in xterm
set ttimeout
set ttimeoutlen=50
set novb
set noeb
set equalalways                " Maintain consistent window sizes
set updatetime=300
set nospell
set shortmess+=c
set shortmess+=T
set shortmess+=a
set shortmess+=W
set noswapfile
set nobackup
set nowritebackup
set wrap
set list
set listchars=tab:→\ ,nbsp:␣,trail:•,precedes:«,extends:»
exe "set cedit=<C-v>"

let mapleader = ','

set inccommand=nosplit       " live replace
set termguicolors

" searching stuff

" Make <C-L> clear highlight and redraw
nnoremap <C-\> :nohls<CR>
inoremap <C-\> <C-O>:nohls<CR>
" nnoremap * :keepjumps normal *``<cr>
nnoremap * *``

" Edit the vimrc file
nnoremap ev  :e $MYVIMRC<CR>
nnoremap evr :source  $MYVIMRC<CR>
nnoremap evp :e  ~/.config/nvim/lua/plugins.lua<CR>
nnoremap tt  :tablast<CR>
nnoremap te  :tabedit<Space>
nnoremap tn  :tabnext<CR>
nnoremap tp  :tabprev<CR>
nnoremap tc  :tabnew<CR>
nnoremap tm  :tabm<Space>
nnoremap tx  :tabclose<CR>
nnoremap t1  1gt<CR>
nnoremap t2  2gt<CR>
nnoremap t3  3gt<CR>
nnoremap t4  4gt<CR>
nnoremap t5  5gt<CR>
nnoremap t6  6gt<CR>
nnoremap fbk :bd!<CR>
nnoremap fak :%bd!<bar>e#<CR>
nnoremap <leader>bo  :bp<CR>
nnoremap <leader>bi  :bn<CR>

" Enable filetype plugins to handle indents
filetype plugin indent on

" plugin-config start
map <silent><leader>w :w<CR>
" map <leader>w! :SudoWrite<CR>
map <silent><leader>x :x<CR>

" vim-plug
map <silent><leader>vpi :PackerInstall<CR>
map <silent><leader>vpc :PackerClean<CR>
map <silent><leader>vpu :PackerSync<CR>

map <silent><leader>rb :%s/<C-r><C-w>/
map <silent><leader>rq :cfdo %s/<C-r><C-w>/

let g:markdown_fenced_languages = ['html', 'python', 'bash=sh', 'ruby', 'go']

let g:gutentags_enabled = 1
let g:gutentags_exclude_filetypes = ['gitcommit', 'gitrebase']
let g:gutentags_generate_on_empty_buffer = 0
let g:gutentags_ctags_exclude = [
      \ '.eggs',
      \ '.mypy_cache',
      \ 'venv',
      \ 'tags',
      \ 'tags.temp',
      \ '.ijwb',
      \ 'bazel-*',
      \ ]
let g:gutentags_project_info = []
call add(g:gutentags_project_info, {'type': 'ruby', 'file': '.solargraph.yml'})

" quickfix nav
nnoremap ]q :cnext<CR>
nnoremap [q :cprev<CR>

tnoremap <C-o> <C-\><C-n>
nnoremap yd :let @" = expand("%")<cr>
syntax enable      " turn syntax highlighting on
set guioptions-=T  " remove Toolbar
set guioptions-=r  " remove right scrollbar
set guioptions-=L  " remove left scrollbar
set number         " show line numbers
set laststatus=2   " Prevent the ENTER prompt more frequently
set scrolloff=8         "Start scrolling when we're 8 lines away from margins
set sidescrolloff=15
set sidescroll=1

" ================ Status Line ======================
if has('cmdline_info')
  set showcmd " Show partial commands in status line and selected characters/lines in visual mode
endif

" other cwd configs
map <leader>ct :cd %:p:h<CR>
map <leader>cg :Gcd<CR>

" disable ex mode
:map Q <Nop>

" Helpers
map <leader>srt :!sort<CR>
map <leader>uq :!uniq<CR>

" Wrapped lines goes down/up to next row, rather than next line in file.
noremap j gj
noremap k gk

" If I don't let off the shift key quick enough
command! Q :q
command! Qa :qa
command! W :w
command! Wa :wa
command! Wqa :wqa
command! Qwa :wqa
command! E :e

" Realign the whole file
map <leader>D ggVG=<CR>
nnoremap <Leader>m :make!<CR>

" create parent directories on write
if !exists("*s:MkNonExDir")
  function s:MkNonExDir(file, buf)
    if empty(getbufvar(a:buf, '&buftype')) && a:file!~#'\v^\w+\:\/'
      let dir=fnamemodify(a:file, ':h')
      if !isdirectory(dir)
        call mkdir(dir, 'p')
      endif
    endif
  endfunction
endif

set undofile " Maintain undo history between sessions

if has('conceal')
  set conceallevel=0 concealcursor=niv
endif

let g:ale_fixers = {

nnoremap <silent><leader>ee :e .env<CR>
nnoremap <silent><leader>eo :e .env-override<CR>

if has('autocmd')
  au FocusGained * :redraw!

  " jsx is both javascript and jsx
  " au BufNewFile,BufRead *.jsx set filetype=javascript.jsx
  " Save files when vim loses focus
  " au FocusLost,BufLeave * silent! wa
  " Default spellcheck off
  " au BufRead,BufNewFile,BufEnter * set nospell|set textwidth=0|set number
  " Source .env files
  au DirChanged * call SourceEnvOnDirChange()
  au VimEnter * call SourceEnv()

  augroup filetype_terminal
    if has('nvim')
      autocmd TermEnter * set nospell|set nonumber|setlocal wrap
      if (exists("+termguicolors"))
        autocmd TermEnter,TermOpen * set termguicolors
      endif
    endif
  augroup END

  augroup filetype_markdown
    au!
    au BufNewFile,BufNewFile,BufRead qutebrowser-editor* set filetype=markdown
    au FileType markdown set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set spell|set conceallevel=0|set wrap
  augroup END

  augroup filetype_ruby
    au!
    au FileType ruby map <silent><leader>df :ALEFix<CR>
    au FileType ruby map <silent><leader>da :!bundle exec rubocop -ADES %:p<CR>
    au FileType ruby map <silent><C-p> <Plug>(ale_previous_wrap)
    au FileType ruby map <silent><C-n> <Plug>(ale_next_wrap)
    au FileType ruby set shiftwidth=2|set tabstop=2|set softtabstop=2|set expandtab|set autoindent
    au FileType ruby map <leader>tq :TestLast --fail-fast<CR>
    au FileType ruby map <leader>to :TestLast --only-failures<CR>
    au FileType ruby map <leader>tn :TestLast -n<CR>
    au FileType ruby map <leader>tv :call <SID>vcr_failures_only()<CR>
    " old style symbol keys to new style symbol keys
    au FileType ruby vnoremap <Bslash>hl :s/\v:([^ ]*)\s\=\>/\1:/g<CR>
    " new style symbol keys to string keys
    au FileType ruby vnoremap <Bslash>hr :s/\v(\w+):/"\1" =>/g<CR>
    " string keys to new style symbol keys
    au FileType ruby vnoremap <Bslash>hs :s/\v[\"\'](\w+)[\"\']\s+\=\>\s+/\1\: /g<CR>
    " symbol string keys to string keys
    au FileType ruby vnoremap <Bslash>hj :s/\v\"(\w+)\":\s+/"\1" => /g<CR>
  augroup END

  augroup filetype_python
    au!
    au FileType python map <leader>tv :TestFile --ff -x<CR>
    au FileType python map <leader>tj :TestFile --ff<CR>
    au FileType python map <leader>tn :TestFile --lf -x<CR>
    au FileType python map <leader>td :TestFile --pdb<CR>
    au FileType python map <leader>tlv :TestLast --ff -x<CR>
    au FileType python map <leader>tlj :TestLast --ff<CR>
    au FileType python map <leader>tln :TestLast --lf -x<CR>
    au FileType python map <leader>tld :TestLast --pdb<CR>
  augroup END

  augroup filetype_lua
    au! FileType lua map <leader>tj :TestFile --no-keep-going<CR>
    au FileType lua set colorcolumn=100|set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set nospell
    au FileType lua map <leader>d :ALEFix<CR>
  augroup END

  augroup filetype_gitcommit
    au! FileType gitcommit set colorcolumn=73|set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set spell|set wrap
  augroup END

  au! FileType git set nofoldenable

  augroup filetype_go
    au!
    au FileType go set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set nospell
    au FileType go nmap <silent> <leader><t-d> :call DebugNearest()<CR>
  augroup END

  au! FileType rust set makeprg=cargo\ run|set colorcolumn=100

  augroup filetype_javascript
    au!
    au FileType javascript set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
    au BufNewFile,BufRead .eslintrc set filetype=json
    au FileType javascript nnoremap <leader>d :ALEFix<CR>
  augroup END

  augroup filetype_haml
    autocmd FileType haml set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
  augroup END

  augroup filetype_sshconfig
    autocmd FileType sshconfig set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
  augroup END

  augroup filetype_json
    autocmd FileType json set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
  augroup END

  augroup filetype_yaml
    autocmd FileType yaml set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
  augroup END

  augroup filetype_fish
    autocmd FileType fish set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
  augroup END

  augroup filetype_perl
    autocmd FileType perl set tabstop=8|set shiftwidth=8|set noexpandtab|set nolist
  augroup END

  augroup filetype_sshconfig
    autocmd FileType sshconfig set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
  augroup END

  augroup filetype_sh
    autocmd BufNewFile,BufRead .alias set filetype=sh
  augroup END

  augroup filetype_vim
    autocmd FileType vim set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set nospell
  augroup END

  augroup BWCCreateDir
    au! BufWritePre * :call s:MkNonExDir(expand('<afile>'), +expand('<abuf>'))
  augroup END
endif

" " Copy to clipboard
vnoremap  <leader>y  "+y
nnoremap  <leader>Y  "+yg_
nnoremap  <leader>y  "+y
nnoremap  <leader>yy  "+yy

" " Paste from clipboard
nnoremap <leader>p "+p
nnoremap <leader>P "+P
vnoremap <leader>p "+p
vnoremap <leader>P "+P

set secure
