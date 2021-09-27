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

if (has("nvim"))
  set inccommand=nosplit       " live replace
endif

if (exists("+termguicolors"))
  let &t_8f="\<Esc>[38;2;%lu;%lu;%lum"
  let &t_8b="\<Esc>[48;2;%lu;%lu;%lum"
  set termguicolors
endif

" ================ Turn Off Swap Files ==============
set noswapfile
set nobackup
set nowritebackup

" Trailing spaces and tabs
set list
set listchars=tab:→\ ,nbsp:␣,trail:•,precedes:«,extends:»

let mapleader = ','

" searching stuff

" Make <C-L> clear highlight and redraw
nnoremap <C-\> :nohls<CR>
inoremap <C-\> <C-O>:nohls<CR>
" nnoremap * :keepjumps normal *``<cr>
nnoremap * *``

" Edit the vimrc file
nnoremap ev  :tabedit $MYVIMRC<CR>
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

" Enable filetype plugins to handle indents
filetype plugin indent on

" plugins:begin
let g:plug_url_format="git://github.com/%s"

" allow separate plugins per editor
if has('nvim-0.5.0')
  call plug#begin('~/.local/share/nvim-HEAD/plugged')
elseif has('nvim')
  call plug#begin('~/.local/share/nvim/plugged')
else
  call plug#begin('~/.local/share/vim/plugged')
endif

