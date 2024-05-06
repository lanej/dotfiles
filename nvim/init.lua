--
-- |_ _| \ | |_ _|_   _| |_   _  __ _
--  | ||  \| || |  | | | | | | |/ _` |
--  | || |\  || |  | |_| | |_| | (_| |
-- |___|_| \_|___| |_(_)_|\__,_|\__,_|
--

vim.cmd [[
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

" replace current word
map <leader>rw :%s/<C-r><C-w>//gc<left><left><left>
vmap <leader>rw :s/<C-r><C-w>//gc<left><left><left>

" legacy support for the muscle memory"
map <leader>rb :%s/<C-r><C-w>//gc<left><left><left>
vmap <leader>rb :s/<C-r><C-w>//gc<left><left><left>

" replace current selection
map <leader>rs "hy:%s/<C-r>h//gc<left><left><left>
vmap <leader>rs ""hy:s/<C-r>h//gc<left><left><left>

" replace current word in all quicklist files
map <leader>rq :cfdo %s/<C-r><C-w>/
vmap <leader>rq :cfdo s/<C-r><C-w>/


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
let g:prosession_tmux_title = 1
let g:prosession_tmux_title_format = '@@@'

map <leader>ntt :NvimTreeToggle<CR>
map <leader>ntc :NvimTreeClose<CR>
map <leader>ntf :NvimTreeFindFile<CR>

let g:indent_blankline_show_current_context = v:true
let g:indent_blankline_use_treesitter = v:true

nnoremap <silent><leader>gm :Git mergetool<CR>
nnoremap <silent><leader>go :GBrowse!<CR>
vnoremap <silent><leader>go :GBrowse!<CR>
nnoremap <silent><leader>gt :Git commit -am'wip'<CR>
nnoremap <silent><leader>gs :Git<CR>
nnoremap <silent><leader>gr :Gread<CR>
nnoremap <silent><leader>ga :Git commit -av<CR>
nnoremap <silent><leader>gv :Git commit -v<CR>
nnoremap <silent><leader>gd :Gdiffsplit origin/master
nnoremap <silent><leader>gb :Git blame<CR>
nnoremap <silent><leader>gp :Git push<CR>

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

" Start interactive EasyAlign in visual mode (e.g. vipga)
xmap ga <Plug>(EasyAlign)

" Start interactive EasyAlign for a motion/text object (e.g. gaip)
nmap ga <Plug>(EasyAlign)

" Realign the whole file
map <leader>D ggVG=<CR>

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
      \ 'sh': ['shfmt'],
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
let g:ale_set_loclist = 0
let g:ale_linters_explicit = 1
let g:ale_set_quickfix = 0
let g:ale_sign_column_always = 1
let g:ale_sign_error = '>>'
let g:ale_echo_cursor = 0
let g:ale_sign_offset = 1000000
let g:ale_sign_warning = '--'
let g:ale_completion_enabled = 0
let g:ale_use_neovim_diagnostics_api = 1

map <silent>th :TSHighlightCapturesUnderCursor<CR>

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

nnoremap <silent><leader>ee :e .env<CR>
nnoremap <silent><leader>eo :e .env-override<CR>

function! GoDebugNearest()
  let g:test#go#runner = 'delve'
  TestNearest
  unlet g:test#go#runner
endfunction

if has('autocmd')
  au FocusGained * :redraw!
  au FocusGained,BufEnter * :checktime

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

  augroup filetype_norg
    au!
    au FileType norg set shiftwidth=2|set spell
    au FileType norg let g:gutentags_enabled = 0
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

    let g:test#runner_commands = ['RSpec']

    function! s:vcr_failures_only()
      let $VCR_RECORD="all"
      TestLast
      unlet $VCR_RECORD
    endfunction
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
    au FileType lua set colorcolumn=122|set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set nospell
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
    " au FileType javascript nnoremap <leader>d :ALEFix<CR>
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
    autocmd FileType sh set tabstop=2|set noexpandtab|set autoindent|set nospell
  augroup END

  augroup filetype_vim
    autocmd FileType vim set tabstop=2|set shiftwidth=2|set expandtab|set autoindent|set nospell
  augroup END

  augroup BWCCreateDir
    au! BufWritePre * :call s:MkNonExDir(expand('<afile>'), +expand('<abuf>'))
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
map <leader>tl :TestLast<CR>
map <leader>ts :TestSuite<CR>
map <leader>tt :TestNearest<CR>
map <leader>tu :TestNearest<CR>

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

if exists("g:neovide")
  let g:neovide_scale_factor=1.0
  function! ChangeScaleFactor(delta)
      let g:neovide_scale_factor = g:neovide_scale_factor * a:delta
  endfunction
  nnoremap <expr><C-=> ChangeScaleFactor(1.25)
  nnoremap <expr><C--> ChangeScaleFactor(1/1.25)
end
]]

local function prequire(m)
  local ok, err = pcall(require, m)
  if not ok then return nil, err end
  return err
end

-- secrets, unversioned local configs, etc.
prequire("local")
-- require("plugins")

local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable", -- latest stable release
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

require("lazy").setup({
  "folke/which-key.nvim",
  { "folke/neoconf.nvim",          cmd = "Neoconf" },
  "folke/neodev.nvim",
  {
    'gbprod/nord.nvim',
    config = function()
      require("nord").setup({
        transparent = true, -- Enable this to disable setting the background color
        terminal_colors = true,
        diff = { mode = "fg" },
        borders = true,             -- Enable the border between verticaly split windows visible
        errors = { mode = "fg" },   -- Display mode for errors and diagnostics
        styles = { comments = { italic = false } },
        search = { theme = "vim" }, -- theme for highlighting search results
        on_highlights = function(highlights, colors)
          highlights['@symbol'] = { fg = colors.aurora.orange }
          highlights['@string.special.symbol'] = highlights['@symbol']
          highlights['@variable.member'] = { fg = colors.frost.polar_water }
          highlights['@variable.parameter'] = { fg = colors.aurora.purple }
          highlights['@module'] = { fg = colors.frost.ice }
          highlights['@error'] = { sp = colors.aurora.red, undercurl = true }
          highlights['@constant'] = { fg = colors.aurora.purple }
          highlights['@text.uri'] = { underline = true }
          highlights['@error'] = { undercurl = true }
          highlights['@spell.bad'] = { undercurl = true }

          return highlights
        end,
      })
      vim.api.nvim_command('colorscheme nord')
    end,
  },
  {
    "hrsh7th/nvim-cmp",
    -- load cmp on InsertEnter
    event = "InsertEnter",
    -- these dependencies will only be loaded when cmp loads
    -- dependencies are always lazy-loaded unless specified otherwise
    dependencies = {
      "hrsh7th/cmp-nvim-lsp",
      "hrsh7th/cmp-buffer",
      "petertriho/cmp-git",
      "nvim-lua/plenary.nvim",
    },
    config = function()
      -- ...
    end,
  },
  { "nvim-tree/nvim-web-devicons", lazy = true },
  {
    'numToStr/Comment.nvim',
    config = function() require('Comment').setup() end
  },
  {
    'Wansmer/treesj',
    dependencies = 'nvim-treesitter/nvim-treesitter',
    config = function()
      require('treesj').setup({
        use_default_keymaps = false,
      })
      vim.keymap.set('n', 'gJ', require('treesj').join)
      vim.keymap.set('n', 'gS', require('treesj').split)
    end,
  },
  ({
    "esensar/nvim-dev-container",
    dependencies = "nvim-treesitter/nvim-treesitter",
    config = function() require("devcontainerconfig") end,
  }),
  {
    'nvim-lualine/lualine.nvim',
    dependencies = { 'nvim-tree/nvim-web-devicons' },
    config = function()
      require('lualine').setup {
        options = {
          icons_enabled = true,
          theme = 'nord',
          component_separators = { left = '', right = '' },
          section_separators = { left = '', right = '' },
          disabled_filetypes = {
            statusline = {},
            winbar = {},
          },
          ignore_focus = {},
          always_divide_middle = true,
          globalstatus = false,
          refresh = {
            statusline = 1000,
            tabline = 1000,
            winbar = 1000,
          }
        },
        sections = {
          lualine_a = { 'mode' },
          lualine_b = { 'branch', "diff", },
          lualine_c = {
            { 'filetype', jcon_only = true },
            { 'filename', path = 1 },
          },
          lualine_x = {
            { 'diagnostics', sources = { 'nvim_lsp', 'ale' } },
            {
              require("noice").api.status.command.get,
              cond = require("noice").api.status.command.has,
              color = { fg = "#ff9e64" },
            },
            {
              require("noice").api.status.mode.get,
              cond = require("noice").api.status.mode.has,
              color = { fg = "#ff9e64" },
            },
          },
          lualine_y = {},
          lualine_z = {}
        },
        inactive_sections = {
          lualine_a = {},
          lualine_b = {},
          lualine_c = {},
          lualine_x = { 'branch', 'diff' },
          lualine_y = {},
          lualine_z = { { 'filename', path = 1 }, { 'filetype', icon_only = true } },
        },
      }
    end,
  },
  {
    'ibhagwan/fzf-lua',
    config = function() require 'fzfconfig' end,
    branch = 'main',
    dependencies = { 'vijaymarupudi/nvim-fzf', 'nvim-tree/nvim-web-devicons' },
  },
  {
    'folke/noice.nvim',
    branch = 'main',
    config = function()
      require("noice").setup({
        routes = {
          {
            -- filter write messages "xxxL, xxxB"
            filter = {
              event = "msg_show",
              find = "%dL",
            },
            opts = { skip = true },
          },
          {
            -- filter yank messages
            filter = {
              event = "msg_show",
              find = "%d lines yanked",
            },
            opts = { skip = true },
          },
          {
            -- filter undo messages
            filter = {
              event = "msg_show",
              find = "%d change",
            },
            opts = { skip = true },
          },
          {
            -- filter undo messages
            filter = {
              event = "msg_show",
              find = "%d more line",
            },
            opts = { skip = true },
          },
          {
            -- filter undo messages
            filter = {
              event = "msg_show",
              find = "%d fewer line",
            },
            opts = { skip = true },
          },
          {
            -- filter undo messages
            filter = {
              event = "msg_show",
              find = "Already at newest change",
            },
            opts = { skip = true },
          },
          {
            -- filter undo messages
            filter = {
              event = "msg_show",
              find = "Already at oldest change",
            },
            opts = { skip = true },
          },
        },
        popupmenu = { enabled = false },
        cmdline = {
          format = {
            conceal = false
          },
        },
        lsp = {
          override = {
            ["vim.lsp.util.convert_input_to_markdown_lines"] = true,
            ["vim.lsp.util.stylize_markdown"] = true,
            ["cmp.entry.get_documentation"] = true,
          },
        },
        notify = { enabled = true },
        presets = { inc_rename = true },
        views = {
          cmdline_popup = {
            border = {
              style = "none",
              padding = { 2, 3 },
            },
            filter_options = {},
            win_options = {
              winhighlight = "NormalFloat:NormalFloat,FloatBorder:FloatBorder",
            },
          },
        },
      })
    end,
    dependencies = { 'MunifTanjim/nui.nvim', 'rcarriga/nvim-notify', 'neovim/nvim-lspconfig' },
  },
  {
    'glepnir/lspsaga.nvim',
    branch = 'main',
    dependencies = { 'neovim/nvim-lspconfig' },
    config = function() require('lspsagaconfig') end,
  },
  {
    'folke/trouble.nvim',
    dependencies = { 'nvim-tree/nvim-web-devicons' },
    config = function() require 'troubleconfig' end,
  },
  { 'norcalli/nvim-colorizer.lua', requires = 'nvim-treesitter/nvim-treesitter' },
  {
    'neovim/nvim-lspconfig',
    config = function() require('lsp') end,
    dependencies = {
      'hrsh7th/cmp-buffer',
      'hrsh7th/cmp-path',
      'hrsh7th/cmp-cmdline',
      'hrsh7th/nvim-cmp',
      'hrsh7th/cmp-nvim-lsp',
      'hrsh7th/cmp-vsnip',
      'andersevenrud/cmp-tmux',
      'hrsh7th/vim-vsnip',
      'simrat39/rust-tools.nvim',
      'nvim-tree/nvim-web-devicons',
      'onsails/lspkind.nvim',
      'altermo/ultimate-autopair.nvim',
    },
  },
  {
    'nvim-treesitter/nvim-treesitter',
    config = function() require 'treesitter' end,
  },
  {
    'nvim-treesitter/nvim-treesitter-textobjects',
    dependencies = { 'nvim-treesitter/nvim-treesitter' },
  },
  {
    'nvim-treesitter/playground',
    dependencies = { 'nvim-treesitter/nvim-treesitter' },
  },
  {
    'ibhagwan/smartyank.nvim',
    config = function()
      require('smartyank').setup {
        highlight = {
          enabled = true,        -- highlight yanked text
          higroup = "IncSearch", -- highlight group of yanked text
          timeout = 2000,        -- timeout for clearing the highlight
        },
        tmux = {
          enabled = true,
          cmd = { 'tmux', 'set-buffer', '-w' },
        },
        clipboard = { enabled = true },
        osc52 = {
          enabled = true,
          ssh_only = true, -- OSC52 yank also in local sessions
          silent = true,   -- false to disable the "n chars copied" echo
        },
      }
    end,
  },
  {
    'lukas-reineke/indent-blankline.nvim',
    dependencies = 'nvim-treesitter/nvim-treesitter',
    config = function() require("ibl").setup({}) end,
  },
  {
    "anuvyklack/windows.nvim",
    dependencies = { "anuvyklack/middleclass" },
    config = function()
      vim.o.winwidth = 10
      vim.o.winminwidth = 10
      vim.o.equalalways = true
      require('windows').setup()
    end
  },
  {
    'christoomey/vim-tmux-navigator',
    init = function()
      vim.g.tmux_navigator_no_mappings = 1
      vim.g.tmux_navigator_save_on_switch = 1
    end,
    config = function()
      vim.api.nvim_set_keymap('n', '<C-h>', ':TmuxNavigateLeft<cr>', { noremap = true, silent = true })
      vim.api.nvim_set_keymap('n', '<C-j>', ':TmuxNavigateDown<cr>', { noremap = true, silent = true })
      vim.api.nvim_set_keymap('n', '<C-k>', ':TmuxNavigateUp<cr>', { noremap = true, silent = true })
      vim.api.nvim_set_keymap('n', '<C-l>', ':TmuxNavigateRight<cr>', { noremap = true, silent = true })
    end,
  },
  {
    'lanej/vim-prosession',
    dependencies = 'tpope/vim-obsession',
  },
  {
    'epwalsh/obsidian.nvim',
    config = function()
      require('obsidian').setup({
        dir = '~/share/work',
        completion = { nvim_cmp = true, },
        daily_notes = { folder = 'dailies' },
        ui = {
          enable = true,         -- set to false to disable all additional syntax features
          update_debounce = 200, -- update delay after a text change (in milliseconds)
          checkboxes = {
            [" "] = { char = "󰄱", hl_group = "ObsidianTodo" },
            ["x"] = { char = "", hl_group = "ObsidianDone" },
            [">"] = { char = "", hl_group = "ObsidianRightArrow" },
            ["~"] = { char = "󰰱", hl_group = "ObsidianTilde" },
          },
          external_link_icon = { char = "", hl_group = "ObsidianExtLinkIcon" },
          reference_text = { hl_group = "ObsidianRefText" },
          highlight_text = { hl_group = "ObsidianHighlightText" },
          tags = { hl_group = "ObsidianTag" },
          hl_groups = {
            ObsidianTodo = { bold = true, fg = "#f78c6c" },
            ObsidianDone = { bold = true, fg = "#89ddff" },
            ObsidianRightArrow = { bold = true, fg = "#f78c6c" },
            ObsidianTilde = { bold = true, fg = "#ff5370" },
            ObsidianRefText = { underline = true, fg = "#c792ea" },
            ObsidianExtLinkIcon = { fg = "#c792ea" },
            ObsidianTag = { italic = true, fg = "#89ddff" },
            ObsidianHighlightText = { bg = "#75662e" },
          },
        }
      }
      )
    end,
    dependencies = {
      "nvim-lua/plenary.nvim",
      "hrsh7th/nvim-cmp",
      "ibhagwan/fzf-lua",
    },
  },
  'RRethy/vim-illuminate',
  "sindrets/diffview.nvim",
  'mbbill/undotree',
  {
    'nvim-treesitter/playground',
    dependencies = 'nvim-treesitter/nvim-treesitter',
  },
  {
    'phaazon/hop.nvim',
    config = function() require 'hopconfig' end,
  },
  'tpope/vim-dotenv',
  'tpope/vim-fugitive',
  'tpope/vim-eunuch',
  'tpope/vim-surround',
  'tpope/vim-repeat',
  { 'norcalli/nvim-colorizer.lua', dependencies = 'nvim-treesitter/nvim-treesitter' },
  {
    "JMarkin/gentags.lua",
    cond = vim.fn.executable("ctags") == 1,
    dependencies = { "nvim-lua/plenary.nvim", },
    config = function() require("gentags").setup({}) end,
    event = "VeryLazy",
  },
  'vim-test/vim-test',
  'junegunn/vim-easy-align',
  {
    'lewis6991/gitsigns.nvim',
    dependencies = { 'nvim-lua/plenary.nvim' },
    tag = 'release',
    config = function() require('gitsignsconfig') end,
  },
  {
    'nvim-tree/nvim-tree.lua',
    dependencies = 'nvim-tree/nvim-web-devicons',
    config = function() require 'nvim-tree-config' end,
  },
  {
    'subnut/nvim-ghost.nvim',
    cond = vim.env.SSH_TTY == nil,
    event = "VeryLazy",
  },
  {
    'folke/todo-comments.nvim',
    config = function()
      require('todo-comments').setup({
        keywords = {
          WTF = { icon = "🤨", color = "warning", alt = { "DAFUQ", "GAH" } },
        }
      })
    end,
  },
  {
    "smjonas/inc-rename.nvim",
    config = function()
      require("inc_rename").setup()
      vim.keymap.set("n", "<leader>ri", ":IncRename ")
    end,
  },
  {
    'altermo/ultimate-autopair.nvim',
    event = { 'InsertEnter', 'CmdlineEnter' },
    branch = 'v0.6',
    opts = {},
  }
})

vim.keymap.set('n', '<leader>vpu', ':Lazy home<CR>', { silent = true, noremap = true })
vim.keymap.set('n', '<leader>vpi', ':Lazy install<CR>', { silent = true, noremap = true })
vim.keymap.set('n', '<leader>vpc', ':Lazy clean<CR>', { silent = true, noremap = true })

vim.cmd [[set secure]]
