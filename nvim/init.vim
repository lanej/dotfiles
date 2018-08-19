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
set hidden                     " Better buffer management
set history=1000               " Store lots of :cmdline history
set hlsearch
set ignorecase                 " Ignore case when searching
set inccommand=nosplit         " live replace
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

if (has("termguicolors"))
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
call plug#begin('~/.local/share/nvim/plugged')

let g:plug_url_format="git://github.com/%s"

Plug 'AndrewRadev/splitjoin.vim'
Plug 'SevereOverfl0w/deoplete-github'
Plug 'Shougo/deoplete.nvim', { 'do': ':UpdateRemotePlugins' }
Plug 'Shougo/neosnippet-snippets'
Plug 'Shougo/neosnippet.vim'
Plug 'Xuyuanp/nerdtree-git-plugin'
Plug 'airblade/vim-gitgutter'
Plug 'aklt/plantuml-syntax'
Plug 'alexgenco/neovim-ruby'
Plug 'aliou/moriarty.vim'
Plug 'bling/vim-airline'
Plug 'carlitux/deoplete-ternjs', { 'do': 'npm install -g tern' }
Plug 'danro/rename.vim'
Plug 'davidhalter/jedi'
Plug 'easymotion/vim-easymotion'
Plug 'fatih/vim-go', { 'do': ':GoInstallBinaries' }
Plug 'godlygeek/tabular'
Plug 'groenewege/vim-less'
Plug 'hashivim/vim-terraform'
Plug 'honza/vim-snippets'
Plug 'jacoborus/tender.vim'
Plug 'janko-m/vim-test'
Plug 'jiangmiao/auto-pairs'
Plug 'jimenezrick/vimerl'
Plug 'jlanzarotta/bufexplorer'
Plug 'joshdick/onedark.vim'
Plug 'juliosueiras/vim-terraform-completion'
Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
Plug 'junegunn/fzf.vim'
Plug 'junegunn/gv.vim'
Plug 'junegunn/vim-easy-align'
Plug 'junegunn/vim-github-dashboard'
Plug 'junegunn/vim-peekaboo'
Plug 'juvenn/mustache.vim'
Plug 'kchmck/vim-coffee-script'
Plug 'lambdalisue/suda.vim'
Plug 'lanej/deoplete-solargraph'
Plug 'ludovicchabant/vim-gutentags'
Plug 'machakann/vim-highlightedyank'
Plug 'majutsushi/tagbar'
Plug 'mattn/gist-vim'
Plug 'mattn/webapi-vim'
Plug 'mhartington/nvim-typescript', { 'do': './install.sh' }
Plug 'mileszs/ack.vim'
Plug 'mxw/vim-jsx'
Plug 'neomake/neomake'
Plug 'ngmy/vim-rubocop'
Plug 'noprompt/vim-yardoc'
Plug 'othree/jspc.vim', { 'for': ['javascript', 'javascript.jsx'] }
Plug 'pangloss/vim-javascript'
Plug 'plasticboy/vim-markdown'
Plug 'rorymckinley/vim-rubyhash'
Plug 'scrooloose/nerdcommenter'
Plug 'scrooloose/nerdtree'
Plug 'scrooloose/vim-slumlord'
Plug 'sebdah/vim-delve'
Plug 'sheerun/vim-polyglot'
Plug 'skywind3000/asyncrun.vim'
Plug 'slack/vim-align'
Plug 'ternjs/tern_for_vim', { 'for': ['javascript', 'javascript.jsx'] }
Plug 'thoughtbot/vim-rspec'
Plug 'tpope/vim-bundler'
Plug 'tpope/vim-dotenv'
Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-haml'
Plug 'tpope/vim-projectionist'
Plug 'tpope/vim-rails'
Plug 'tpope/vim-rbenv'
Plug 'tpope/vim-repeat'
Plug 'tpope/vim-rhubarb'
Plug 'tpope/vim-speeddating'
Plug 'tpope/vim-surround'
Plug 'vim-scripts/xorium.vim'
Plug 'w0rp/ale'
Plug 'wting/rust.vim'
Plug 'zchee/deoplete-go', { 'do': 'make && gocode set autobuild true' }
Plug 'zchee/deoplete-jedi'

