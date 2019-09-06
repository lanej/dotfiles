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
set incsearch                  " Makes search act like search in modern browsers
set lazyredraw                 " Don't redraw while executing macros (good performance config)
set magic                      " For regular expressions turn magic on
set modelines=5
set nobackup
set number                     " Line numbers are good
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
set ttimeoutlen=100
set novb
set noeb
set equalalways                " Maintain consistent window sizes
set updatetime=300

if (has("nvim"))
  set inccommand=nosplit       " live replace
endif

if $OS != "Linux"
  set termguicolors
endif

" ================ Turn Off Swap Files ==============
set noswapfile
set nobackup
set nowritebackup

" Trailing spaces and tabs
set list
set listchars=tab:→\ ,space:·,nbsp:␣,trail:•,precedes:«,extends:»

let mapleader = ','

" searching stuff

" Make <C-L> clear highlight and redraw
nmap <C-\> :nohls<CR>
imap <C-\> <C-O>:nohls<CR>

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
" quick search, configured to use ag
Plug 'mileszs/ack.vim'
" markdown preview with mermaid support
Plug 'previm/previm'
Plug 'tyru/open-browser.vim'
Plug 'tpope/vim-markdown'
" code commenter
Plug 'scrooloose/nerdcommenter'
" file browser
Plug 'scrooloose/nerdtree'
" show changed files in file browser
Plug 'Xuyuanp/nerdtree-git-plugin'
" git integration
Plug 'tpope/vim-rhubarb'
Plug 'tpope/vim-fugitive'
" additional editing commands
Plug 'tpope/vim-surround'
" sessions
Plug 'tpope/vim-obsession'
Plug 'dhruvasagar/vim-prosession'
" editorconfig
Plug 'sgur/vim-editorconfig'
Plug 'sheerun/vim-polyglot'
Plug 'christoomey/vim-tmux-navigator'
Plug 'w0rp/ale'

if has('nvim')
  " Plug 'neoclide/coc.nvim', {'branch':'release'}
  " Plug 'autozimu/LanguageClient-neovim', { 'branch': 'next', 'do': 'bash install.sh' }
  Plug 'Shougo/deoplete.nvim', { 'do': ':UpdateRemotePlugins' }
  Plug 'deoplete-plugins/deoplete-tag'
  Plug 'ryanoasis/vim-devicons'
  Plug 'fatih/vim-go'
endif

let g:editorconfig_blacklist = {
      \ 'filetype': ['git.*', 'fugitive'],
      \ 'pattern': ['\.un~$']}

if executable('python')
  Plug 'davidhalter/jedi-vim', { 'for': 'python' }
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

map <leader>rb :%s/<C-r><C-w>/

let g:vim_markdown_conceal = 0
let g:markdown_fenced_languages = ['html', 'python', 'bash=sh', 'ruby', 'go']

" gutentag
let g:gutentags_enabled = 1
" map <C-[> :pop<cr>


" terraform
let g:terraform_completion_keys = 1
let g:terraform_fmt_on_save     = 1
let g:terraform_align           = 1
let g:terraform_remap_spacebar  = 0

if executable('rg')
  " use ripgrep if available
  let g:ackprg = 'rg --vimgrep'
  set grepprg=rg\ --nogroup\ --nocolor
  nnoremap <leader>aa :Rg!<space>
  nnoremap <leader>az :Rg!<CR>
elseif executable('ag')
  " use silver-searcher if available
  let g:ackprg = 'ag --vimgrep'
  set grepprg=ag\ --nogroup\ --nocolor
  nnoremap <leader>aa :Ag!<space>
  nnoremap <leader>az :Ag!<CR>
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
let g:airline#extensions#branch#enabled = 1
let g:airline#extensions#bufferline#enabled = 0
let g:airline#extensions#tabline#buffer_nr_show = 0
let g:airline#extensions#tabline#enabled = 1
let g:airline#extensions#tabline#show_tabs = 1
let g:airline#extensions#tabline#formatter = 'unique_tail_improved'
let g:airline#extensions#tabline#tab_nr_type = 0
let g:airline#extensions#tabline#show_buffers = 0
let g:airline#extensions#whitespace#enabled = 0
let g:airline#extensions#tabline#tab_min_count = 2
let g:airline_powerline_fonts = 0
let g:airline_theme = 'tenderplus'