Plug 'AndrewRadev/splitjoin.vim'                    " split / join code blocks
Plug 'christoomey/vim-tmux-navigator'               " buffer navigation
Plug 'editorconfig/editorconfig-vim'                " .editorconfig integration
Plug 'janko-m/vim-test'                             " test integration
Plug 'junegunn/fzf', { 'do': { -> fzf#install() } }
Plug 'junegunn/fzf.vim'                             " fzf integration
Plug 'junegunn/vim-easy-align'                      " space align
Plug 'lanej/vim-phab'                               " vim-fugitive phab integration
Plug 'ludovicchabant/vim-gutentags'                 " automatically update tags
Plug 'mileszs/ack.vim'                              " quick search, configured to use rg or ag
Plug 'previm/previm', { 'for': 'markdown' }         " markdown preview with mermaid support
Plug 'scrooloose/nerdcommenter'                     " code commenter
Plug 'idanarye/vim-merginal'
Plug 'tpope/vim-dotenv'                             " support dotenv
Plug 'tpope/vim-eunuch'                             " file system interactions
Plug 'tpope/vim-fugitive'                           " git integratino
Plug 'tpope/vim-markdown', { 'for': 'markdown' }    " markdown tools
Plug 'tpope/vim-rhubarb'                            " vim-fugitive github integration
Plug 'tpope/vim-surround'                           " surround mod tools
Plug 'tyru/open-browser.vim', { 'for': 'markdown' } " xdg-open or open integration
Plug 'norcalli/nvim-colorizer.lua'
" Plug 'rcarriga/vim-ultest'

" ordered load required
Plug 'tpope/vim-obsession'        " sessions
Plug 'dhruvasagar/vim-prosession' " per-branch session auto management

if has('nvim')
  if has('nvim-0.5.0')
    Plug 'https://gitlab.com/yorickpeterse/nvim-window.git', {'branch': 'main'}
    Plug 'lewis6991/gitsigns.nvim', {'branch':'main'}
    Plug 'lukas-reineke/indent-blankline.nvim'
    Plug 'neovim/nvim-lspconfig'
    Plug 'nvim-lua/completion-nvim'
    Plug 'nvim-lua/lsp_extensions.nvim'
    Plug 'nvim-lua/plenary.nvim'
    Plug 'nvim-lua/popup.nvim'
    Plug 'ghifarit53/tokyonight-vim'
    Plug 'glepnir/galaxyline.nvim' , {'branch': 'main'}
    Plug 'kyazdani42/nvim-web-devicons' " lua
    Plug 'kyazdani42/nvim-tree.lua'
    Plug 'nvim-treesitter/nvim-treesitter'
    Plug 'nvim-treesitter/nvim-treesitter-textobjects'
    Plug 'nvim-treesitter/playground'
    Plug 'phaazon/hop.nvim'
    Plug 'David-Kunz/treesitter-unit', {'branch':'main'}
    Plug 'lewis6991/gitsigns.nvim', {'branch':'main'}
    Plug 'dense-analysis/ale'
    Plug 'folke/todo-comments.nvim', {'branch':'main'}
    " Plug 'nvim-telescope/telescope.nvim'
  else
    Plug 'ryanoasis/vim-devicons'
    Plug 'easymotion/vim-easymotion'                    " quick in-buffer navigation
    Plug 'airblade/vim-gitgutter'                       " show git diffs in left gutter
    Plug 'Yggdroot/indentLine', { 'for': ['ruby', 'python'] }
    Plug 'sheerun/vim-polyglot'
    Plug 'dense-analysis/ale'
    Plug 'neoclide/coc-neco', { 'for': 'vim' }
    Plug 'Shougo/neco-vim', { 'for': 'vim' }
    Plug 'neoclide/coc.nvim', {'branch':'release'}
  endif
endif

" plugins:end Add plugins to &runtimepath
call plug#end()

" plugin:tmux
let g:tmux_navigator_no_mappings = 1
let g:tmux_navigator_save_on_switch = 1

nnoremap <silent> <C-h> :TmuxNavigateLeft<cr>
nnoremap <silent> <C-j> :TmuxNavigateDown<cr>
nnoremap <silent> <C-k> :TmuxNavigateUp<cr>
nnoremap <silent> <C-l> :TmuxNavigateRight<cr>

" plugin-config start
map <leader>w :w<CR>
" map <leader>w! :SudoWrite<CR>
map <leader>x :x<CR>

" vim-plug
map <leader>vpi :PlugInstall<CR>
map <leader>vpc :PlugClean<CR>
map <leader>vpu :PlugUpdate<CR>

map <leader>rb :%s/<C-r><C-w>/
map <leader>rq :cfdo %s/<C-r><C-w>/

let g:vim_markdown_conceal = 0
let g:markdown_fenced_languages = ['html', 'python', 'bash=sh', 'ruby', 'go']

" gutentag
" let g:gutentags_define_advanced_commands = 1
" let g:gutentags_ctags_executable_ruby = 'rtags'

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

nnoremap <silent> [t :pop<cr>

" quickfix nav
nnoremap ]q :cnext<CR>
nnoremap [q :cprev<CR>

" terraform
let g:terraform_completion_keys = 1
let g:terraform_fmt_on_save     = 1
let g:terraform_align           = 1
let g:terraform_remap_spacebar  = 0

if executable('rg')
  " use ripgrep if available
  let g:ackprg = 'rg --vimgrep'
  set grepprg=rg\ --nogroup\ --nocolor
  nmap <leader>aa :Rg<space>
  nmap <leader>az :Rg<CR>
elseif executable('ag')
  " use silver-searcher if available
  let g:ackprg = 'ag --vimgrep'
  set grepprg=ag\ --nogroup\ --nocolor
  nmap <leader>aa :Ag<space>
  nmap <leader>az :Ag<CR>
endif

" sessions
map <leader>ps :Prosession<space>
let g:prosession_per_branch = 1

if &runtimepath =~ 'nerdtree'
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
  let g:NERDCreateDefaultMappings = 0

  map <leader>c<space> <plug>NERDCommenterToggle

  " Align line-wise comment delimiters flush left instead of following code indentation
  let g:NERDDefaultAlign = 'left'
endif

if &runtimepath =~ 'nvim-tree'
  map <leader>ntt :NvimTreeToggle<CR>
  map <leader>ntc :NvimTreeClose<CR>
  map <leader>ntf :NvimTreeFindFile<CR>
endif


" let g:indentLine_char = '⎸'
let g:indent_blankline_show_current_context = v:true
let g:indent_blankline_use_treesitter = v:true
" splitjoin
let g:splitjoin_ruby_curly_braces = 0

" airline
" if you want to disable auto detect, comment out those two lines
"let g:airline#extensions#disable_rtp_load = 1
" let g:airline_extensions = ['branch', 'hunks', 'coc']


if !exists('g:airline_symbols')
  let g:airline_symbols = {}
endif

let g:airline_left_alt_sep = ''
let g:airline_right_alt_sep = ''
let g:airline_symbols.branch = ''
let g:airline_symbols.crypt = '🔒'
let g:airline_symbols.dirty='ˉ'
let g:airline_symbols.linenr = '¶'
let g:airline_symbols.linenr = '☰'
let g:airline_symbols.maxlinenr = '㏑'
let g:airline_symbols.paste = '∥'
let g:airline_symbols.readonly = ''
let g:airline_symbols.spell = '✓'
let g:airline_symbols.whitespace = 'Ξ'
let g:airline_symbols.notexists = '⁉'

let g:airline#extensions#branch#enabled = 1
let g:airline#extensions#bufferline#enabled = 0
let g:airline#extensions#tabline#buffer_nr_show = 0
let g:airline#extensions#tabline#enabled = 1
let g:airline#extensions#tabline#show_tabs = 1
let g:airline#extensions#tabline#formatter = 'unique_tail_improved'
let g:airline#extensions#tabline#tab_nr_type = 0
let g:airline#extensions#tabline#show_buffers = 1
let g:airline#extensions#whitespace#enabled = 0
let g:airline#extensions#tabline#tab_min_count = 2
let g:airline#extensions#obsession#enabled = 0
let g:airline#extensions#ale#show_line_numbers = 0
let g:airline#extensions#wordcount#enabled = 0
let g:airline#extensions#hunks#enabled = 0
let g:airline_section_z=""
let g:airline_powerline_fonts = 0
let g:airline_theme = 'tokyonight'
let g:airline_focuslost_inactive = 1
let g:airline#extensions#tabline#switch_buffers_and_tabs = 0
let g:airline#extensions#tabline#show_tab_type = 0
let g:airline#extensions#tabline#show_close_button = 0
let g:airline#extensions#tabline#show_tab_count = 0
let g:ale_virtualtext_cursor = 1

" git-gutter
if exists('&signcolumn')  " Vim 7.4.2201
  set signcolumn=yes
else
  let g:gitgutter_sign_column_always = 1
endif

let g:gitgutter_max_signs = 1024
let g:gitgutter_sign_added = "❙"
let g:gitgutter_sign_modified = "❙"
let g:gitgutter_sign_modified_removed = "❙"
let g:gitgutter_sign_removed = "❙"
let g:gitgutter_sign_removed_first_line = "❙"
let g:gitgutter_show_msg_on_hunk_jumping = 0
let g:gitgutter_highlight_linenrs = 0
let g:gitgutter_highlight_lines = 0

if &runtimepath =~ 'hop.nvim'
  lua <<EOF
  require'hop'.setup()
EOF
  map <leader><leader>w :HopWord<CR>
  map <leader><leader>b :HopWordBC<CR>
  map <leader><leader>f :HopWordAC<CR>
  map <leader><leader>l :HopLineStart<CR>
  map <leader><leader>j :HopLineStartAC<CR>
  map <leader><leader>k :HopLineStartBC<CR>
  map <leader><leader>\ :HopPattern<CR>
endif


if &runtimepath =~ 'todo-comments'
lua << EOF
  require("todo-comments").setup { }
EOF
endif

if &runtimepath =~ 'galaxyline'
  lua <<EOF
  require ('galaxyline').short_line_list = {
  'Mundo',
  'MundoDiff',
  'NvimTree',
  'fugitive',
  'fugitiveblame',
  'help',
  'minimap',
  'qf',
  'tabman',
  'tagbar',
  'toggleterm'
}

local vi_mode_mapping = {
  ['']   = {'Empty',        '-'},
  ['!']  = {'Shell',        '-'},
  [''] = {'CommonVisual', 'B'}, -- NOTE: You'll have to remove '^V' and input a 'real' '^V' sequence. You can do that with the following key sequence: <SHIFT-i> + <CTRL-v> + <CTRL-v> (don't be slow with the double <CTRL-v>)
  ['R']  = {'Replace',      'R'},
  ['Rv'] = {'Normal',       '-'},
  ['S']  = {'Normal',       '-'},
  ['V']  = {'CommonVisual', 'V'},
  ['c']  = {'Command',      'C'},
  ['ce'] = {'Normal',       '-'},
  ['cv'] = {'Normal',       '-'},
  ['i']  = {'Insert',       'I'},
  ['ic'] = {'Normal',       '-'},
  ['n']  = {'Normal',       'N'},
  ['no'] = {'Normal',       '-'},
  ['r']  = {'Normal',       '-'},
  ['r?'] = {'Normal',       '-'},
  ['rm'] = {'Normal',       '-'},
  ['s']  = {'Normal',       '-'},
  ['t']  = {'Terminal',     'T'},
  ['v']  = {'CommonVisual', 'v'}
}

local colors = {
  bg = '#1a1b26',
  black = '#32344a',
  blue = '#7aa2f7',
  cyan = '#449dab',
  fg = '#a9b1d6',
  green = '#9ece6a',
  magenta = '#ad8ee6',
  orange = '#ff9e64',
  red = '#f7768e',
  white = '#787c99',
  yellow = '#e0af68',
}

-- Local helper functions
local mode_color = function()
  local mode_colors = {
    n = colors.cyan,
    i = colors.green,
    c = colors.orange,
    V = colors.yellow,
    [''] = colors.magenta,
    v = colors.blue,
    R = colors.red
  }

  local color = mode_colors[vim.fn.mode()]

  if color == nil then color = colors.red end

  return color
end


local gl = require('galaxyline')
local gls = gl.section

gls.left[1] = {
  ViMode = {
     provider = function()
       if vi_mode_mapping[vim.fn.mode()] == nil then
         return ' -'
       else
         vim.api.nvim_command('hi GalaxyViMode guibg=' .. mode_color())
         return ' ' .. string.format('%s', vi_mode_mapping[vim.fn.mode()][2]) .. ' '
       end
     end,
    highlight = {colors.bg, colors.bg},
  }
}
gls.left[2] = {
  LeftGitBranch = {
    provider = function()
      if require('galaxyline.condition').check_git_workspace() then
        return '   ' .. require('galaxyline.provider_vcs').get_git_branch()
      else
        return '   '
      end
    end,
    highlight = {colors.magenta, colors.bg},
    separator = ' ',
    separator_highlight = {colors.bg, colors.bg},
  }
}
gls.left[3] = {
  LeftGitDiffSeparator = {
    provider = function()
      return ''
    end,
    separator = ' ',
    highlight = { colors.magenta },
  }
}
gls.left[4] = {
  LeftGitDiffAdd = {
    condition = require("galaxyline.condition").check_git_workspace,
    provider = function()
      if require('galaxyline.provider_vcs').diff_add() then
        vim.api.nvim_command('hi GalaxyLeftGitDiffAdd guifg=' .. colors.green)
        return '+' .. require('galaxyline.provider_vcs').diff_add()
      else
        return '+0 '
      end
    end
  }
}
gls.left[5] = {
  LeftGitDiffModified = {
    condition = require("galaxyline.condition").check_git_workspace,
    provider = function()
      if require('galaxyline.provider_vcs').diff_modified() then
        vim.api.nvim_command('hi GalaxyLeftGitDiffModified guifg=' .. colors.cyan)
        return '~' .. require('galaxyline.provider_vcs').diff_modified()
      else
        return '~0 '
      end
    end
  }
}
gls.left[6] = {
  LeftGitDiffRemove = {
    condition = require("galaxyline.condition").check_git_workspace,
    provider = function()
      if require('galaxyline.provider_vcs').diff_remove() then
        vim.api.nvim_command('hi GalaxyLeftGitDiffRemove guifg=' .. colors.red)
        return '-' .. require('galaxyline.provider_vcs').diff_remove()
      else
        return '-0 '
      end
    end
  }
}

gls.mid[1] = {
  MidFileName = {
    provider = function()
      if vim.fn.expand '%:p' == 0 then
        return '-'
      end
      if vim.fn.winwidth(0) > 50 then
        return vim.fn.expand '%:~'
      else
        return vim.fn.expand '%:t'
      end
    end,
    highlight = { colors.fg, colors.black },
  }
}

gls.right[1] = {
  RightLspError = {
    provider = function()
      if #vim.tbl_keys(vim.lsp.buf_get_clients()) <= 0 then
         return
      end

      if vim.lsp.diagnostic.get_count(0, 'Error') == 0 then
        vim.api.nvim_command('hi GalaxyRightLspError guifg=' .. colors.fg)
      else
        vim.api.nvim_command('hi GalaxyRightLspError guifg=' .. colors.red)
      end

      return '!' .. vim.lsp.diagnostic.get_count(0, 'Error') .. ' '
    end
  }
}

gls.right[2] = {
  RightLspWarning = {
    provider = function()
      if #vim.tbl_keys(vim.lsp.buf_get_clients()) <= 0 then
         return
      end

      if vim.lsp.diagnostic.get_count(0, 'Warning') == 0 then
        vim.api.nvim_command('hi GalaxyRightLspWarning guifg=' .. colors.fg)
      else
        vim.api.nvim_command('hi GalaxyRightLspWarning guifg=' .. colors.orange)
      end

      return '?' .. vim.lsp.diagnostic.get_count(0, 'Warning') .. ' '
    end
  }
}

gls.right[3] = {
 RightLspInformation = {
   provider = function()
     if #vim.tbl_keys(vim.lsp.buf_get_clients()) <= 0 then
        return
     end

     if vim.lsp.diagnostic.get_count(0, 'Information') == 0 then
        vim.api.nvim_command('hi GalaxyRightLspInformation guifg=' .. colors.fg)
     else
        vim.api.nvim_command('hi GalaxyRightLspInformation guifg=' .. colors.blue)
     end

     return '+' .. vim.lsp.diagnostic.get_count(0, 'Information') .. ' '
   end
 }
}

gls.right[4] = {
  RightLspHint = {
    provider = function()
      if #vim.tbl_keys(vim.lsp.buf_get_clients()) <= 0 then
         return
      end

      if vim.lsp.diagnostic.get_count(0, 'Hint') == 0 then
        vim.api.nvim_command('hi GalaxyRightLspHint guifg=' .. colors.fg)
      else
        vim.api.nvim_command('hi GalaxyRightLspHint guifg=' .. colors.yellow)
      end

      return '-' .. vim.lsp.diagnostic.get_count(0, 'Hint') .. ' '
    end
  }
}

gls.right[5] = {
 RightLspHintSeparator = {
   highlight = { colors.yellow, colors.bg },
   provider = function()
     return ''
   end,
 }
}

gls.right[6] = {
  RightLspClient = {
    highlight = { colors.fg, colors. bg },
    provider = function()
      if #vim.tbl_keys(vim.lsp.buf_get_clients()) >= 1 then
        local lsp_client_name_first = vim.lsp.get_client_by_id(tonumber(vim.inspect(vim.tbl_keys(vim.lsp.buf_get_clients())):match('%d+'))).name:match('%l+')

        if lsp_client_name_first == nil then
          vim.api.nvim_command('hi GalaxyRightLspClient guifg=' .. colors.fg)
          return #vim.tbl_keys(vim.lsp.buf_get_clients()) .. ': '
        else
          vim.api.nvim_command('hi GalaxyRightLspClient guifg=' .. colors.yellow)
          return #vim.tbl_keys(vim.lsp.buf_get_clients()) .. ':' .. lsp_client_name_first .. ' '
        end
      else
        return ' '
      end
    end,
    separator = ' ',
  }
}

gls.right[7] = {
 RightPositionSeparator = {
   provider = function()
     return '  '
   end
 }
}

require ('galaxyline').section.short_line_left = {
  {
    ShortLineLeftBufferType = {
      highlight = 'GalaxyMapperCommon2',
      provider = function ()
        local BufferTypeMap = {
          ['Mundo'] = 'Mundo History',
          ['MundoDiff'] = 'Mundo Diff',
          ['NvimTree'] = 'Nvim Tree',
          ['fugitive'] = 'Fugitive',
          ['fugitiveblame'] = 'Fugitive Blame',
          ['help'] = 'Help',
          ['minimap'] = 'Minimap',
          ['qf'] = 'Quick Fix',
          ['tabman'] = 'Tab Manager',
          ['tagbar'] = 'Tagbar',
          ['toggleterm'] = 'Terminal'
        }
        local name = BufferTypeMap[vim.bo.filetype] or 'Editor'
        return string.format('  %s ', name)
      end,
      separator = ' ',
      separator_highlight = 'GalaxyMapperCommon7'
    }
  },
  {
    ShortLineLeftWindowNumber = {
      highlight = 'GalaxyMapperCommon6',
      provider = function()
        return '  ' .. vim.api.nvim_win_get_number(vim.api.nvim_get_current_win()) .. ' '
      end,
      separator = '',
      separator_highlight = 'GalaxyMapperCommon1'
    }
  }
}

require ('galaxyline').section.short_line_right = {
  {
    ShortLineRightBlank = {
      highlight = 'GalaxyMapperCommon6',
      provider = function()
        if vim.bo.filetype == 'toggleterm' then
          return ' ' .. vim.api.nvim_buf_get_var(0, 'toggle_number') .. ' '
        else
          return '  '
        end
      end,
      separator = '',
      separator_highlight = 'GalaxyMapperCommon1'
    }
  },
  {
    ShortLineRightInformational = {
      highlight = 'GalaxyMapperCommon2',
      provider = function()
        return ' Neovim '
      end,
      separator = '',
      separator_highlight = 'GalaxyMapperCommon7'
    }
  }
}

EOF
endif


if &runtimepath =~ 'gitsigns'
  lua <<EOF
  require('gitsigns').setup()
EOF
  map <leader>gl :Gitsigns blame_line<CR>
endif

command! -bang -nargs=* Rg
      \ call fzf#vim#grep(
      \   'rg --column --line-number --no-heading --color=always --smart-case -- '.shellescape(<q-args>), 1,
      \   fzf#vim#with_preview(), <bang>0)

command! -nargs=* Rgc
      \ call fzf#vim#grep(
      \   'rg --column --line-number --no-heading --color=always --smart-case -- '.shellescape(expand('<cword>')), 1,
      \   fzf#vim#with_preview(), <bang>0)

command! -bang -nargs=? -complete=dir DFiles
      \ call fzf#run(fzf#wrap({'source': 'fd . --full-path '.shellescape(expand('%:h'))}))

" TODO: change Buffers to use a smaller list and different orientation for
" quick differention

let g:fzf_colors = {
      \ 'fg':      ['fg', 'Normal'],
      \ 'bg':      ['bg', 'Normal'],
      \ 'hl':      ['fg', 'String'],
      \ 'fg+':     ['fg', 'Function', 'CursorColumn', 'Normal'],
      \ 'bg+':     ['bg', 'Type', 'CursorColumn'],
      \ 'hl+':     ['fg', 'String'],
      \ 'info':    ['fg', 'Function'],
      \ 'border':  ['fg', 'Ignore'],
      \ 'prompt':  ['fg', 'Function'],
      \ 'pointer': ['fg', 'Type'],
      \ 'marker':  ['fg', 'Function'],
      \ 'spinner': ['fg', 'Function'],
      \ 'header':  ['fg', 'Function']}

noremap <leader>af :DFiles<CR>
" [Buffers] Jump to the existing window if possible
let g:fzf_buffers_jump = 1

" [[B]Commits] Customize the options used by 'git log':
let g:fzf_commits_log_options = '--color=always --format="%C(auto)%h%d %s %C(black)%C(bold)%cr"'

" fugitive and fzf git integrations
autocmd  BufReadPost fugitive://* set bufhidden=delete

if &runtimepath =~ 'telescope'
  nmap <leader>ac :Telescope commands<CR>
  nmap <leader>ah :Telescope help_tags<CR>
  nmap <leader>bl :Telescope current_buffer_fuzzy_find<CR>
  nmap <leader>at :Telescope tags<CR>
  nmap <leader>az :Telescope live_grep<CR>
  nmap <leader>bc :Telescope git_bcommits<CR>
  nmap <leader>bb :Telescope buffers<CR>
  nmap <leader>bt :Telescope current_buffer_tags<CR>
  nmap <leader>bv :Telescope treesitter<CR>
  nmap <leader>f  :Telescope find_files<CR>
  nmap <leader>gc :Telescope git_commits<CR>
  nmap <leader>gf :Telescope git_files<CR>
  nmap <leader>l  :Telescope current_buffer_fuzzy_find<CR>
  nmap <leader>rr :Telescope command_history<CR>
  nmap <leader>/  :Telescope search_history<CR>
else
  nnoremap <leader>as :Rgc<space><cword><CR>
  nnoremap <leader>ag :Ack<CR>
  nnoremap <leader>ac :Commands<CR>
  nnoremap <leader>al :Lines<CR>
  nnoremap <leader>at :Tags<CR>
  nnoremap <leader>f  :Files<CR>
  nnoremap <leader>rr :History:<CR>
  nnoremap <leader>/  :History/<CR>
  nnoremap <leader>bl  :BLines<CR>
  nnoremap <leader>bt :BTags<CR>
  noremap  <leader>bc :BCommits<CR>
  noremap  <leader>gf :GFiles<CR>
  noremap  <leader>bb :Buffers<CR>
  noremap  <leader>gc :Commits<CR>
endif

nmap <leader>gm :Git mergetool<CR>
nmap <leader>go :GBrowse<CR>
nmap <leader>gt :Gcommit -am'wip'<CR>
nmap <leader>gr :Gread<CR>
nmap <leader>gs :Git<CR>
nmap <leader>gw :Gwrite<CR>
nmap <leader>ga :Gcommit -av<CR>
nmap <leader>gb :Git blame<CR>
nmap <leader>gp :Git push<CR>
nmap <leader>gc :Gcommit<CR>
nmap <leader>gd :Gdiffsplit origin/master
nmap <leader>as :Rgc<space><cword><CR>
nmap <leader>ag :Ack<CR>

" rename
map <leader>re :Rename<space>

"terminal
if has("nvim")
  tnoremap <C-o> <C-\><C-n>
endif

" noremap <leader>sh :terminal<cr>
nnoremap yd :let @" = expand("%")<cr>
" plugin-config end

" =============== UI ================
syntax enable      " turn syntax highlighting on
colorscheme tokyonight " set that smooth smooth color scheme
set guioptions-=T  " remove Toolbar
set guioptions-=r  " remove right scrollbar
set guioptions-=L  " remove left scrollbar
set number         " show line numbers
set laststatus=2   " Prevent the ENTER prompt more frequently

set completeopt=menu,noinsert,noselect

" ================ Scrolling ========================
set scrolloff=8         "Start scrolling when we're 8 lines away from margins
set sidescrolloff=15
set sidescroll=1

" ================ Status Line ======================
if has('cmdline_info')
  set showcmd " Show partial commands in status line and selected characters/lines in visual mode
endif

" polyglot syntax cues
let ruby_operators=1
let ruby_space_errors=1
let ruby_line_continuation_error=1
let ruby_no_expensive=1

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

set shortmess=a

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

" vim-go config
let g:go_addtags_transform = "snakecase"
let g:go_auto_sameids = 0
let g:go_auto_type_info = 0 " often overrides command window
let g:go_decls_mode = 'gopls'
let g:go_def_mode='gopls'
let g:go_fmt_command = 'goimports'
let g:go_fmt_fail_silently = 1
let g:go_highlight_build_constraints = 1
let g:go_highlight_extra_types = 1
let g:go_highlight_fields = 1
let g:go_highlight_function_calls = 1
let g:go_highlight_functions = 1
let g:go_highlight_generate_tags = 1
let g:go_highlight_methods = 1
let g:go_highlight_operators = 1
let g:go_highlight_structs = 1
let g:go_highlight_types = 1
let g:go_highlight_variable_assignments = 1
let g:go_highlight_variable_declarations = 1
let g:go_fmt_autosave = 0
let g:go_info_mode='gopls'
let g:go_list_type = 'quickfix'
let g:go_doc_popup_window = 1
let g:go_doc_keywordprg_enabled = 0
" let g:go_snippet_engine = "neosnippet"

if has('conceal')
  set conceallevel=0 concealcursor=niv
endif

if &runtimepath =~ 'lspconfig'
  " nnoremap <silent> <c-k> <cmd>lua vim.lsp.buf.signature_help()<CR>
  nnoremap <silent> K          <cmd>lua vim.lsp.buf.hover()<CR>
  nnoremap <silent> <leader>cd <cmd>lua vim.lsp.buf.definition()<CR>
  nnoremap <silent> <leader>cr <cmd>lua vim.lsp.buf.references()<CR>
  nnoremap <silent> <leader>d  <cmd>lua vim.lsp.buf.formatting_sync()<CR>
  nnoremap <silent> <leader>ci <cmd>lua vim.lsp.buf.implementation()<CR>
  nnoremap <silent> <leader>cy <cmd>lua vim.lsp.buf.type_definition()<CR>
  nnoremap <silent> <leader>rn <cmd>lua vim.lsp.buf.rename()<CR>
  nnoremap <silent> <leader>ca <cmd>lua vim.lsp.buf.code_action()<CR>

  sign define LspDiagnosticsSignError text=✖ texthl=LspDiagnosticsDefaultError linehl= numhl=
  sign define LspDiagnosticsSignWarning text=⚠ texthl=LspDiagnosticsDefaultWarning linehl= numhl=
  sign define LspDiagnosticsSignInformation text=i texthl=LspDiagnosticsDefaultInformation linehl= numhl=
  sign define LspDiagnosticsSignHint text=? texthl=LspDiagnosticsDefaultHint linehl= numhl=

  autocmd BufEnter * lua require'completion'.on_attach()

  " lua vim.lsp.set_log_level("debug")
  lua <<EOF
  lsp = require'lspconfig'
  lsp.solargraph.setup{}
  lsp.gopls.setup{}
  lsp.vimls.setup{}
  lsp.yamlls.setup{}
  lsp.sumneko_lua.setup{
  cmd = {"lua-language-server"};
  }
  lsp.jedi_language_server.setup{}
  lsp.texlab.setup{}
  lsp.jsonls.setup {
    commands = {
      Format = {
        function()
          vim.lsp.buf.range_formatting({},{0,0},{vim.fn.line("$"),0})
        end
      }
    }
  }

  local on_attach = function(client)
    require'completion'.on_attach(client)
  end

  local capabilities = vim.lsp.protocol.make_client_capabilities()
  capabilities.textDocument.completion.completionItem.snippetSupport = true

  lsp.rust_analyzer.setup({
    capabilities=capabilities,
    on_attach=on_attach,
    settings = {
      ["rust-analyzer.cargo.allFeatures"] = true
    }
  })

  -- Enable diagnostics
  vim.lsp.handlers["textDocument/publishDiagnostics"] = vim.lsp.with(
    vim.lsp.diagnostic.on_publish_diagnostics, {
      virtual_text = false,
      signs = true,
      update_in_insert = true,
    }
  )
EOF

  nnoremap <silent><c-p> <cmd>lua vim.lsp.diagnostic.goto_prev()<CR>
  nnoremap <silent><c-n> <cmd>lua vim.lsp.diagnostic.goto_next()<CR>
  nnoremap <silent><space>c <cmd>lua vim.lsp.diagnostic.set_loclist()<CR>
endif

if &runtimepath =~ 'nvim-treesitter'
  lua <<EOF
  require'nvim-treesitter.configs'.setup({
    ensure_installed = "maintained",
    highlight = {
      enable = true,
    },
    indent = {
      enable = true
    },
    textobjects = {
      select = {
        enable = true,
        lookahead = true,
        keymaps = {
          ["af"] = "@function.outer",
          ["if"] = "@function.inner",
          ["ac"] = "@class.outer",
          ["ic"] = "@class.inner",
          ["ab"] = "@block.outer",
          ["ib"] = "@block.inner",
          ["ap"] = "@parameter.outer",
          ["ip"] = "@parameter.inner",
          ["ai"] = "@conditional.outer",
          ["ii"] = "@conditional.inner",
          ["ax"] = "@call.outer",
          ["ix"] = "@call.inner",
          ["an"] = "@statement.outer",
        },
      },
      swap = {
        enable = true,
        swap_next = {
          ["<leader>a"] = "@parameter.inner",
        },
        swap_previous = {
          ["<leader>A"] = "@parameter.inner",
        },
      },
      move = {
        enable = true,
        set_jumps = true, -- whether to set jumps in the jumplist
        goto_next_start = {
          ["]m"] = "@function.outer",
          ["]]"] = "@class.outer",
        },
        goto_next_end = {
          ["]M"] = "@function.outer",
          ["]["] = "@class.outer",
        },
        goto_previous_start = {
          ["[m"] = "@function.outer",
          ["[["] = "@class.outer",
        },
        goto_previous_end = {
          ["[M"] = "@function.outer",
          ["[]"] = "@class.outer",
        },
      },
    }
  })
EOF

vnoremap as :lua require"treesitter-unit".select()<CR>
onoremap as :<c-u>lua require"treesitter-unit".select()<CR>
endif

if &runtimepath =~ 'completion-nvim'
  autocmd BufEnter * lua require'completion'.on_attach()
endif

if &runtimepath =~ 'nvim-window'
  lua <<EOF
  require('nvim-window').setup({
    -- The characters available for hinting windows.
    chars = {
      'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
      'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'
    },

    -- A group to use for overwriting the Normal highlight group in the floating
    -- window. This can be used to change the background color.
    normal_hl = 'Type',

    -- The highlight group to apply to the line that contains the hint characters.
    -- This is used to make them stand out more.
    hint_hl = 'Bold',

    -- The border style to use for the floating window.
    border = 'double'
  })
EOF

  map <silent> <c-w><c-w> :lua require('nvim-window').pick()<CR>
endif


if &runtimepath =~ 'coc.nvim'
  nnoremap <silent> <leader>"  :<C-u>CocList -A --normal yank<cr>
  " Use <c-space> to trigger completion.
  inoremap <silent><expr> <c-space> coc#refresh()
  inoremap <expr> <cr> pumvisible() ? "\<C-y>" : "\<C-g>u\<CR>"

  " Use `[c` and `]c` to navigate diagnostics
  nmap <silent><C-p> <Plug>(coc-diagnostic-prev)
  nmap <silent><C-n> <Plug>(coc-diagnostic-next)

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
  " Remap keys for gotos
  xmap <leader>cd <Plug>(coc-definition)
  nmap <leader>cd <Plug>(coc-definition)
  xmap <leader>cy <Plug>(coc-type-definition)
  nmap <leader>cy <Plug>(coc-type-definition)
  xmap <leader>ci <Plug>(coc-implementation)
  nmap <leader>ci <Plug>(coc-implementation)
  xmap <leader>cr <Plug>(coc-references)
  nmap <leader>cr <Plug>(coc-references)

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

  nmap <leader>ce  <Plug>(coc-refactor)

  " Remap for do codeAction of current line
  nmap <leader>ca  <Plug>(coc-codeaction)
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
  " Search workspace symbols
  nnoremap <silent> <space>s  :<C-u>CocList -I symbols<cr>
  " Do default action for next item.
  nnoremap <silent> <space>p  :<C-u>CocListResume<CR>
endif

if &runtimepath =~ 'ale'
  let g:ale_fixers = {
        \ 'ruby': ['rubocop'],
        \ 'rspec': ['rubocop'],
        \ 'javascript.jsx': ['eslint'],
        \ 'javascript': ['eslint'],
        \ 'json': ['jq'],
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

  augroup filetype_ruby_ale
    autocmd!
    autocmd FileType ruby map <leader>d :ALEFix<CR>
    autocmd FileType ruby nmap <silent><C-p> <Plug>(ale_previous_wrap)
    autocmd FileType ruby nmap <silent><C-n> <Plug>(ale_next_wrap)
    autocmd FileType ruby set colorcolumn=100
  augroup END
endif

if &runtimepath =~ 'playground'
  map gm :TSHighlightCapturesUnderCursor<CR>
else
  function! SynStack ()
    for i1 in synstack(line("."), col("."))
      let i2 = synIDtrans(i1)
      let n1 = synIDattr(i1, "name")
      let n2 = synIDattr(i2, "name")
      echo n1 "->" n2
    endfor
  endfunction
  map gm :call SynStack()<CR>
endif

let g:jedi#auto_initialization = 0

function! SourceEnv()
  if get(v:event, "cwd") == get(g:, "source_env_dir", "")
    return
  else
    let g:source_env_dir = get(v:event, "cwd")
  end

  if filereadable(".env")
    silent! Dotenv .env
  endif

  if filereadable(".env-override")
    silent! Dotenv .env-override
  endif

  if &runtimepath =~ 'coc.nvim'
    silent! CocRestart
  endif
endfunction

if has('autocmd')
  augroup FiletypeGroup
    autocmd!
    " jsx is both javascript and jsx
    autocmd BufNewFile,BufRead *.jsx set filetype=javascript.jsx
    " Save files when vim loses focus
    autocmd FocusLost,BufLeave * silent! wa
    " Reload files when vim gains focus
    autocmd FocusGained,BufEnter * :checktime
    " Default spellcheck off
    autocmd BufRead,BufNewFile,BufEnter set nospell|set textwidth=0|set number
    " Source .env files
    if has('nvim')
      autocmd DirChanged * call SourceEnv()
    endif
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
let g:test#runner_commands = ['PyTest', 'RSpec', 'GoTest']

map <leader>tf :TestFile<CR>
map <leader>tu :TestNearest<CR>
map <leader>tt :TestNearest<CR>
map <leader>tl :TestLast<CR>
map <leader>ts :TestSuite<CR>

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
" Configure lsp
" https://github.com/neovim/nvim-lspconfig#rust_analyzer
lua <<EOF
-- nvim_lsp object
EOF

:match ExtraWhitespace /\s\+$/

" Enable type inlay hints
autocmd CursorMoved,InsertLeave,BufEnter,BufWinEnter,TabEnter,BufWritePost *.rs
\ lua require'lsp_extensions'.inlay_hints{ prefix = '', highlight = "LspInlay", enabled = {"TypeHint", "ChainingHint", "ParameterHint"} }