" Add plugins to &runtimepath
call plug#end()

" plugins:end

" =============== UI ================
" turn syntax highlighting on
syntax enable
colorscheme tender

highlight clear LineNr     " Current line number row will have same background color in relative mode
highlight clear SignColumn " SignColumn should match background

" grep
nnoremap <Leader>ap :Ack!<Space>
map <leader>a* :Ack!<space><cword><CR>

set completeopt=longest,menuone,noselect

if executable('ag')
  let g:ackprg = 'ag --vimgrep'
  " Use ag over grep
  set grepprg=ag\ --nogroup\ --nocolor
endif

" ================ Scrolling ========================
set scrolloff=8         "Start scrolling when we're 8 lines away from margins
set sidescrolloff=15
set sidescroll=1

" ================ Status Line ======================
if has('cmdline_info')
  set showcmd                 " Show partial commands in status line and
  " Selected characters/lines in visual mode
endif

" NerdTREE
map <leader>n :NERDTreeToggle<CR>
map <leader>ntm :NERDTreeMirror<CR>
map <leader>ntc :NERDTreeClose<CR>
map <leader>ntf :NERDTreeFind<CR>

let g:NERDTreeShowHidden=1
let g:NERDTreeChDirMode=2
let g:NERDTreeQuitOnOpen=1
let g:NERDSpaceDelims = 1

" NERDCommenter
" Enable trimming of trailing whitespace when uncommenting
let g:NERDTrimTrailingWhitespace = 1

" Align line-wise comment delimiters flush left instead of following code indentation
let g:NERDDefaultAlign = 'left'

" other cwd configs
map <leader>ct :cd %:p:h<CR>
map <leader>cg :Gcd<CR>

" disable ex mode
:map Q <Nop>

" disable ri check
:map K <Nop>

