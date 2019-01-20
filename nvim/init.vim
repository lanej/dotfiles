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
set history=1000               " Store lots of :cmdline history
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

" searching stuff

" Make <C-L> clear highlight and redraw
nnoremap <C-\> :nohls<CR>
inoremap <C-\> <C-O>:nohls<CR>

" Edit the vimrc file
nnoremap ev  :tabedit $MYVIMRC<CR>
nnoremap evr :source  $MYVIMRC<CR>
nnoremap tk  :tabnext<CR>
nnoremap th  :tabprev<CR>
nnoremap tl  :tablast<CR>
nnoremap tt  :tabedit<Space>
nnoremap tn  :tabnext<CR>
nnoremap tc  :tabnew<CR>
nnoremap tm  :tabm<Space>
nnoremap tx  :tabclose<CR>
nnoremap t1  1gt<CR>
nnoremap t2  2gt<CR>
nnoremap t3  3gt<CR>
nnoremap t4  4gt<CR>
nnoremap t5  5gt<CR>
nnoremap t6  6gt<CR>

" Enable filetype plugins to handle indents
filetype plugin indent on

" plugins:begin
let g:plug_url_format="git://github.com/%s"

" allow separate plugins per editor
if has('nvim')
  call plug#begin('~/.local/share/nvim/plugged')
else
  call plug#begin('~/.local/share/vim/plugged')
endif

" split / join code blocks
Plug 'AndrewRadev/splitjoin.vim'
" show git diffs in left gutter
Plug 'airblade/vim-gitgutter'
" additional omnicompletion
Plug 'autozimu/LanguageClient-neovim', { 'branch': 'next', 'do': 'bash install.sh' }
" fancy status line
Plug 'bling/vim-airline'
" easily rename files
Plug 'danro/rename.vim'
" quick in-buffer navigation
Plug 'easymotion/vim-easymotion'
" colorscheme
Plug 'jacoborus/tender.vim'
" test integration
Plug 'janko-m/vim-test'
" buffer explorer
Plug 'jlanzarotta/bufexplorer'
" fzf install, fast fuzzy finder
Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
" fzf integration
Plug 'junegunn/fzf.vim'
" easy alignment
Plug 'junegunn/vim-easy-align'
" vim github self / team activity
Plug 'junegunn/vim-github-dashboard'
" yank register browser
Plug 'junegunn/vim-peekaboo'
" automatically update tags
Plug 'ludovicchabant/vim-gutentags'
" show me what i just yanked
Plug 'machakann/vim-highlightedyank'
" browse tags
Plug 'majutsushi/tagbar'
" quick search, configured to use ag
Plug 'mileszs/ack.vim'
" markdown preview with mermaid support
Plug 'previm/previm'
Plug 'tyru/open-browser.vim'
" code commenter
Plug 'scrooloose/nerdcommenter'
" file browser
Plug 'scrooloose/nerdtree'
" show changed files in file browser
Plug 'Xuyuanp/nerdtree-git-plugin'
" syntax highlighting
Plug 'sheerun/vim-polyglot', { 'do': './build' }
" javascript
Plug 'ternjs/tern_for_vim', { 'for': ['javascript', 'javascript.jsx'] }
" typescript
Plug 'mhartington/nvim-typescript', { 'do': './install.sh' }
" git integration
Plug 'tpope/vim-fugitive'
" github integration
Plug 'tpope/vim-rhubarb'
" git commit browser
Plug 'junegunn/gv.vim'
" additional editing commands
Plug 'tpope/vim-surround'
" linter / fixer 
Plug 'w0rp/ale'
"python completion
Plug 'davidhalter/jedi'
" terraform
Plug 'hashivim/vim-terraform'
" sessions
Plug 'tpope/vim-obsession'
Plug 'dhruvasagar/vim-prosession'

if has('nvim') || v:version > 8000
  " deoplete
  Plug 'zchee/deoplete-jedi'
  Plug 'zchee/deoplete-go', { 'do': 'make' }
  Plug 'carlitux/deoplete-ternjs', { 'do': 'npm install -g tern' }
  " ruby completion
  Plug 'lanej/deoplete-solargraph'
  " go completion
  Plug 'mdempsky/gocode', { 'rtp': 'nvim', 'do': '~/.local/share/nvim/plugged/gocode/nvim/symlink.sh' }
  " go debugger
  Plug 'sebdah/vim-delve'
  if !has('nvim')
    Plug 'Shougo/deoplete.nvim'
    Plug 'Shougo/vimproc.vim'
    Plug 'Shougo/vimshell.vim'
  else
    Plug 'Shougo/deoplete.nvim', { 'do': ':UpdateRemotePlugins' }
  endif