" git-gutter
if exists('&signcolumn')  " Vim 7.4.2201
  set signcolumn=yes
else
  let g:gitgutter_sign_column_always = 1
endif

" fzf
nnoremap <leader>as :Ack!<space><cword><CR>
noremap  <leader>ac :Commands<CR>
noremap  <leader>gf :GFiles<CR>
noremap  <leader>ag :Commits<CR>
noremap  <leader>al :Lines<CR>
noremap  <leader>at :Tags<CR>
noremap  <leader>f  :Files<CR>
noremap  <leader>gc :BCommits<CR>
noremap  <leader>gg :Buffers<CR>
noremap  <leader>;  :History:<CR>
noremap  <leader>/  :History/<CR>
noremap  <leader>l  :BLines<CR>
noremap  <leader>t  :BTags<CR>

command! -bang -nargs=* Ag
  \ call fzf#vim#ag(<q-args>,
  \                 <bang>0 ? fzf#vim#with_preview('right:60%')
  \                         : fzf#vim#with_preview('right:50%:hidden', '?'),
  \                 <bang>0)

command! -bang -nargs=* Rg
  \ call fzf#vim#ag(<q-args>,
  \                 <bang>0 ? fzf#vim#with_preview('right:60%')
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
noremap <leader>gm :Gmerge<CR>
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

set completeopt+=menu,noinsert,noselect

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
  let g:go_def_mode='gopls'
  let g:go_info_mode='gopls'
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
  " let g:go_snippet_engine = "neosnippet"
end

function! SourceEnv()
   if filereadable(".env")
     silent! Dotenv .env
   endif

   if filereadable(".env-override")
     silent! Dotenv .env-override
     " silent! CocRestart
   endif
endfunction

