"
"   ██╗███╗   ██╗██╗████████╗██╗   ██╗██╗███╗   ███╗
"   ██║████╗  ██║██║╚══██╔══╝██║   ██║██║████╗ ████║
"   ██║██╔██╗ ██║██║   ██║   ██║   ██║██║██╔████╔██║
"   ██║██║╚██╗██║██║   ██║   ╚██╗ ██╔╝██║██║╚██╔╝██║
"   ██║██║ ╚████║██║   ██║██╗ ╚████╔╝ ██║██║ ╚═╝ ██║
"   ╚═╝╚═╝  ╚═══╝╚═╝   ╚═╝╚═╝  ╚═══╝  ╚═╝╚═╝     ╚═╝

set autoread                   " Reload files changed outside vim
set background=dark
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
set lazyredraw                 " Don't redraw while executing macros (good performance config)
set magic                      " For regular expressions turn magic on
set modelines=5
set nobackup
set scrolloff=7                " Set 7 lines to the cursor - when moving vertically using j/k
set secure
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
set list
set listchars=tab:→\ ,nbsp:␣,trail:•,precedes:«,extends:»
exe "set cedit=<C-V>"

let mapleader = ','

let g:coq_settings = {
      \ 'auto_start': 'shut-up',
      \ 'keymap.jump_to_mark': '<c-b>',
      \ 'clients.buffers.match_syms': v:true,
      \ }

lua require('plugins')

colorscheme tender

call plug#begin(stdpath('data') . '/plugged')
Plug 'AndrewRadev/splitjoin.vim'
Plug 'ludovicchabant/vim-gutentags'
call plug#end()

set inccommand=nosplit       " live replace

if (exists("+termguicolors"))
  set termguicolors
endif

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

" Enable filetype plugins to handle indents
filetype plugin indent on

" plugin-config start
map <leader>w :w<CR>
" map <leader>w! :SudoWrite<CR>
map <leader>x :x<CR>

" vim-plug
map <leader>vpi :PackerInstall<CR>
map <leader>vpc :PackerClean<CR>
map <leader>vpu :PackerSync<CR>

map <leader>rb :%s/<C-r><C-w>/
map <leader>rq :cfdo %s/<C-r><C-w>/

let g:vim_markdown_conceal = 0
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

" terraform
let g:terraform_completion_keys = 1
let g:terraform_fmt_on_save     = 1
let g:terraform_align           = 1
let g:terraform_remap_spacebar  = 0

" sessions
map <leader>ps :Prosession<space>
let g:prosession_per_branch = 1

map <leader>ntt :NvimTreeToggle<CR>
map <leader>ntc :NvimTreeClose<CR>
map <leader>ntf :NvimTreeFindFile<CR>

let g:indent_blankline_show_current_context = v:true
let g:indent_blankline_use_treesitter = v:true

map <leader>gl :Gitsigns blame_line<CR>

nnoremap <leader>gm :Git mergetool<CR>
nnoremap <leader>go :GBrowse<CR>
nnoremap <leader>gt :Gcommit -am'wip'<CR>
nnoremap <leader>gs :Git<CR>
nnoremap <leader>gw :Gwrite<CR>
nnoremap <leader>gr :Gread<CR>
nnoremap <leader>ga :Gcommit -av<CR>
nnoremap <leader>gd :Gdiffsplit origin/master
nnoremap <leader>gb :Git blame<CR>
nnoremap <leader>gp :Git push<CR>

map <leader>re :Rename<space>

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

" Start interactive EasyAlign in visual mode (e.g. vip<Enter>)
vmap <Enter> <Plug>(EasyAlign)
" Realign the whole file
map <leader>= ggVG=<CR>

let g:clang_format#style_options = {
      \ "AccessModifierOffset" : -4,
      \ "AllowShortIfStatementsOnASingleLine" : "true",
      \ "AlwaysBreakTemplateDeclarations" : "true",
      \ "Standard" : "C++11"}

set makeprg="make -j9"
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
if has('nvim-0.5.0')
  set undodir=~/.cache/nvim-head/undo
else
  set undodir=~/.cache/nvim/undo
endif

if has('conceal')
  set conceallevel=0 concealcursor=niv
endif

let g:ale_fixers = {
      \ 'ruby': ['rubocop'],
      \ 'rspec': ['rubocop'],
      \ 'javascript.jsx': ['eslint'],
      \ 'javascript': ['eslint'],
      \ 'json': ['jq'],
      \ 'lua': ['lua-format'],
      \ }