else
  Plug 'roxma/nvim-yarp'
  Plug 'roxma/vim-hug-neovim-rpc'
endif

if v:version > 704 || has('nvim')
  " sudo write
  Plug 'lambdalisue/suda.vim'
  " Allow saving of files as sudo when I forgot to start vim using sudo.
  cmap w! w suda://%<CR>
  " additional go support
  Plug 'fatih/vim-go', { 'do': ':GoInstallBinaries' }
endif

" Add plugins to &runtimepath
call plug#end()

" plugins:end

" plugin-config start

" vim-plug
map <leader>pi :PlugInstall<CR>
map <leader>pc :PlugClean<CR>
map <leader>pu :PlugUpdate<CR>

"previm
" let g:previm_open_cmd = 'open -a Safari'

" vim-polyglot
let g:vim_markdown_conceal = 0

" gutentag
let g:gutentags_enabled = 1

" terraform
let g:terraform_completion_keys = 1
let g:terraform_fmt_on_save     = 1
let g:terraform_align           = 1
let g:terraform_remap_spacebar  = 0

" ack.vim
nnoremap <Leader>aa :Ack!<Space>
nnoremap <Leader>ap :Ack!<Space>
map <leader>a* :Ack!<space><cword><CR>
map <leader>as :Ack!<space><cword><CR>

" use silver-searcher if available
if executable('ag')
  let g:ackprg = 'ag --vimgrep'
  " Use ag over grep
  set grepprg=ag\ --nogroup\ --nocolor
endif

" sessions
map <leader>ps :Prosession 

" NERDTree
let g:NERDTreeShowHidden = 1
let g:NERDTreeChDirMode  = 2
let g:NERDTreeQuitOnOpen = 1
let g:NERDSpaceDelims    = 1

map <leader>n :NERDTreeToggle<CR>
map <leader>ntm :NERDTreeMirror<CR>
map <leader>ntc :NERDTreeClose<CR>
map <leader>ntf :NERDTreeFind<CR>

" NERDCommenter
" Enable trimming of trailing whitespace when uncommenting
let g:NERDTrimTrailingWhitespace = 1

" Align line-wise comment delimiters flush left instead of following code indentation
let g:NERDDefaultAlign = 'left'

" airline

let g:airline#extensions#ale#enabled = 1
let g:airline#extensions#branch#enabled = 1
let g:airline#extensions#bufferline#enabled = 0
let g:airline#extensions#tabline#buffer_nr_show = 0
let g:airline#extensions#tabline#enabled = 0
let g:airline#extensions#tabline#formatter = 'jsformatter'
let g:airline#extensions#tabline#tab_nr_type = 2
let g:airline#extensions#whitespace#enabled = 0
let g:airline_powerline_fonts = 0
let g:airline_theme = 'tenderplus'

" git-gutter
set updatetime=100
if exists('&signcolumn')  " Vim 7.4.2201
  set signcolumn=yes
else
  let g:gitgutter_sign_column_always = 1
endif

" fzf
noremap <leader>f :Files<CR>
noremap <leader>gf :GFiles<CR>
noremap <leader>gg :Buffers<CR>
noremap <leader>t :Tags<CR>
noremap <leader>l :Lines<CR>
noremap <leader>gc :Commits<CR>

" [Buffers] Jump to the existing window if possible
let g:fzf_buffers_jump = 1

" [[B]Commits] Customize the options used by 'git log':
let g:fzf_commits_log_options = '--graph --color=always --format="%C(auto)%h%d %s %C(black)%C(bold)%cr"'

" [Tags] Command to generate tags file
let g:fzf_tags_command = 'ctags -R'

" fugitive
noremap <leader>gb :Gblame<CR>
noremap <leader>go :Gbrowse<CR>