if has('autocmd')
  augroup FiletypeGroup
    autocmd!
    " jsx is both javascript and jsx
    autocmd BufNewFile,BufRead *.jsx set filetype=javascript.jsx
    " Save files when vim loses focus
    autocmd FocusLost * silent! wa
    " Reload files when vim gains focus
    autocmd FocusGained,BufEnter * :checktime
    " Default spellcheck off
    autocmd BufRead,BufNewFile,BufEnter set nospell|set textwidth=0
    " Source .env files
    if has('nvim')
      autocmd DirChanged * call SourceEnv()
    endif
  augroup END

  augroup filetype_terminal
    if has('nvim')
      autocmd TermOpen * set nospell|set nonumber
    endif
  augroup END

  augroup filetype_markdown
    autocmd!
    " hub pull-request accepts markdown
    autocmd BufRead,BufNewFile,BufEnter PULLREQ_EDITMSG set filetype=markdown
    autocmd BufNewFile,BufNewFile,BufRead qutebrowser-editor* set filetype=markdown
    autocmd FileType markdown set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set spell
    autocmd FileType markdown let g:gutentags_enabled = 0
    autocmd FileType markdown set conceallevel=0
  augroup END

  augroup filetype_ruby
    autocmd!
    autocmd BufNewFile,BufRead Berksfile set filetype=ruby
    autocmd FileType ruby set shiftwidth=2|set tabstop=2|set softtabstop=2|set expandtab
    autocmd FileType ruby map <Bslash>f :TestFile --fail-fast<CR>
    autocmd FileType ruby map <Bslash>n :TestFile -n<CR>
    autocmd FileType ruby map <leader>d :ALEFix<CR>
    autocmd FileType ruby nmap <silent><C-p> <Plug>(ale_previous_wrap)
    autocmd FileType ruby nmap <silent><C-n> <Plug>(ale_next_wrap)
  augroup END

  augroup filetype_gitcommit
    autocmd!
    autocmd BufNewFile,BufRead new-commit set filetype=markdown
    autocmd BufNewFile,BufRead differential* set filetype=markdown
    autocmd FileType gitcommit set colorcolumn=73|highlight ColorColumn ctermbg=DarkGrey guibg=LightGrey
    autocmd FileType gitcommit set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set spell
  augroup END

  augroup filetype_git
    autocmd!
    autocmd FileType git set nofoldenable
  augroup END

  augroup filetype_go
    autocmd!
  augroup END

  augroup filetype_rust
    autocmd!
    autocmd FileType rust set makeprg=cargo\ run
    autocmd FileType rust nmap <leader>d :RustFmt<CR>
  augroup END

  augroup filetype_javascript
    autocmd!
    autocmd FileType javascript set tabstop=2|set shiftwidth=2|set expandtab|set autoindent
    autocmd BufNewFile,BufRead .eslintrc set filetype=json
    if filereadable(".eslintrc")
      " autocmd FileType javascript nmap <silent> <leader>d :CocCommand eslint.executeAutofix<CR>
      " autocmd FileType javascript.jsx nmap <silent> <leader>d :CocCommand eslint.executeAutofix<CR>
    endif
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

  augroup filetype_go
    autocmd!

    autocmd FileType go set tabstop=4|set shiftwidth=4|set expandtab|set autoindent|set nolist
    autocmd FileType qf wincmd J

    autocmd FileType go nmap <leader>b  <Plug>(go-build)
    autocmd FileType go nmap <leader>r  <Plug>(go-run)

    autocmd FileType go nmap <leader>d :GoImports<CR>
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

map <Bslash>t :TestFile<CR>
map <Bslash>u :TestNearest<CR>
map <Bslash>r :TestLast<CR>
map <Bslash>s :TestSuite<CR>

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

if &runtimepath =~ 'coc.nvim'
  " Use <c-space> to trigger completion.
  inoremap <silent><expr> <c-space> coc#refresh()

  " Use <cr> to confirm completion, `<C-g>u` means break undo chain at current position.
  " Coc only does snippet and additional edit on confirm.
  inoremap <expr> <cr> pumvisible() ? "\<C-y>" : "\<C-g>u\<CR>"

  " Use `[c` and `]c` to navigate diagnostics
  nmap <silent><C-p> <Plug>(coc-diagnostic-prev)
  nmap <silent><C-n> <Plug>(coc-diagnostic-next)

  " Remap keys for gotos
  nmap <silent> gd <Plug>(coc-definition)
  nmap <silent> gy <Plug>(coc-type-definition)
  nmap <silent> gi <Plug>(coc-implementation)
  nmap <silent> gr <Plug>(coc-references)

  " Use K to show documentation in preview window
  nnoremap <silent> K :call <SID>show_documentation()<CR>

  function! s:show_documentation()
    if (index(['vim','help'], &filetype) >= 0)
      execute 'h '.expand('<cword>')
    else
      call CocAction('doHover')
    endif
  endfunction

  " Highlight symbol under cursor on CursorHold
  autocmd CursorHold * silent call CocActionAsync('highlight')

  " Remap for rename current word
  nmap <leader>rn <Plug>(coc-rename)
  nmap <silent> <leader>d :Format<cr>

  " Remap for format selected region
  xmap <leader>cf  <Plug>(coc-format-selected)
  nmap <leader>cf  <Plug>(coc-format-selected)

  augroup mygroup
    autocmd!
    " Setup formatexpr specified filetype(s).
    autocmd FileType typescript,json,rust setl formatexpr=CocAction('formatSelected')
    " Update signature help on jump placeholder
    autocmd User CocJumpPlaceholder call CocActionAsync('showSignatureHelp')
  augroup end

  " Remap for do codeAction of selected region, ex: `<leader>aap` for current paragraph
  xmap <leader>a  <Plug>(coc-codeaction-selected)
  nmap <leader>a  <Plug>(coc-codeaction-selected)

  " Remap for do codeAction of current line
  nmap <leader>ac  <Plug>(coc-codeaction)
  " Fix autofix problem of current line
  nmap <leader>qf  <Plug>(coc-fix-current)

  " Use `:Format` to format current buffer
  command! -nargs=0 Format :call CocAction('format')

  " Use `:Fold` to fold current buffer
  command! -nargs=? Fold :call CocAction('fold', <f-args>)

  " Using CocList
  " Show all diagnostics
  nnoremap <silent> <space>a  :<C-u>CocList diagnostics<cr>
  " Manage extensions
  nnoremap <silent> <space>e  :<C-u>CocList extensions<cr>
  " Show commands
  nnoremap <silent> <space>c  :<C-u>CocList commands<cr>
  " Find symbol of current document
  nnoremap <silent> <space>o  :<C-u>CocList outline<cr>
  " Search workspace symbols
  nnoremap <silent> <space>s  :<C-u>CocList -I symbols<cr>
  " Do default action for next item.
  nnoremap <silent> <space>j  :<C-u>CocNext<CR>
  " Do default action for previous item.
  nnoremap <silent> <space>k  :<C-u>CocPrev<CR>
  " Resume latest coc list
  nnoremap <silent> <space>p  :<C-u>CocListResume<CR>
