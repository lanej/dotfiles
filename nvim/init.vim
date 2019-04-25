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
set novb
set noeb
set equalalways                " Maintain consistent window sizes

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
nnoremap fbk :bd!<CR>
nnoremap fak :%bd!<bar>e#<CR>

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

Plug 'junegunn/vim-easy-align'
" support dotenv
Plug 'tpope/vim-dotenv'
" unified diffs only
Plug 'lambdalisue/vim-unified-diff'
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
Plug 'lanej/tender.vim'
" test integration
Plug 'janko-m/vim-test'
" fzf install, fast fuzzy finder
Plug 'junegunn/fzf', { 'dir': '~/.fzf', 'do': './install --all' }
" fzf integration
Plug 'junegunn/fzf.vim'
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
" git integration
Plug 'tpope/vim-rhubarb'
Plug 'tpope/vim-fugitive'
" additional editing commands
Plug 'tpope/vim-surround'
" linter / fixer
Plug 'w0rp/ale'
" sessions
Plug 'tpope/vim-obsession'
Plug 'dhruvasagar/vim-prosession'
" snippets
Plug 'Shougo/neosnippet.vim'
Plug 'Shougo/neosnippet-snippets'
" editorconfig
Plug 'sgur/vim-editorconfig'
Plug 'neoclide/coc.nvim', {'do': { -> coc#util#install()}}

let g:editorconfig_blacklist = {
      \ 'filetype': ['git.*', 'fugitive'],
      \ 'pattern': ['\.un~$']}

" language plugins
if executable('node')
  " javascript
  Plug 'ternjs/tern_for_vim', { 'for': ['javascript', 'javascript.jsx'] }
  " typescript
  Plug 'mhartington/nvim-typescript', { 'do': './install.sh' }
end

if executable('python')
  Plug 'davidhalter/jedi', { 'for': 'python' }
endif

" terraform
if executable('terraform')
  Plug 'hashivim/vim-terraform', { 'for': 'terraform' }
end

if v:version > 704 || has('nvim')
  " sudo write
  Plug 'lambdalisue/suda.vim'
  " Allow saving of files as sudo when I forgot to start vim using sudo.
  cmap w! w suda://%<CR>
endif

" Add plugins to &runtimepath
call plug#end()

" plugins:end

" plugin-config start

" vim-plug
map <leader>pi :PlugInstall<CR>
map <leader>pc :PlugClean<CR>
map <leader>pu :PlugUpdate<CR>

" vim-polyglot
let g:vim_markdown_conceal = 0

" gutentag
let g:gutentags_enabled = 1

" terraform
let g:terraform_completion_keys = 1
let g:terraform_fmt_on_save     = 1
let g:terraform_align           = 1
let g:terraform_remap_spacebar  = 0

" use silver-searcher if available
if executable('ag')
  let g:ackprg = 'ag --vimgrep'
  " Use ag over grep
  set grepprg=ag\ --nogroup\ --nocolor
endif

" sessions
map <leader>ps :Prosession<space>

" NERDTree
let g:NERDTreeShowHidden = 1
let g:NERDTreeChDirMode  = 2
let g:NERDTreeQuitOnOpen = 1
let g:NERDSpaceDelims    = 1

map <leader>ntt :NERDTreeToggle<CR>
map <leader>ntm :NERDTreeMirror<CR>
map <leader>ntc :NERDTreeClose<CR>
map <leader>ntf :NERDTreeFind<CR>

" NERDCommenter
" Enable trimming of trailing whitespace when uncommenting
let g:NERDTrimTrailingWhitespace = 1

" Align line-wise comment delimiters flush left instead of following code indentation
let g:NERDDefaultAlign = 'left'

" airline
" if you want to disable auto detect, comment out those two lines
"let g:airline#extensions#disable_rtp_load = 1
" let g:airline_extensions = ['branch', 'hunks', 'coc']
let g:airline_section_error = '%{airline#util#wrap(airline#extensions#coc#get_error(),0)}'
let g:airline_section_warning = '%{airline#util#wrap(airline#extensions#coc#get_warning(),0)}'
let g:airline#extensions#branch#enabled = 1
let g:airline#extensions#bufferline#enabled = 1
let g:airline#extensions#tabline#buffer_nr_show = 0
let g:airline#extensions#tabline#enabled = 1
let g:airline#extensions#tabline#formatter = 'unique_tail_improved'
let g:airline#extensions#tabline#tab_nr_type = 2
let g:airline#extensions#whitespace#enabled = 0
let g:airline_powerline_fonts = 0
let g:airline_theme = 'tenderplus'

" git-gutter
set updatetime=300
if exists('&signcolumn')  " Vim 7.4.2201
  set signcolumn=yes
else
  let g:gitgutter_sign_column_always = 1
endif

" fzf
nnoremap <leader>aa :Ack!<space>
nnoremap <leader>as :Ack!<space><cword><CR>
nnoremap <leader>az :Ag!<CR>
noremap  <leader>ac :Commands<CR>
noremap  <leader>af :Files<CR>
noremap  <leader>ag :Commits<CR>
noremap  <leader>al :Lines<CR>
noremap  <leader>at :Tags<CR>
noremap  <leader>f  :GFiles<CR>
noremap  <leader>gc :BCommits<CR>
noremap  <leader>gg :Buffers<CR>
noremap  <leader>;  :History:<CR>
noremap  <leader>/  :History/<CR>
noremap  <leader>l  :BLines<CR>
noremap  <leader>t  :BTags<CR>

command! -bang -nargs=* Ag
  \ call fzf#vim#ag(<q-args>,
  \                 <bang>0 ? fzf#vim#with_preview('up:60%')
  \                         : fzf#vim#with_preview('right:50%:hidden', '?'),
  \                 <bang>0)

command! -bang -nargs=? -complete=dir Files
  \ call fzf#vim#files(<q-args>, fzf#vim#with_preview(), <bang>0)
command! -bang -nargs=? -complete=dir GFiles
  \ call fzf#vim#gitfiles(<q-args>, fzf#vim#with_preview(), <bang>0)

" [Buffers] Jump to the existing window if possible
let g:fzf_buffers_jump = 1

" [[B]Commits] Customize the options used by 'git log':
let g:fzf_commits_log_options = '--graph --color=always --format="%C(auto)%h%d %s %C(black)%C(bold)%cr"'

" fugitive
noremap <leader>gb :Gblame<CR>
noremap <leader>go :Gbrowse<CR>
autocmd BufReadPost fugitive://* set bufhidden=delete

" rename
map <leader>re :Rename<space>

"terminal
if has("nvim")
  tnoremap <C-o> <C-\><C-n>
endif

noremap <leader>sh :terminal<cr>
nmap cp :let @" = expand("%")<cr>
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
hi Visual guifg=White guibg=DarkGrey gui=none
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

" other cwd configs
map <leader>ct :cd %:p:h<CR>
map <leader>cg :Gcd<CR>

" disable ex mode
:map Q <Nop>

" disable ri check
:map K <Nop>

" Helpers
map <leader>srt :!sort<CR>
map <leader>q :!uniq<CR>

" Wrapped lines goes down/up to next row, rather than next line in file.
noremap j gj
noremap k gk

" If I don't let off the shift key quick enough
command! Q :q
command! Qa :qa
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

nnoremap tb :TagbarToggle<CR>

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
if &runtimepath =~ 'vim-go'
  let g:go_addtags_transform = "snakecase"
  let g:go_auto_sameids = 0
  let g:go_auto_type_info = 0 " often overrides command window
  let g:go_decls_mode = 'gopls'
  let g:go_fmt_command = 'goimports'
  let g:go_fmt_fail_silently = 1
  let g:go_highlight_build_constraints = 1
  let g:go_highlight_extra_types = 1
  let g:go_highlight_fields = 1
  let g:go_highlight_functions = 1
  let g:go_highlight_function_calls = 1
  let g:go_highlight_generate_tags = 1
  let g:go_highlight_methods = 1
  let g:go_highlight_operators = 1
  let g:go_highlight_structs = 1
  let g:go_highlight_types = 1
  let g:go_highlight_variable_declarations = 1
  let g:go_highlight_variable_assignments = 1
  " let g:go_list_type = 'quickfix'
  let g:go_snippet_engine = "neosnippet"
end

function! SourceEnv()
   if filereadable(".env")
     silent! Dotenv .env
   endif

   if filereadable(".env-overrides")
     silent! Dotenv .env-overrides
     silent! CocRestart
   endif
endfunction

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
    " Source .env files and restart coc.nvim
    if has('nvim')
      autocmd DirChanged * call SourceEnv()
    endif
  augroup END

  augroup filetype_markdown
    autocmd!
    autocmd BufNewFile,BufRead qutebrowser-editor* set filetype=markdown
    autocmd FileType markdown set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set spell
    autocmd FileType markdown let g:gutentags_enabled = 0
    autocmd FileType markdown set conceallevel=0
  augroup END

  augroup filetype_ruby
    autocmd!
    autocmd BufNewFile,BufRead Berksfile set filetype=ruby
    autocmd FileType ruby map <Bslash>f :TestFile --fail-fast<CR>
    autocmd FileType ruby map <Bslash>n :TestFile -n<CR>
  augroup END

  augroup filetype_gitcommit
    autocmd!
    autocmd BufNewFile,BufRead new-commit set filetype=markdown
    autocmd FileType gitcommit set colorcolumn=73|highlight ColorColumn ctermbg=DarkGrey guibg=LightGrey
    autocmd FileType gitcommit set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set spell
  augroup END

  augroup filetype_git
    autocmd!
    autocmd FileType git set nofoldenable
  augroup END

  augroup filetype_go
    autocmd!
    autocmd FileType go let g:ale_fix_on_save = 1
  augroup END

  augroup filetype_rust
    autocmd!
    autocmd FileType rust let g:ale_fix_on_save = 1
    autocmd FileType rust set colorcolumn=100|highlight ColorColumn ctermbg=DarkGrey guibg=LightGrey
    autocmd FileType rust set makeprg=cargo\ run
  augroup END

  augroup filetype_java
    autocmd!
    autocmd FileType java setlocal omnifunc=javacomplete#Complete
    autocmd FileType java let g:ale_fix_on_save = 1

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
    autocmd FileType sh let g:ale_fix_on_save = 1
    autocmd BufNewFile,BufRead .alias set filetype=sh
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

    autocmd FileType go nmap <leader>gi :GoImports<CR>
    autocmd FileType go nmap <leader>gr :GoRename<CR>
    autocmd FileType go nmap <leader>gd :GoDef<CR>
    autocmd FileType go nmap <leader>gp :GoDefPop<CR>
    autocmd FileType go nmap <leader>gs :GoCallers<CR>
    autocmd FileType go nmap <leader>ga :GoReferrers<CR>
    autocmd FileType go nmap <leader>ge :GoCallees<CR>
    autocmd FileType go nmap <leader>gt :TestFile -v<CR>

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
let test#ruby#rspec#executable = 'bundle exec rspec -cfd'
let test#ruby#minitest#executable = 'bundle exec ruby -Itest/'
let test#python#pytest#options = '-s'
let test#rust#cargotest#options = '-- --nocapture'
map <Bslash>t :TestFile<CR>
map <Bslash>u :TestNearest<CR>
map <Bslash>r :TestLast<CR>

" c	don't give |ins-completion-menu| messages.  For example,
" "-- XXX completion (YYY)", "match 1 of 2", "The only match",
set shortmess+=c
" T	truncate other messages in the middle if they are too long to
set shortmess+=T
" a	all of the above abbreviations
set shortmess+=a

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

if has('conceal')
  set conceallevel=2 concealcursor=niv
endif

" coc
nmap <silent> gd <Plug>(coc-definition)
nmap <silent> gy <Plug>(coc-type-definition)
nmap <silent> gi <Plug>(coc-implementation)
nmap <silent> gr <Plug>(coc-references)
" Highlight symbol under cursor on CursorHold
autocmd CursorHold * silent call CocActionAsync('highlight')

" Remap for rename current word
nmap <leader>rn <Plug>(coc-rename)

" Remap for format selected region
vmap <leader>d  <Plug>(coc-format-selected)
nmap <leader>d  <Plug>(coc-format-selected)

function! s:show_documentation()
  if &filetype == 'vim'
    execute 'h '.expand('<cword>')
  else
    call CocAction('doHover')
  endif
endfunction

" Use K to show documentation in preview window
nnoremap <silent> K :call <SID>show_documentation()<CR>

" Remap for rename current word
nmap <leader>rn <Plug>(coc-rename)

" ALE config
let g:ale_completion_enabled = 0
let g:ale_echo_cursor = 1
let g:ale_echo_msg_error_str = 'Error'
let g:ale_echo_msg_format = '%s'
let g:ale_echo_msg_warning_str = 'Warning'
let g:ale_emit_conflict_warnings = 1
let g:ale_enabled = 1
let g:ale_fix_on_save = 0
let g:ale_fixers = {
      \ '*': ['remove_trailing_lines', 'trim_whitespace'],
      \ 'go': [ 'gofmt'],
      \ 'java': ['google_java_format'],
      \ 'javascript.jsx': ['eslint'],
      \ 'javscript': ['eslint'],
      \ 'json': 'prettier',
      \ 'jsx': ['eslint'],
      \ 'markdown': ['prettier'],
      \ 'python': ['autopep8'],
      \ 'ruby': [ 'rufo', 'rubocop' ],
      \ 'rust': [ 'rustfmt' ],
      \ 'sh': ['shfmt'],
    \ }

let g:ale_go_gometalinter_options = '--tests'
let g:ale_keep_list_window_open = 0
let g:ale_lint_delay = 200
let g:ale_lint_on_enter = 1
let g:ale_lint_on_save = 1
let g:ale_lint_on_text_changed = 'always'
let g:ale_open_list = 0
let g:ale_ruby_bundler_executable = 'bundle'
let g:ale_ruby_rubocop_executable = 'bundle'
let g:ale_ruby_rufo_executable = 'bundle'
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