" ALE config
let g:ale_completion_enabled = 1
let g:ale_echo_cursor = 1
let g:ale_echo_msg_error_str = 'Error'
let g:ale_echo_msg_format = '%s'
let g:ale_echo_msg_warning_str = 'Warning'
let g:ale_emit_conflict_warnings = 1
let g:ale_enabled = 1
let g:ale_fix_on_save = 0
let g:ale_fixers = {
      \ 'go': [ 'gofmt'],
      \ 'javascript.jsx': ['eslint'],
      \ 'javscript': ['eslint'],
      \ 'json': 'prettier',
      \ 'jsx': ['eslint'],
      \ 'markdown': ['prettier'],
      \ 'ruby': [ 'rufo', 'rubocop' ],
      \ 'sh': ['shfmt'],
      \ 'python': ['autopep8'],
      \ }

" let g:ale_linters = { 'go': [ 'gofmt' ], 'ruby': [ 'ruby', 'rubocop' ], 'yaml': [ 'yamllint'], 'jsx': ['stylelint', 'eslint'] }
let g:ale_javascript_eslint_executable = 'npm run list eslint'
let g:ale_linter_aliases = {'jsx': 'css'}
let g:ale_go_gometalinter_options = '--tests'
let g:ale_keep_list_window_open = 0
let g:ale_lint_delay = 200
let g:ale_lint_on_enter = 1
let g:ale_lint_on_save = 1
let g:ale_lint_on_text_changed = 'always'
let g:ale_open_list = 0
let g:ale_ruby_bundler_executable = 'bundle'
let g:ale_ruby_rubocop_executable = 'rubocop'
let g:ale_set_highlights = 1
let g:ale_set_loclist = 1
let g:ale_set_quickfix = 0
let g:ale_set_signs = 1
let g:ale_sign_column_always = 0
let g:ale_sign_error = '>>'
let g:ale_sign_offset = 1000000
let g:ale_sign_warning = '--'
let g:ale_statusline_format = ['%d error(s)', '%d warning(s)', 'OK']
let g:ale_warn_about_trailing_whitespace = 0

map <leader>d :ALEFix<CR>
nmap <silent> <C-p> <Plug>(ale_previous_wrap)
nmap <silent> <C-n> <Plug>(ale_next_wrap)

" rename
map <leader>re :Rename 

"terminal
if has("terminal")
  tnoremap <C-o> <C-\><C-n>
endif

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

set completeopt=longest,menuone,noinsert,noselect

" ================ Scrolling ========================
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

" disable ri check
:map K <Nop>

" Helpers
map <leader>srt :!sort<CR>

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

" Start interactive EasyAlign in visual mode (e.g. vip<Enter>)
vmap <Enter> <Plug>(EasyAlign)
" Realign the whole file
map <leader>= ggVG=<CR>

set shortmess=a

let g:clang_format#style_options = {
      \ "AccessModifierOffset" : -4,
      \ "AllowShortIfStatementsOnASingleLine" : "true",
      \ "AlwaysBreakTemplateDeclarations" : "true",
      \ "Standard" : "C++11"}

set makeprg="make -j9"
nnoremap <Leader>m :make!<CR>

let g:tagbar_type_go = {
      \ 'ctagstype' : 'go',
      \ 'kinds'     : [
      \ 'p:package',
      \ 'i:imports:1',
      \ 'c:constants',
      \ 'v:variables',
      \ 't:types',
      \ 'n:interfaces',
      \ 'w:fields',
      \ 'e:embedded',
      \ 'm:methods',
      \ 'r:constructor',
      \ 'f:functions'
      \ ],
      \ 'sro' : '.',
      \ 'kind2scope' : {
      \ 't' : 'ctype',
      \ 'n' : 'ntype'
      \ },
      \ 'scope2kind' : {
      \ 'ctype' : 't',
      \ 'ntype' : 'n'
      \ },
      \ 'ctagsbin'  : 'gotags',
      \ 'ctagsargs' : '-sort -silent'
      \ }

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
set undodir=~/.cache/nvim/undo

" vim-go config
let g:go_auto_sameids = 1
let g:go_auto_type_info = 0
let g:go_fmt_command = 'goimports'
let g:go_highlight_build_constraints = 1
let g:go_highlight_extra_types = 1
let g:go_highlight_fields = 1
let g:go_highlight_functions = 1
let g:go_highlight_methods = 1
let g:go_highlight_operators = 1
let g:go_highlight_structs = 1
let g:go_highlight_types = 1
let g:go_list_type = 'quickfix'
let g:go_highlight_generate_tags = 1
let g:go_highlight_build_constraints = 1
let g:go_fmt_fail_silently = 1