let g:ale_linters = {
      \ 'ruby': ['rubocop'],
      \ 'rspec': ['rubocop'],
      \ 'javascript.jsx': ['eslint'],
      \ 'javascript': ['eslint'],
      \ }

let g:ale_keep_list_window_open = 0
let g:ale_lint_delay = 200
let g:ale_lint_on_enter = 1
let g:ale_lint_on_save = 1
let g:ale_lint_on_text_changed = 'always'
let g:ale_open_list = 0
let g:ale_ruby_bundler_executable = 'bundle'
let g:ale_ruby_rubocop_executable = 'bundle'
let g:ale_set_highlights = 1
let g:ale_set_loclist = 0
let g:ale_linters_explicit = 1
let g:ale_set_quickfix = 0
let g:ale_set_signs = 1
let g:ale_sign_column_always = 1
let g:ale_sign_error = '>>'
let g:ale_sign_offset = 1000000
let g:ale_sign_warning = '--'
let g:ale_completion_enabled = 0
let g:ale_virtualtext_cursor = 1

augroup filetype_ale
  autocmd!
  autocmd FileType ruby,lua map <leader>d :ALEFix<CR>
  autocmd FileType ruby nmap <silent><C-p> <Plug>(ale_previous_wrap)
  autocmd FileType ruby nmap <silent><C-n> <Plug>(ale_next_wrap)
augroup END

augroup packer_user_config
  autocmd!
  autocmd BufWritePost plugins.lua source <afile> | PackerCompile
augroup end

map gm :TSHighlightCapturesUnderCursor<CR>

let g:jedi#auto_initialization = 0

function! SourceEnvOnDirChange()
  if has_key(v:event, "cwd")
    let sources = SourceEnv()
    if sources
      echo "reloaded env"
    end
  end
endfunction

function! SourceEnv()
  let loaded=0
  if filereadable(".env")
    let loaded=1
    silent! Dotenv .env
  endif

  if filereadable(".env-override")
    let loaded=1
    silent! Dotenv .env-override
  endif

  return loaded
endfunction

nnoremap <leader>se :call SourceEnv()<CR>

function! Env()
  let evars = environ()
  for var in evars->keys()->sort()
      echo var . '=' . evars[var]
  endfor
endfunction

nnoremap <leader>ee :call Env()<CR>