endif

if &runtimepath =~ 'ale'
  let g:ale_linters = {'ruby': ['rubocop']}
  let g:ale_fixers = {'ruby': ['rubocop']}


  let g:ale_keep_list_window_open = 0
  let g:ale_lint_delay = 200
  let g:ale_lint_on_enter = 1
  let g:ale_lint_on_save = 1
  let g:ale_lint_on_text_changed = 'always'
  let g:ale_open_list = 0
  let g:ale_ruby_bundler_executable = 'bundle'
  let g:ale_ruby_rubocop_executable = 'bundle'
  let g:ale_set_highlights = 1
  let g:ale_set_loclist = 1
  let g:ale_set_quickfix = 0
  let g:ale_set_signs = 1
  let g:ale_sign_column_always = 1
  let g:ale_sign_error = '>>'
  let g:ale_sign_offset = 1000000
  let g:ale_sign_warning = '--'
  let g:ale_completion_enabled = 0
endif

let g:jedi#auto_initialization = 0

if &runtimepath =~ 'LanguageClient-neovim'
  let g:LanguageClient_serverCommands = {
    \ 'rust': ['rustup', 'run', 'stable', 'rls'],
    \ 'javascript': ['/usr/local/bin/javascript-typescript-stdio'],
    \ 'javascript.jsx': ['tcp://127.0.0.1:2089'],
    \ 'python': ['pyls'],
    \ }

  nnoremap <silent> gd :call LanguageClient#textDocument_definition()<CR>
  nnoremap <silent> gr :call LanguageClient#textDocument_references()<CR>
  nnoremap <silent> K :call LanguageClient#textDocument_hover()<CR>
  nnoremap <silent> rn :call LanguageClient#textDocument_rename()<CR>
endif

if &runtimepath =~ 'deoplete'
  let g:deoplete#enable_at_startup = 0

  inoremap <silent> <CR> <C-r>=<SID>my_cr_function()<CR>
  function! s:my_cr_function() abort
    return deoplete#close_popup() . "\<CR>"
  endfunction

  call deoplete#custom#option({
  \ 'auto_complete_delay': 200,
  \ 'auto_refresh_delay': 200,
  \ 'smart_case': v:true,
  \ 'max_list': 25,
  \ })

  " Enable deoplete when InsertEnter.
  autocmd InsertEnter * call deoplete#enable()
end