if has('autocmd')
  augroup FiletypeGroup
    autocmd!
    " hub pull-request accepts markdown
    autocmd BufRead,BufNewFile,BufEnter PULLREQ_EDITMSG set filetype=markdown
    " jsx is both javascript and jsx
    autocmd BufNewFile,BufRead *.jsx set filetype=javascript.jsx
    " Save files when vim loses focus
    autocmd FocusLost * silent! wa
    " Reload files when vim gains focus
    autocmd FocusGained,BufEnter * :checktime
    " Default spellcheck off
    autocmd BufRead,BufNewFile,BufEnter set nospell|set textwidth=0
  augroup END

  augroup filetype_markdown
    autocmd!
    autocmd FileType markdown set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set spell
    let g:gutentags_enabled = 0
  augroup END

  augroup filetype_ruby
    autocmd!
    autocmd FileType ruby set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
    autocmd FileType ruby set wrapscan|set textwidth=120
    autocmd BufNewFile,BufRead Berksfile set filetype=ruby
    autocmd FileType ruby set colorcolumn=120|highlight ColorColumn ctermbg=Black guibg=LightGrey
  augroup END

  augroup filetype_gitcommit
    autocmd!
    autocmd FileType gitcommit set colorcolumn=72|highlight ColorColumn ctermbg=Black guibg=LightGrey
    autocmd FileType gitcommit set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set spell
  augroup END

  augroup straggelers
    autocmd!
    " remove trailing spaces
    autocmd FileType c,cpp,java,php,ruby autocmd BufWritePre <buffer> :%s/\s\+$//e
    " remove trailing whitespace automatically
    autocmd FileType c,cpp,java,php,ruby autocmd BufWritePre <buffer> :set et | retab
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

  augroup filetype_python
    autocmd!
    autocmd FileType python set tabstop=8|set shiftwidth=2|set expandtab
  augroup END

  augroup filetype_c
    autocmd!
    " map to <Leader>cf in C++ code
    autocmd FileType c,cpp,objc nnoremap <buffer><Leader>cf :<C-u>ClangFormat<CR>
    autocmd FileType c,cpp,objc vnoremap <buffer><Leader>cf :ClangFormat<CR>
    " if you install vim-operator-user
    autocmd FileType c,cpp,objc map <buffer><Leader>x <Plug>(operator-clang-format)
    " Toggle auto formatting:
    nmap <Leader>C :ClangFormatAutoToggle<CR>
  augroup END

  augroup filetype_go
    autocmd!

    autocmd FileType go set tabstop=4|set shiftwidth=4|set expandtab|set autoindent|set nolist
    autocmd FileType qf wincmd J

    autocmd FileType go nmap <leader>b  <Plug>(go-build)
    autocmd FileType go nmap <leader>r  <Plug>(go-run)

    autocmd FileType go nmap <Leader>gi :GoImports<CR>
    autocmd FileType go nmap <Leader>gr :GoRename<CR>
    autocmd FileType go nmap <Leader>gd :GoDef<CR>
    autocmd FileType go nmap <Leader>gp :GoDefPop<CR>
    autocmd FileType go nmap <Leader>gs :GoCallers<CR>
    autocmd FileType go nmap <Leader>ga :GoReferrers<CR>
    autocmd FileType go nmap <Leader>ge :GoCallees<CR>

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

" vim-test configuration
let test#strategy = "neovim"
let test#ruby#rspec#executable = 'chruby $(cat .ruby-version); bundle exec rspec'
let test#ruby#minitest#executable = 'chruby $(cat .ruby-version); bundle exec ruby -Itest/'
let g:test#preserve_screen = 1
map <Bslash>t :TestFile<CR>
map <Bslash>u :TestNearest<CR>

" neovim specific
let g:ruby_host_prog = '~/.rbenv/versions/2.5.1/bin/neovim-ruby-host'

set shortmess+=c
" For conceal markers.
if has('conceal')
  set conceallevel=2 concealcursor=niv
endif