if has('autocmd')
  augroup FiletypeGroup
    autocmd!
    " jsx is both javascript and jsx
    autocmd BufNewFile,BufRead *.jsx set filetype=javascript.jsx
    " Save files when vim loses focus
    autocmd FocusLost,BufLeave * silent! wa
    " Reload files when vim gains focus
    " autocmd FocusGained,BufEnter * :checktime
    " Default spellcheck off
    autocmd BufRead,BufNewFile,BufEnter set nospell|set textwidth=0|set number
    " Source .env files
    autocmd DirChanged * call SourceEnvOnDirChange()
    autocmd VimEnter * call SourceEnv()
  augroup END

  augroup filetype_terminal
    if has('nvim')
      autocmd TermEnter * set nospell|set nonumber|setlocal wrap
      if (exists("+termguicolors"))
        autocmd TermEnter,TermOpen * set termguicolors
      endif
    endif
  augroup END

  augroup filetype_markdown
    autocmd!
    " hub pull-request accepts markdown
    autocmd BufRead,BufNewFile,BufEnter PULLREQ_EDITMSG set filetype=markdown
    autocmd BufNewFile,BufNewFile,BufRead qutebrowser-editor* set filetype=markdown
    autocmd FileType markdown set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set spell|set conceallevel=0
    autocmd FileType markdown let g:gutentags_enabled = 0
  augroup END

  augroup filetype_lua
    autocmd!
    autocmd FileType lua set shiftwidth=2|set tabstop=2|set softtabstop=2|set expandtab|set autoindent
  augroup END

  augroup filetype_ruby
    autocmd!
    autocmd BufNewFile,BufRead Berksfile set filetype=ruby
    autocmd FileType ruby set shiftwidth=2|set tabstop=2|set softtabstop=2|set expandtab|set autoindent
    autocmd FileType ruby map <leader>tq :TestLast --fail-fast<CR>
    autocmd FileType ruby map <leader>to :TestLast --only-failures<CR>
    autocmd FileType ruby map <leader>tn :TestLast -n<CR>
    autocmd FileType ruby map <leader>tv :call <SID>vcr_failures_only()<CR>
    autocmd FileType ruby vnoremap <Bslash>hl :s/\v:([^ ]*) \=\>/\1:/g<CR>
    autocmd FileType ruby vnoremap <Bslash>hr :s/\v(\w+):/"\1" =>/g<CR>
    autocmd FileType ruby vnoremap <Bslash>hs :s/\v\"(\w+)\"\s+\=\>\s+/\1\: /g<CR>
    autocmd FileType ruby vnoremap <Bslash>hj :s/\v\"(\w+)\":\s+/"\1" => /g<CR>
    autocmd FileType ruby map <leader>d :ALEFix<CR>
    autocmd FileType ruby nmap <silent><C-p> <Plug>(ale_previous_wrap)
    autocmd FileType ruby nmap <silent><C-n> <Plug>(ale_next_wrap)

    let g:test#runner_commands = ['RSpec']

    function! s:vcr_failures_only()
      let $VCR_RECORD="all"
      TestLast
      unlet $VCR_RECORD
    endfunction
  augroup END

  augroup filetype_python
    autocmd!
    autocmd FileType python map <Bslash>ff :TestFile --ff -x<CR>
    autocmd FileType python map <Bslash>fo :TestFile --ff<CR>
    autocmd FileType python map <Bslash>n :TestFile --lf -x<CR>
    autocmd FileType python map <Bslash>d :TestFile --pdb<CR>
  augroup END

  augroup filetype_lua
    autocmd!
    autocmd FileType lua map <Bslash>ff :TestFile --no-keep-going<CR>
    autocmd FileType lua map <leader>d :ALEFix<CR>
  augroup END

  augroup filetype_gitcommit
    autocmd!
    autocmd BufNewFile,BufRead new-commit set filetype=markdown
    autocmd BufNewFile,BufRead differential* set filetype=markdown
    autocmd FileType gitcommit set colorcolumn=73
    autocmd FileType gitcommit set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set spell
  augroup END

  augroup filetype_git
    autocmd!
    autocmd FileType git set nofoldenable
  augroup END

  augroup filetype_go
    autocmd!
    autocmd FileType go set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set nospell

  augroup END

  augroup filetype_rust
    autocmd!
    autocmd FileType rust set makeprg=cargo\ run
    autocmd FileType rust set colorcolumn=100
    autocmd FileType rust map <Bslash>t :TestFile --jobs 1<CR>
  augroup END

  augroup filetype_javascript
    autocmd!
    autocmd FileType javascript set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
    autocmd BufNewFile,BufRead .eslintrc set filetype=json
    autocmd FileType javascript nnoremap <leader>d :ALEFix<CR>
  augroup END

  augroup filetype_haml
    autocmd!
    autocmd FileType haml set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
  augroup END

  augroup filetype_sshconfig
    autocmd!
    autocmd FileType sshconfig set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
  augroup END

  augroup filetype_json
    autocmd!
    autocmd FileType json set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
  augroup END

  augroup filetype_yaml
    autocmd!
    autocmd FileType yaml set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
  augroup END

  augroup filetype_fish
    autocmd!
    autocmd FileType fish set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
  augroup END

  augroup filetype_perl
    autocmd!
    autocmd FileType perl set tabstop=8|set shiftwidth=8|set noexpandtab|set nolist
  augroup END

  augroup filetype_sshconfig
    autocmd!
    autocmd FileType sshconfig set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
  augroup END

  augroup filetype_sh
    autocmd!
    autocmd BufNewFile,BufRead .alias set filetype=sh
  augroup END

  augroup filetype_vim
    autocmd!
    autocmd FileType vim set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
  augroup END

  augroup BWCCreateDir
    autocmd!
    autocmd BufWritePre * :call s:MkNonExDir(expand('<afile>'), +expand('<abuf>'))
  augroup END
endif

" vim-test
if has('nvim')
  let test#strategy = "neovim"
endif

let test#ruby#minitest#executable = 'bundle exec ruby -Itest/'
let test#go#gotest#options = {
      \ 'nearest': '-v',
      \ 'file': '-v',
      \}

let test#rust#cargotest#options = {
      \ 'nearest': '-- --nocapture',
      \}

let test#python#pytest#options = {
      \ 'nearest': '-s',
      \ 'file':    '-s',
      \}

let test#ruby#rspec#options = {
      \ 'nearest': '--format documentation',
      \ 'file':    '--format documentation',
      \ 'suite':   '--tag \~slow',
      \}

let test#python#runner = 'pytest'
let g:test#runner_commands = ['PyTest', 'RSpec', 'GoTest', 'Minitest']

map <leader>tf :TestFile<CR>
map <leader>tu :TestNearest<CR>
map <leader>tt :TestNearest<CR>
map <leader>tl :TestLast<CR>
map <leader>ts :TestSuite<CR>

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