" Align bindings
" map <leader>a= to :Align = (rather than :Align := )
map <leader>a= :Align =<CR>
map <leader>ah :Align =><CR>
map <leader>a# :Align #<CR>
map <leader>a{ :Align {<CR>
map <leader>A :Align [A-Z].*<CR>:'<,'>s/\s*$//<CR><C-l>
map <leader>= ggVG=<CR>

" Helpers
map <leader>rts %s/\v\s+$//g<CR>
map <leader>srt :!sort<CR>

" Allow saving of files as sudo when I forgot to start vim using sudo.
cmap w! w suda://%<CR>

" Haml
map <leader>hs :!haml -c %:p<CR>

" Set minimum window height
set winheight=10

" ctags stuff
set tags=tags

" numbers
set number

" git-gutter
set updatetime=100
set signcolumn=yes

" gui stuff
set guioptions-=T
set guioptions-=r
set guioptions-=L

" ctrlp
set wildignore+=*/tmp/*,*.so,*.swp,*.zip,*.log,.git,*/bundle/*
let g:ctrlp_custom_ignore = '\.git$\|\.hg$\|\.svn$'

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
" let g:fzf_tags_command = 'ctags -R'

" fugitive
noremap <leader>gb :Gblame<CR>
noremap <leader>go :Gbrowse<CR>

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

set shortmess=a

let g:clang_format#style_options = {
      \ "AccessModifierOffset" : -4,
      \ "AllowShortIfStatementsOnASingleLine" : "true",
      \ "AlwaysBreakTemplateDeclarations" : "true",
      \ "Standard" : "C++11"}

set makeprg="make -j9"
nnoremap <Leader>m :make!<CR>

" airline
set laststatus=2

let g:airline#extensions#branch#enabled = 0
let g:airline#extensions#bufferline#enabled = 0
let g:airline#extensions#tabline#buffer_nr_show = 0
let g:airline#extensions#tabline#enabled = 1
" let g:airline#extensions#tabline#formatter = 'jsformatter'
let g:airline#extensions#tabline#tab_nr_type = 2
let g:airline#extensions#whitespace#enabled = 0
" let g:airline_left_alt_sep=''
" let g:airline_left_sep=''
" let g:airline_powerline_fonts = 1
" let g:airline_right_alt_sep=''
" let g:airline_right_sep=''
" let g:airline_theme='onedark'
let g:airline_theme = 'tenderplus'

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


" Signify
" highlight SignifySignAdd    cterm=bold ctermbg=237  ctermfg=29
" highlight SignifySignDelete cterm=bold ctermbg=237  ctermfg=124 guifg=#af0000
" highlight SignifySignChange cterm=bold ctermbg=106  ctermfg=106

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
" let g:go_fmt_fail_silently = 1

" vim-rufo
let g:rufo_auto_formatting = 0

if has('autocmd')

  augroup FiletypeGroup
    autocmd!
    " hub pull-request accepts markdown
    autocmd BufRead,BufNewFile PULLREQ_EDITMSG set filetype=markdown
    " jsx is both javascript and jsx
    autocmd BufNewFile,BufRead *.jsx set filetype=javascript.jsx
    " Save files when vim loses focus
    autocmd FocusLost * silent! wa

    " Reload files when vim gains focus
    autocmd FocusGained,BufEnter * :checktime
  augroup END

  augroup filetype_markdown
    " autocmd!
    " autocmd FileType markdown set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set spell|set wrap|set textwidth=0|set wrapmargin=0
    " autocmd FileType markdown imap <S-Tab> <C-d>
    " autocmd FileType markdown imap <Tab> <C-t>
  augroup END

  augroup filetype_ruby
    autocmd!
    autocmd FileType ruby set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
    autocmd FileType ruby set wrapscan|set textwidth=120
    autocmd BufNewFile,BufRead Berksfile set filetype=ruby
    autocmd FileType ruby set colorcolumn=120|highlight ColorColumn ctermbg=DarkGrey guibg=DarkGrey
  augroup END

  augroup filetype_gitcommit
    autocmd!
    autocmd FileType gitcommit set colorcolumn=72|highlight ColorColumn ctermbg=DarkGrey guibg=DarkGrey
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
    autocmd FileType go nmap <Leader>ge :GoCallees<CR>

  augroup END

  augroup BWCCreateDir
    autocmd!

    autocmd BufWritePre * :call s:MkNonExDir(expand('<afile>'), +expand('<abuf>'))

  augroup END
endif

" vim-test configuration
let test#strategy = "neovim"
let test#ruby#rspec#executable = 'rbenv exec bundle exec rspec'
let test#ruby#minitest#executable = 'rbenv exec bundle exec ruby -Itest/'
let g:test#preserve_screen = 1
map <Bslash>t :TestFile<CR>
map <Bslash>u :TestNearest<CR>

" neovim specific
let g:ruby_host_prog = '~/.rbenv/versions/2.5.1/bin/neovim-ruby-host'

set shortmess+=c

" ALE config
let g:airline#extensions#ale#enabled = 1
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

" let g:ale_linters = { 'go': [ 'gofmt' ], 'ruby': [ 'ruby', 'rubocop' ], 'yaml': [ 'yamllint'] }
let g:ale_linters = {'jsx': ['stylelint', 'eslint']}
let g:ale_javascript_eslint_executable = 'npm run list eslint'
let g:ale_linter_aliases = {'jsx': 'css'}
let g:ale_go_gometalinter_options = '--tests'
let g:ale_keep_list_window_open = 0
let g:ale_lint_delay = 200
let g:ale_lint_on_enter = 1
let g:ale_lint_on_save = 1
let g:ale_lint_on_text_changed = 'always'
let g:ale_open_list = 0
let g:ale_ruby_bundler_executable = '/Users/jlane/.rbenv/shims/bundle'
let g:ale_ruby_rubocop_executable = '/Users/jlane/.rbenv/shims/rubocop'
let g:ale_set_highlights = 1
let g:ale_set_loclist = 1
let g:ale_set_quickfix = 0
let g:ale_set_signs = 1
let g:ale_sign_column_always = 0
let g:ale_sign_error = '>>'
let g:ale_sign_offset = 1000000
let g:ale_sign_warning = '--'
let g:ale_statusline_format = ['%d error(s)', '%d warning(s)', 'OK']
let g:ale_warn_about_trailing_whitespace = 1

map <leader>d :ALEFix<CR>
nmap <silent> <C-p> <Plug>(ale_previous_wrap)
nmap <silent> <C-n> <Plug>(ale_next_wrap)

" rename
map <leader>re :Rename 

" markdown
" let g:mkdx#settings = { 'highlight': { 'enable': 1 }, 'links': { 'fragment': { 'complete': 0 } } }

"terminal
tnoremap <C-o> <C-\><C-n>

" let g:deoplete#enable_profile = 1
" Use deoplete.
let g:deoplete#enable_at_startup = 1
" Use smartcase.
let g:deoplete#enable_smart_case = 1
" debug logging
" call deoplete#enable_logging('DEBUG', '/tmp/deoplete.log')

let g:deoplete#omni#functions = {}
let g:deoplete#omni_patterns = {}

let g:deoplete#omni#functions.javascript = [
      \ 'tern#Complete',
      \ 'jspc#omni'
      \]

let g:deoplete#sources = {}

" deoplete-go settings
let g:deoplete#sources#go#gocode_binary = $GOPATH.'/bin/gocode'
let g:deoplete#sources#go#sort_class = ['package', 'func', 'type', 'var', 'const']

let g:deoplete#sources['javascript.jsx'] = ['file', 'ultisnips', 'ternjs']

let g:tern#command = ['tern']
let g:tern#arguments = ['--persistent']
let g:deoplete#sources#ternjs#timeout = 1

" Consistent solargraph binary location
let g:deoplete#sources#solargraph#command = '/Users/jlane/.rbenv/versions/2.5.1/bin/solargraph'
let g:deoplete#sources#solargraph#args = ['socket', '--port=0']

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


let g:deoplete#sources.gitcommit=['github']
let g:deoplete#keyword_patterns = {}
let g:deoplete#keyword_patterns.gitcommit = '.+'

let g:github_dashboard = { 'username': 'lanej', 'password': $GITHUB_TOKEN }
" let g:github_user = 'lanej'
" let g:github_password = $GITHUB_TOKEN

" call deoplete#util#set_pattern(
" \ g:deoplete#omni#input_patterns,
" \ 'gitcommit', [g:deoplete#keyword_patterns.gitcommit])


let g:deoplete#max_abbr_width = 35
let g:deoplete#max_menu_width = 20
let g:deoplete#skip_chars = ['(', ')', '<', '>']
let g:deoplete#tag#cache_limit_size = 800000
let g:deoplete#file#enable_buffer_path = 1

let g:deoplete#sources#jedi#statement_length = 30
let g:deoplete#sources#jedi#show_docstring = 1
let g:deoplete#sources#jedi#short_types = 1

let g:deoplete#omni_patterns.terraform = '[^ *\t"{=$]\w*'
let g:terraform_completion_keys = 1
let g:terraform_fmt_on_save = 1
let g:terraform_align=1
let g:terraform_remap_spacebar=0

" Plugin key-mappings.
" Note: It must be "imap" and "smap".  It uses <Plug> mappings.
imap <C-k> <Plug>(neosnippet_expand_or_jump)
smap <C-k> <Plug>(neosnippet_expand_or_jump)
xmap <C-k> <Plug>(neosnippet_expand_target)

" SuperTab like snippets behavior.
" Note: It must be "imap" and "smap".  It uses <Plug> mappings.
"imap <expr><TAB>
" \ pumvisible() ? "\<C-n>" :
" \ neosnippet#expandable_or_jumpable() ?
" \    "\<Plug>(neosnippet_expand_or_jump)" : "\<TAB>"
smap <expr><TAB> neosnippet#expandable_or_jumpable() ?
      \ "\<Plug>(neosnippet_expand_or_jump)" : "\<TAB>"

" For conceal markers.
if has('conceal')
  set conceallevel=2 concealcursor=niv
endif

"" Enable snipMate compatibility feature.
let g:neosnippet#enable_snipmate_compatibility = 1


call deoplete#initialize()