if has('nvim') || v:version > 8000
  " let g:deoplete#enable_profile = 1
  " Use deoplete.
  let g:deoplete#enable_at_startup = 1
  " Use smartcase.
  let g:deoplete#enable_smart_case = 1
  " debug logging
  call deoplete#enable_logging('DEBUG', '/tmp/deoplete.log')

  let g:deoplete#omni#functions = {}
  let g:deoplete#omni_patterns = {}
  let g:deoplete#sources = {}

  " Automatically start language servers.
  let g:LanguageClient_autoStart = 1

  let g:LanguageClient_serverCommands = {}

  " Minimal LSP configuration for JavaScript
  if executable('javascript-typescript-stdio')
    let g:LanguageClient_serverCommands.javascript = ['javascript-typescript-stdio']
  endif

  let g:LanguageClient_loggingLevel = 'INFO'
  let g:LanguageClient_loggingFile  = $HOME.'/LanguageClient.log'
  let g:LanguageClient_serverStderr = $HOME.'/LanguageServer.log'

  let g:deoplete#omni#functions.javascript = [
        \ 'tern#Complete',
        \ 'jspc#omni'
        \]

  " deoplete-go settings
  let g:deoplete#sources#go#gocode_binary = $GOPATH.'/bin/gocode'
  let g:deoplete#sources#go#sort_class = ['package', 'func', 'type', 'var', 'const']

  let g:deoplete#sources['javascript.jsx'] = ['file', 'ultisnips', 'ternjs']

  let g:tern#command = ['tern']
  let g:tern#arguments = ['--persistent']
  let g:deoplete#sources#ternjs#timeout = 1

  " Consistent solargraph binary location
  let g:deoplete#sources#solargraph#command = $HOME.'/.rbenv/versions/2.5.1/bin/solargraph'
  let g:deoplete#sources#solargraph#args = ['stdio']

  " Whether to include the types of the completions in the result data. Default: 0
  let g:deoplete#sources#ternjs#types = 1

  " Whether to include the distance (in scopes for variables, in prototypes for
  " properties) between the completions and the origin position in the result
  " data. Default: 0
  let g:deoplete#sources#ternjs#depths = 1

  " Whether to include documentation strings (if found) in the result data.
  " Default: 0
  let g:deoplete#sources#ternjs#docs = 1

  " When on, only completions that match the current word at the given point will
  " be returned. Turn this off to get all results, so that you can filter on the
  " client side. Default: 1
  let g:deoplete#sources#ternjs#filter = 0

  " Whether to use a case-insensitive compare between the current word and
  " potential completions. Default 0
  let g:deoplete#sources#ternjs#case_insensitive = 1

  " When completing a property and no completions are found, Tern will use some
  " heuristics to try and return some properties anyway. Set this to 0 to
  " turn that off. Default: 1
  let g:deoplete#sources#ternjs#guess = 0

  " Determines whether the result set will be sorted. Default: 1
  let g:deoplete#sources#ternjs#sort = 0

  " When disabled, only the text before the given position is considered part of
  " the word. When enabled (the default), the whole variable name that the cursor
  " is on will be included. Default: 1
  let g:deoplete#sources#ternjs#expand_word_forward = 0

  " Whether to ignore the properties of Object.prototype unless they have been
  " spelled out by at least two characters. Default: 1
  let g:deoplete#sources#ternjs#omit_object_prototype = 0

  " Whether to include JavaScript keywords when completing something that is not
  " a property. Default: 0
  let g:deoplete#sources#ternjs#include_keywords = 1

  " If completions should be returned when inside a literal. Default: 1
  let g:deoplete#sources#ternjs#in_literal = 0

  "Add extra filetypes
  let g:deoplete#sources#ternjs#filetypes = [
        \ 'jsx',
        \ 'javascript.jsx',
        \ 'vue',
        \ ]

  let g:deoplete#max_abbr_width = 35
  let g:deoplete#max_menu_width = 20
  let g:deoplete#skip_chars = ['(', ')', '<', '>']
  let g:deoplete#tag#cache_limit_size = 800000
  let g:deoplete#file#enable_buffer_path = 1

  let g:deoplete#sources#jedi#statement_length = 30
  let g:deoplete#sources#jedi#show_docstring = 1
  let g:deoplete#sources#jedi#short_types = 1

  call deoplete#initialize()
endif
