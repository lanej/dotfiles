--
-- |_ _| \ | |_ _|_   _| |_   _  __ _
--  | ||  \| || |  | | | | | | |/ _` |
--  | || |\  || |  | |_| | |_| | (_| |
-- |___|_| \_|___| |_(_)_|\__,_|\__,_|
--

vim.opt.autoread = true
vim.opt.autoindent = true
vim.opt.backspace = { "indent", "eol", "start" }
vim.opt.cmdheight = 2
vim.opt.cursorline = true
vim.opt.encoding = "utf-8"
vim.opt.exrc = true
vim.opt.fileformats:append("mac")
vim.opt.guicursor = {
	"n-v-c:block-Cursor",
	"i:ver100-iCursor",
	"n-v-c:blinkon0",
}
vim.opt.hidden = true
vim.opt.history = 10000
vim.opt.hlsearch = true
vim.opt.ignorecase = true
vim.opt.incsearch = true
-- vim.opt.lazyredraw = true -- Don't redraw while executing macros (good performance config)
vim.opt.completeopt = { "menu", "menuone", "noselect", "preview", "noinsert" }
vim.opt.magic = true
vim.opt.modelines = 5
vim.opt.backup = false
vim.opt.scrolloff = 7
vim.opt.shell = os.getenv("SHELL")
vim.opt.showcmd = true
vim.opt.showmatch = true
vim.opt.matchtime = 2
vim.opt.showmode = true
vim.opt.smartcase = true
vim.opt.smarttab = true
vim.opt.tabpagemax = 15
vim.opt.title = true
vim.opt.ttimeout = true
vim.opt.ttimeoutlen = 50
vim.opt.vb = false
vim.opt.eb = false

-- equalalways: always keep the window size the same
-- except for nerdtree undotree andl;
vim.api.nvim_create_autocmd("BufEnter", {
	pattern = "NERD_tree*",
	command = "setlocal equalalways=false",
})
vim.api.nvim_create_autocmd("BufEnter", {
	pattern = "undotree*",
	command = "setlocal equalalways=false",
})
vim.opt.equalalways = true

vim.opt.updatetime = 300
vim.opt.spell = false
vim.opt.shortmess:append("c")
vim.opt.shortmess:append("T")
vim.opt.shortmess:append("a")
vim.opt.shortmess:append("W")
vim.opt.swapfile = false
vim.opt.backup = false
vim.opt.writebackup = false
vim.opt.wrap = true
vim.opt.list = true
vim.opt.listchars = { tab = "→ ", nbsp = "␣", trail = "•", precedes = "«", extends = "»" }
vim.cmd("set cedit=<C-v>")

vim.g.mapleader = ","

vim.opt.inccommand = "nosplit" -- live replace
vim.opt.termguicolors = true

-- searching stuff
vim.api.nvim_set_keymap("n", "<C-\\>", ":nohls<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("i", "<C-\\>", "<C-O>:nohls<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "*", "*``", { noremap = true, silent = true })

-- Edit the vimrc file
vim.api.nvim_set_keymap("n", "ev", ":e $MYVIMRC<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "evr", ":source $MYVIMRC<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "tt", ":tablast<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "te", ":tabedit<Space>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "tn", ":tabnext<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "tp", ":tabprev<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "tc", ":tabnew<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "tm", ":tabm<Space>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "tx", ":tabclose<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "t1", "1gt<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "t2", "2gt<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "t3", "3gt<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "t4", "4gt<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "t5", "5gt<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "t6", "6gt<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "fbk", ":bd!<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "fak", ":%bd!|e#<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>bo", ":bp<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>bi", ":bn<CR>", { noremap = true, silent = true })

-- Enable filetype plugins to handle indents
vim.cmd("filetype plugin indent on")

-- plugin-config start
vim.api.nvim_set_keymap("n", "<leader>w", ":w<CR>", { noremap = true, silent = true })
-- vim.api.nvim_set_keymap('n', '<leader>w!', ':SudoWrite<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>x", ":x<CR>", { noremap = true, silent = true })

-- replace current word
vim.api.nvim_set_keymap("n", "<leader>rw", ":%s/<C-r><C-w>//gc<left><left><left>", { noremap = true })
vim.api.nvim_set_keymap("v", "<leader>rw", ":s/<C-r><C-w>//gc<left><left><left>", { noremap = true })

-- legacy support for the muscle memory
vim.api.nvim_set_keymap("n", "<leader>rb", ":%s/<C-r><C-w>//gc<left><left><left>", { noremap = true })
vim.api.nvim_set_keymap("v", "<leader>rb", ":s/<C-r><C-w>//gc<left><left><left>", { noremap = true })

-- replace current selection
vim.api.nvim_set_keymap("n", "<leader>rs", '"hy:%s/<C-r>h//gc<left><left><left>', { noremap = true })
vim.api.nvim_set_keymap("v", "<leader>rs", '""hy:s/<C-r>h//gc<left><left><left>', { noremap = true })

-- replace current word in all quicklist files
vim.api.nvim_set_keymap("n", "<leader>rq", ":cfdo %s/<C-r><C-w>/", { noremap = true })
vim.api.nvim_set_keymap("v", "<leader>rq", ":cfdo s/<C-r><C-w>/", { noremap = true })

-- quickfix nav
vim.api.nvim_set_keymap("n", "]q", ":cnext<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "[q", ":cprev<CR>", { noremap = true, silent = true })

-- Set leader key
vim.g.mapleader = ","

-- NvimTree mappings
vim.api.nvim_set_keymap("n", "<leader>ntt", ":NvimTreeToggle<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>ntc", ":NvimTreeClose<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>ntf", ":NvimTreeFindFile<CR>", { noremap = true, silent = true })

-- Rename mapping
vim.api.nvim_set_keymap("n", "<leader>re", ":Rename ", { noremap = true })

-- Terminal mode escape
vim.api.nvim_set_keymap("t", "<C-o>", "<C-\\><C-n>", { noremap = true })

-- Yank current file path
vim.api.nvim_set_keymap("n", "yd", ':let @" = expand("%")<CR>', { noremap = true })

-- Enable syntax highlighting
vim.cmd("syntax enable")

-- GUI options
-- vim.o.guioptions:remove("T") -- remove Toolbar
-- vim.o.guioptions:remove("r") -- remove right scrollbar
-- vim.o.guioptions:remove("L") -- remove left scrollbar

-- Line numbers
vim.opt.number = true

-- Status line
vim.opt.laststatus = 2

-- Scrolling options
vim.opt.scrolloff = 8
vim.opt.sidescrolloff = 15
vim.opt.sidescroll = 1

-- Status line command
if vim.fn.has("cmdline_info") == 1 then
	vim.opt.showcmd = true
end

-- Change working directory mappings
vim.api.nvim_set_keymap("n", "<leader>ct", ":cd %:p:h<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>cg", ":Gcd<CR>", { noremap = true, silent = true })

-- Disable Ex mode
vim.api.nvim_set_keymap("n", "Q", "<Nop>", { noremap = true })

-- Helpers
vim.api.nvim_set_keymap("n", "<leader>srt", ":!sort<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>uq", ":!uniq<CR>", { noremap = true, silent = true })

-- Wrapped lines navigation
vim.api.nvim_set_keymap("n", "j", "gj", { noremap = true })
vim.api.nvim_set_keymap("n", "k", "gk", { noremap = true })

-- Command aliases
vim.api.nvim_create_user_command("Q", "q", {})
vim.api.nvim_create_user_command("Qa", "qa", {})
vim.api.nvim_create_user_command("W", "w", {})
vim.api.nvim_create_user_command("Wa", "wa", {})
vim.api.nvim_create_user_command("Wqa", "wqa", {})
vim.api.nvim_create_user_command("Qwa", "wqa", {})
vim.api.nvim_create_user_command("E", "e", {})

-- TODO: ale is only used for legacy ruby linting but conform.nvim could replace this i think
vim.g.ale_fixers = {
	ruby = { "rubocop" },
	rspec = { "rubocop" },
	["javascript.jsx"] = { "eslint" },
	javascript = { "eslint" },
	json = { "jq" },
	sh = { "shfmt" },
}

vim.g.ale_linters = {
	ruby = { "rubocop" },
	rspec = { "rubocop" },
	["javascript.jsx"] = { "eslint" },
	javascript = { "eslint" },
}

vim.g.ale_keep_list_window_open = 0
vim.g.ale_lint_delay = 200
vim.g.ale_lint_on_enter = 1
vim.g.ale_lint_on_save = 1
vim.g.ale_lint_on_text_changed = "always"
vim.g.ale_open_list = 0
vim.g.ale_ruby_bundler_executable = "bundle"
vim.g.ale_ruby_rubocop_executable = "bundle"
vim.g.ale_set_loclist = 0
vim.g.ale_linters_explicit = 1
vim.g.ale_set_quickfix = 0
vim.g.ale_sign_column_always = 1
vim.g.ale_sign_error = ">>"
vim.g.ale_echo_cursor = 0
vim.g.ale_sign_offset = 1000000
vim.g.ale_sign_warning = "--"
vim.g.ale_completion_enabled = 0
vim.g.ale_use_neovim_diagnostics_api = 1

-- Start interactive EasyAlign in visual mode (e.g. vipga)
vim.api.nvim_set_keymap("x", "ga", "<Plug>(EasyAlign)", {})

-- Start interactive EasyAlign for a motion/text object (e.g. gaip)
vim.api.nvim_set_keymap("n", "ga", "<Plug>(EasyAlign)", {})

-- Realign the whole file
vim.api.nvim_set_keymap("n", "<leader>D", "ggVG=<CR>", { noremap = true, silent = true })

-- Clang format style options
vim.g.clang_format_style_options = {
	AccessModifierOffset = -4,
	AllowShortIfStatementsOnASingleLine = "true",
	AlwaysBreakTemplateDeclarations = "true",
	Standard = "C++11",
}

-- Set make program
vim.opt.makeprg = "make -j9"
vim.api.nvim_set_keymap("n", "<Leader>m", ":make!<CR>", { noremap = true, silent = true })

-- Create parent directories on write
if not vim.fn.exists("*s:MkNonExDir") then
	function _G.MkNonExDir(file, buf)
		if vim.fn.empty(vim.fn.getbufvar(buf, "&buftype")) == 1 and not string.match(file, "^%w+:") then
			local dir = vim.fn.fnamemodify(file, ":h")
			if vim.fn.isdirectory(dir) == 0 then
				vim.fn.mkdir(dir, "p")
			end
		end
	end
end

-- Maintain undo history between sessions
vim.opt.undofile = true

-- Conceal settings
if vim.fn.has("conceal") == 1 then
	vim.opt.conceallevel = 0
end

-- Highlight captures under cursor
vim.api.nvim_set_keymap("n", "<space>th", ":TSHighlightCapturesUnderCursor<CR>", { noremap = true, silent = true })

-- Disable Jedi auto initialization
vim.g.jedi_auto_initialization = 0

-- Source environment on directory change
function _G.SourceEnvOnDirChange()
	if vim.tbl_contains(vim.tbl_keys(vim.v.event), "cwd") then
		local sources = SourceEnv()
		if sources then
			print("reloaded env")
		end
	end
end

vim.g.dotenv_files = { ".env", ".env-build", ".env-runtime", ".env-override", ".env-secrets" }

-- Load all vim.g.dotenv_files in the current directory if present
-- @param files table
-- @return table
function _G.SourceEnv(files)
	files = files or vim.g.dotenv_files
	local loaded = {}
	for _, file in ipairs(vim.g.dotenv_files) do
		if vim.fn.filereadable(file) == 1 then
			table.insert(loaded, file)
			vim.cmd("silent! Dotenv " .. file)
		end
	end
	return loaded
end

vim.api.nvim_set_keymap("n", "<leader>se", ":lua SourceEnv()<CR>", { noremap = true, silent = true })

-- Print environment variables
function _G.Env()
	local evars = vim.fn.environ()
	for _, var in ipairs(vim.fn.sort(vim.tbl_keys(evars))) do
		print(var .. "=" .. evars[var])
	end
end

vim.api.nvim_set_keymap("n", "<silent><leader>ee", ":e .env<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<silent><leader>eo", ":e .env-override<CR>", { noremap = true, silent = true })

-- Go debug nearest
function _G.GoDebugNearest()
	vim.g.test_go_runner = "delve"
	vim.cmd("TestNearest")
	vim.cmd("unlet g:test_go_runner")
end

-- Redraw the screen when gaining focus
vim.api.nvim_create_autocmd("FocusGained", {
	pattern = "*",
	command = "redraw!",
})

-- Check if the file has been changed outside of Vim when gaining focus or entering a buffer
vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter" }, {
	pattern = "*",
	command = "checktime",
})

-- Source environment on directory change
vim.api.nvim_create_autocmd("DirChanged", {
	pattern = "*",
	callback = function()
		SourceEnvOnDirChange()
	end,
})

-- Source environment on Vim enter
vim.api.nvim_create_autocmd("VimEnter", {
	pattern = "*",
	callback = function()
		SourceEnv()
	end,
})

-- Terminal settings
vim.api.nvim_create_augroup("filetype_terminal", { clear = true })
vim.api.nvim_create_autocmd("TermEnter", {
	group = "filetype_terminal",
	pattern = "*",
	command = "setlocal nospell nonumber wrap",
})
if vim.fn.exists("+termguicolors") == 1 then
	vim.api.nvim_create_autocmd({ "TermEnter", "TermOpen" }, {
		group = "filetype_terminal",
		pattern = "*",
		command = "set termguicolors",
	})
end

-- Norg settings
vim.api.nvim_create_augroup("filetype_norg", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_norg",
	pattern = "norg",
	command = "setlocal shiftwidth=2 spell",
})
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_norg",
	pattern = "norg",
	command = "let g:gutentags_enabled = 0",
})

-- Justfile settings
vim.api.nvim_create_augroup("filetype_justfile", { clear = true })
vim.api.nvim_create_autocmd({ "BufNewFile", "BufRead" }, {
	group = "filetype_justfile",
	pattern = "Justfile",
	command = "set filetype=make",
})

-- Markdown settings
vim.api.nvim_create_augroup("filetype_markdown", { clear = true })
vim.api.nvim_create_autocmd({ "BufNewFile", "BufRead" }, {
	group = "filetype_markdown",
	pattern = "qutebrowser-editor*",
	command = "set filetype=markdown",
})
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_markdown",
	pattern = "markdown",
	command = "setlocal tabstop=2 shiftwidth=2 expandtab autoindent spell nowrap conceallevel=1",
})

-- Typescript settings
vim.api.nvim_create_augroup("filetype_typescript", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_typescript",
	pattern = "typescript",
	command = "setlocal tabstop=2 shiftwidth=2 expandtab autoindent spell wrap",
})

-- Ruby settings
vim.api.nvim_create_augroup("filetype_ruby", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_ruby",
	pattern = "ruby",
	command = "setlocal shiftwidth=2 tabstop=2 softtabstop=2 expandtab autoindent",
})

-- RSpec settings
-- TODO: replace test file modifiers as default args for vim-test
-- TODO: replace formatting with conform.nvim config
-- vim.api.nvim_set_keymap('n', '<leader>da', ':!bundle exec rubocop -ADES %:p<CR>', { noremap = true, silent = true })
-- vim.api.nvim_set_keymap('n', '<leader>tq', ':TestLast --fail-fast<CR>', { noremap = true, silent = true })
-- vim.api.nvim_set_keymap('n', '<leader>to', ':TestLast --only-failures<CR>', { noremap = true, silent = true })
-- vim.api.nvim_set_keymap('n', '<leader>tn', ':TestLast -n<CR>', { noremap = true, silent = true })
-- vim.api.nvim_set_keymap('n', '<leader>tv', ':lua _G.vcr_failures_only()<CR>', { noremap = true, silent = true })
-- vim.api.nvim_set_keymap('v', '<Bslash>hl', ':s/\\v:([^ ]*)\\s\\=\\>/\\1:/g<CR>', { noremap = true, silent = true })
-- vim.api.nvim_set_keymap('v', '<Bslash>hr', ':s/\\v(\\w+):/"\\1" =>/g<CR>', { noremap = true, silent = true })
-- vim.api.nvim_set_keymap('v', '<Bslash>hs', ':s/\\v[\\\"\\'](\\w+)[\\\"\\']\\s+\\=\\>\\s+/\\1\\: /g<CR>', { noremap = true, silent = true })
-- vim.api.nvim_set_keymap('v', '<Bslash>hj', ':s/\\v\\"(\\w+)\\":\\s+/"\\1" => /g<CR>', { noremap = true, silent = true })

function _G.vcr_failures_only()
	vim.env.VCR_RECORD = "all"
	vim.cmd("TestLast")
	vim.env.VCR_RECORD = nil
end

-- Python settings
vim.api.nvim_create_augroup("filetype_python", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_python",
	pattern = "python",
	command = "setlocal tabstop=4 shiftwidth=4 expandtab autoindent",
})
vim.api.nvim_set_keymap("n", "<leader>tv", ":TestFile --ff -x<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>tj", ":TestFile --ff<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>tn", ":TestFile --lf -x<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>td", ":TestFile --pdb<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>tlv", ":TestLast --ff -x<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>tlj", ":TestLast --ff<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>tln", ":TestLast --lf -x<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>tld", ":TestLast --pdb<CR>", { noremap = true, silent = true })

-- Lua settings
vim.api.nvim_create_augroup("filetype_lua", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_lua",
	pattern = "lua",
	command = "setlocal colorcolumn=122 tabstop=2 shiftwidth=2 expandtab autoindent nospell",
})
vim.api.nvim_set_keymap("n", "<leader>tj", ":TestFile --no-keep-going<CR>", { noremap = true, silent = true })

-- Git commit settings
vim.api.nvim_create_augroup("filetype_gitcommit", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_gitcommit",
	pattern = "gitcommit",
	command = "setlocal colorcolumn=73 tabstop=2 shiftwidth=2 expandtab autoindent spell wrap",
})

-- Disable folding for git files
vim.api.nvim_create_autocmd("FileType", {
	pattern = "git",
	command = "set nofoldenable",
})

-- Go settings
vim.api.nvim_create_augroup("filetype_go", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_go",
	pattern = "go",
	command = "setlocal tabstop=2 shiftwidth=2 expandtab autoindent nospell",
})
vim.api.nvim_set_keymap("n", "<leader><t-d>", ":lua DebugNearest()<CR>", { noremap = true, silent = true })

-- Rust settings
vim.api.nvim_create_autocmd("FileType", {
	pattern = "rust",
	command = "setlocal makeprg=cargo\\ run colorcolumn=100",
})

-- JavaScript settings
vim.api.nvim_create_augroup("filetype_javascript", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_javascript",
	pattern = "javascript",
	command = "setlocal tabstop=2 shiftwidth=2 expandtab autoindent",
})
vim.api.nvim_create_autocmd({ "BufNewFile", "BufRead" }, {
	group = "filetype_javascript",
	pattern = ".eslintrc",
	command = "set filetype=json",
})

-- Haml settings
vim.api.nvim_create_augroup("filetype_haml", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_haml",
	pattern = "haml",
	command = "setlocal tabstop=2 shiftwidth=2 expandtab autoindent",
})

-- SSH config settings
vim.api.nvim_create_augroup("filetype_sshconfig", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_sshconfig",
	pattern = "sshconfig",
	command = "setlocal tabstop=2 shiftwidth=2 expandtab autoindent",
})

-- JSON settings
vim.api.nvim_create_augroup("filetype_json", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_json",
	pattern = { "json", "jsonc" },
	command = "setlocal tabstop=2 shiftwidth=2 expandtab autoindent",
})

-- YAML settings
vim.api.nvim_create_augroup("filetype_yaml", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_yaml",
	pattern = "yaml",
	command = "setlocal tabstop=2 shiftwidth=2 expandtab autoindent",
})

-- Fish settings
vim.api.nvim_create_augroup("filetype_fish", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_fish",
	pattern = "fish",
	command = "setlocal tabstop=2 shiftwidth=2 expandtab autoindent",
})

-- Perl settings
vim.api.nvim_create_augroup("filetype_perl", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_perl",
	pattern = "perl",
	command = "setlocal tabstop=8 shiftwidth=8 noexpandtab nolist",
})

-- Shell settings
vim.api.nvim_create_augroup("filetype_sh", { clear = true })
vim.api.nvim_create_autocmd({ "BufNewFile", "BufRead" }, {
	group = "filetype_sh",
	pattern = ".alias",
	command = "set filetype=sh",
})
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_sh",
	pattern = "sh",
	command = "setlocal tabstop=2 noexpandtab autoindent nospell",
})

-- Vim settings
vim.api.nvim_create_augroup("filetype_vim", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_vim",
	pattern = "vim",
	command = "setlocal tabstop=2 shiftwidth=2 expandtab autoindent nospell",
})

-- Create parent directories on write
vim.api.nvim_create_augroup("BWCCreateDir", { clear = true })
vim.api.nvim_create_autocmd("BufWritePre", {
	group = "BWCCreateDir",
	pattern = "*",
	callback = function()
		local file = vim.fn.expand("<afile>")
		local buf = vim.fn.expand("<abuf>")
		if vim.fn.empty(vim.fn.getbufvar(buf, "&buftype")) == 1 and not string.match(file, "^%w+:") then
			local dir = vim.fn.fnamemodify(file, ":h")
			if vim.fn.isdirectory(dir) == 0 then
				vim.fn.mkdir(dir, "p")
			end
		end
	end,
})

vim.g["test#strategy"] = "neovim"

-- Set test executable for various languages
vim.g["test#ruby#minitest#executable"] = "bundle exec ruby -Itest/"

vim.g["test#go#gotest#options"] = {
	nearest = "-v",
	file = "-v",
}

vim.g["test#rust#cargotest#options"] = {
	nearest = "-- --nocapture",
}

vim.g["test#python#pytest#options"] = {
	nearest = "-s",
	file = "-s",
}

vim.g["test#ruby#rspec#options"] = {
	nearest = "--format documentation",
	file = "--format documentation",
	suite = "--tag ~slow",
}

vim.g["test#typescript#jest#options"] = {
	nearest = "--verbose -e",
	file = "--verbose",
}

vim.g["test#python#runner"] = "pytest"
vim.g["test#runner_commands"] = { "PyTest", "RSpec", "GoTest", "Minitest", "Jest" }

-- Key mappings for test commands
vim.api.nvim_set_keymap("n", "<leader>tf", ":TestFile<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>tl", ":TestLast<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>ts", ":TestSuite<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>tt", ":TestNearest<CR>", { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<leader>tu", ":TestNearest<CR>", { noremap = true, silent = true })

local function prequire(m)
	local ok, err = pcall(require, m)
	if not ok then
		return nil, err
	end
	return err
end

-- secrets, unversioned local configs, etc.
prequire("local")
-- require("plugins")

-- NOTE: this is the autoloader for lazy.nvim
-- TODO: checksum verification
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
	{
		"gbprod/nord.nvim",
		config = function()
			require("nord").setup({
				transparent = true, -- Enable this to disable setting the background color
				terminal_colors = true,
				diff = { mode = "fg" },
				borders = true, -- Enable the border between verticaly split windows visible
				errors = { mode = "fg" }, -- Display mode for errors and diagnostics
				styles = { comments = { italic = false } },
				search = { theme = "vim" }, -- theme for highlighting search results
				on_highlights = function(highlights, colors)
					highlights["@symbol"] = { fg = colors.aurora.orange }
					highlights["@string.special.symbol"] = highlights["@symbol"]
					highlights["@variable.member"] = { fg = colors.frost.polar_water }
					highlights["@variable.parameter"] = { fg = colors.aurora.purple }
					highlights["@module"] = { fg = colors.frost.ice }
					highlights["@error"] = { sp = colors.aurora.red, undercurl = true }
					highlights["@constant"] = { fg = colors.aurora.purple }
					highlights["@text.uri"] = { underline = true }
					highlights["@error"] = { undercurl = true }
					highlights["@spell.bad"] = { undercurl = true }

					return highlights
				end,
			})
			vim.api.nvim_command("colorscheme nord")
		end,
	},
	{
		"giuxtaposition/blink-cmp-copilot",
	},
	{
		"saghen/blink.cmp",
		-- optional: provides snippets for the snippet source
		dependencies = { "rafamadriz/friendly-snippets" },
		-- use a release tag to download pre-built binaries
		version = "*",
		-- AND/OR build from source, requires nightly: https://rust-lang.github.io/rustup/concepts/channels.html#working-with-nightly-rust
		-- build = 'cargo build --release',
		-- If you use nix, you can build from source using latest nightly rust with:
		-- build = 'nix run .#build-plugin',

		---@module 'blink.cmp'
		---@type blink.cmp.Config
		opts = {
			-- Experimental signature help support
			signature = {
				-- enabled = true,
			},
			completion = {
				documentation = {
					auto_show = true,
					auto_show_delay_ms = 500,
				},
				list = {
					selection = "auto_insert",
				},
				trigger = {
					show_on_keyword = true,
					show_on_trigger_character = true,
				},
				menu = {
					draw = {
						columns = {
							{ "kind_icon", gap = 3 },
							{ "label", "label_description", gap = 2 },
						},
					},
				},
			},
			-- 'default' for mappings similar to built-in completion
			-- 'super-tab' for mappings similar to vscode (tab to accept, arrow keys to navigate)
			-- 'enter' for mappings similar to 'super-tab' but with 'enter' to accept
			-- See the full "keymap" documentation for information on defining your own keymap.
			keymap = {
				preset = "enter",
			},
			appearance = {
				-- Sets the fallback highlight groups to nvim-cmp's highlight groups
				-- Useful for when your theme doesn't support blink.cmp
				-- Will be removed in a future release
				use_nvim_cmp_as_default = true,
				-- Set to 'mono' for 'Nerd Font Mono' or 'normal' for 'Nerd Font'
				-- Adjusts spacing to ensure icons are aligned
				nerd_font_variant = "mono",
			},

			-- Default list of enabled providers defined so that you can extend it
			-- elsewhere in your config, without redefining it, due to `opts_extend`
			sources = {
				default = { "lazydev", "lsp", "path", "snippets", "buffer" },
				providers = {
					lazydev = {
						name = "LazyDev",
						module = "lazydev.integrations.blink",
						-- make lazydev completions top priority (see `:h blink.cmp`)
						score_offset = 100,
					},
				},
			},
		},
		opts_extend = { "sources.default" },
	},
	{ "nvim-tree/nvim-web-devicons", lazy = true },
	{
		"numToStr/Comment.nvim",
		config = function()
			require("Comment").setup()
		end,
	},
	{
		"Wansmer/treesj",
		dependencies = "nvim-treesitter/nvim-treesitter",
		config = function()
			require("treesj").setup({
				use_default_keymaps = false,
			})
			vim.keymap.set("n", "gJ", require("treesj").join)
			vim.keymap.set("n", "gS", require("treesj").split)
		end,
	},
	{
		"esensar/nvim-dev-container",
		dependencies = "nvim-treesitter/nvim-treesitter",
		config = function()
			require("devcontainerconfig")
		end,
	},
	{
		"nvim-lualine/lualine.nvim",
		dependencies = {
			"nvim-tree/nvim-web-devicons",
		},
		config = function()
			require("lualine").setup({
				options = {
					icons_enabled = true,
					theme = "nord",
					component_separators = { left = "", right = "" },
					section_separators = { left = "", right = "" },
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
					},
				},
				sections = {
					lualine_a = { "mode" },
					lualine_b = { "branch", "diff" },
					lualine_c = {
						{ "filetype", jcon_only = true },
						{ "filename", path = 1 },
					},
					lualine_x = {
						{ "diagnostics", sources = { "nvim_lsp" } },
					},
					lualine_y = {},
					lualine_z = {},
				},
				inactive_sections = {
					lualine_a = {},
					lualine_b = { "branch", "diff" },
					lualine_c = {
						{ "filetype", jcon_only = true },
						{ "filename", path = 1 },
					},
					lualine_x = {},
					lualine_y = {},
					lualine_z = {},
				},
			})
		end,
	},
	{
		"ibhagwan/fzf-lua",
		config = function()
			require("fzfconfig")
		end,
		branch = "main",
		dependencies = { "vijaymarupudi/nvim-fzf", "nvim-tree/nvim-web-devicons" },
	},
	{
		"folke/noice.nvim",
		branch = "main",
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
						conceal = false,
					},
				},
				lsp = {
					override = {
						["vim.lsp.util.convert_input_to_markdown_lines"] = true,
						["vim.lsp.util.stylize_markdown"] = true,
						["cmp.entry.get_documentation"] = true,
					},
				},
				notify = {
					enabled = true,
					timeout_ms = 1000,
				},
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
		dependencies = { "MunifTanjim/nui.nvim", "rcarriga/nvim-notify", "neovim/nvim-lspconfig" },
	},
	{
		"glepnir/lspsaga.nvim",
		branch = "main",
		dependencies = { "neovim/nvim-lspconfig" },
		config = function()
			require("lspsagaconfig")
		end,
	},
	{ "norcalli/nvim-colorizer.lua", requires = "nvim-treesitter/nvim-treesitter" },
	{
		"mrcjkb/rustaceanvim",
		version = "^5", -- Recommended
		lazy = false, -- This plugin is already lazy
	},
	{
		"neovim/nvim-lspconfig",
		dependencies = {
			-- "hrsh7th/cmp-buffer",
			-- "hrsh7th/cmp-path",
			-- "hrsh7th/cmp-cmdline",
			-- "hrsh7th/nvim-cmp",
			-- "hrsh7th/cmp-emoji",
			-- "Gelio/cmp-natdat",
			-- "hrsh7th/cmp-nvim-lsp",
			-- "hrsh7th/cmp-vsnip",
			-- "andersevenrud/cmp-tmux",
			-- "hrsh7th/vim-vsnip",
			"saghen/blink.cmp",
			"nvim-tree/nvim-web-devicons",
			"onsails/lspkind.nvim",
		},
		opts = {
			servers = {
				lua_ls = {},
				ts_ls = {
					settings = {
						completions = {
							completeFunctionCalls = true,
						},
					},
				},
				gopls = {},
				ruby_lsp = {},
				jsonls = {},
				marksman = {},
				pylsp = {},
				html = {},
				bashls = {
					filetypes = { "sh", "zsh", "bash" },
				},
			},
			opts = {
				inlay_hints = { enabled = true },
			},
		},
		config = function(_, opts)
			require("lsp")
			local lspconfig = require("lspconfig")
			for server, config in pairs(opts.servers) do
				-- passing config.capabilities to blink.cmp merges with the capabilities in your
				-- `opts[server].capabilities, if you've defined it
				config.capabilities = require("blink.cmp").get_lsp_capabilities(config.capabilities)
				lspconfig[server].setup(config)
			end
		end,
	},
	{
		"nvim-treesitter/nvim-treesitter",
		config = function()
			require("treesitter")
		end,
	},
	{
		"nvim-treesitter/nvim-treesitter-textobjects",
		dependencies = { "nvim-treesitter/nvim-treesitter" },
	},
	{
		"nvim-treesitter/playground",
		dependencies = { "nvim-treesitter/nvim-treesitter" },
	},
	{
		"ibhagwan/smartyank.nvim",
		config = function()
			require("smartyank").setup({
				highlight = {
					enabled = true, -- highlight yanked text
					higroup = "IncSearch", -- highlight group of yanked text
					timeout = 2000, -- timeout for clearing the highlight
				},
				tmux = {
					enabled = true,
					cmd = { "tmux", "set-buffer", "-w" },
				},
				clipboard = { enabled = true },
				osc52 = {
					enabled = true,
					ssh_only = true, -- OSC52 yank also in local sessions
					silent = true, -- false to disable the "n chars copied" echo
				},
			})
		end,
	},
	{
		"lukas-reineke/indent-blankline.nvim",
		dependencies = "nvim-treesitter/nvim-treesitter",
		config = function()
			require("ibl").setup({})
		end,
	},
	{
		"christoomey/vim-tmux-navigator",
		init = function()
			vim.g.tmux_navigator_no_mappings = 1
			vim.g.tmux_navigator_save_on_switch = 1
		end,
		config = function()
			vim.api.nvim_set_keymap("n", "<C-h>", ":TmuxNavigateLeft<cr>", { noremap = true, silent = true })
			vim.api.nvim_set_keymap("n", "<C-j>", ":TmuxNavigateDown<cr>", { noremap = true, silent = true })
			vim.api.nvim_set_keymap("n", "<C-k>", ":TmuxNavigateUp<cr>", { noremap = true, silent = true })
			vim.api.nvim_set_keymap("n", "<C-l>", ":TmuxNavigateRight<cr>", { noremap = true, silent = true })
		end,
	},
	{
		"lanej/vim-prosession",
		dependencies = "tpope/vim-obsession",
		init = function()
			vim.g.prosession_per_branch = 1
			vim.g.prosession_tmux_title = 1
			vim.g.prosession_tmux_title_format = "@@@"
		end,
	},
	{
		"RRethy/vim-illuminate",
		config = function()
			require("illuminate").configure({
				under_cursor = false,
			})
		end,
	},
	{
		"NeogitOrg/neogit",
		dependencies = {
			"nvim-lua/plenary.nvim", -- required
			"sindrets/diffview.nvim", -- optional - Diff integration

			-- Only one of these is needed.
			"ibhagwan/fzf-lua", -- optional
			-- "echasnovski/mini.pick", -- optional
		},
		config = function()
			require("neogit").setup({
				disable_commit_confirmation = true,
				disable_signs = false,
				disable_context_highlighting = false,
				disable_insert_on_commit = false,
				signs = {
					section = { "", "" },
					item = { "", "" },
					hunk = { "", "" },
				},
				integrations = {
					diffview = true,
					fzf_lua = true,
				},
				mappings = {
					status = {
						["q"] = "Close",
					},
				},
			})
			vim.keymap.set({ "n", "v" }, "<leader>gv", function()
				vim.cmd("Neogit commit -v")
			end, { silent = true, noremap = true })
		end,
	},
	{
		"sindrets/diffview.nvim",
		config = function()
			require("diffview").setup({
				keymaps = {
					file_panel = {
						{
							"n",
							"gm",
							function()
								vim.ui.input({ prompt = "Commit message: " }, function(msg)
									if not msg then
										return
									end
									local results = vim.system({ "git", "commit", "-m", msg }, { text = true }):wait()

									if results.code ~= 0 then
										vim.notify(
											"Commit failed with the message: \n"
												.. vim.trim(results.stdout .. "\n" .. results.stderr),
											vim.log.levels.ERROR,
											{ title = "Commit" }
										)
									else
										vim.notify(results.stdout, vim.log.levels.INFO, { title = "Commit Message:%" })
									end
								end)
							end,
						},
					},
				},
			})

			vim.keymap.set("n", "<leader>gs", ":DiffviewOpen<CR>", { silent = true, noremap = true })
			vim.keymap.set("n", "<leader>gS", ":DiffviewClose<CR>", { silent = true, noremap = true })
			vim.keymap.set("n", "<leader>gd", ":DiffviewOpen origin/master<CR>", { silent = true, noremap = true })
			vim.keymap.set("n", "<leader>fh", ":DiffviewFileHistory %<CR>", { silent = true, noremap = true })
			vim.keymap.set("v", "<leader>gh", ":DiffviewFileHistory<CR>", { silent = true, noremap = true })

			-- use an autocmd to set the keymap only when the buffer is a diffview buffer
			-- vim.keymap.set("n", "<leader>hs", ":diffput",
			--   { buffer = 0, expr = "bufname(bufnr('')):match('^diffview://') ~= nil", silent = true })
			vim.api.nvim_create_autocmd({ "BufEnter", "BufRead", "BufWinEnter" }, {
				pattern = "diffview://*",
				callback = function()
					vim.keymap.set("n", "<leader>hs", ":diffput<CR>", { buffer = 0, silent = true })
					vim.keymap.set("n", "<leader>hr", ":diffget<CR>", { buffer = 0, silent = true })
				end,
			})
		end,
	},
	{
		"mbbill/undotree",
		config = function()
			vim.keymap.set("n", "<leader>fu", ":UndotreeToggle<CR>", { silent = true, noremap = true })
		end,
	},
	{
		"nvim-treesitter/playground",
		dependencies = "nvim-treesitter/nvim-treesitter",
	},
	{
		"phaazon/hop.nvim",
		config = function()
			require("hopconfig")
		end,
	},
	"tpope/vim-dotenv",
	{
		"tpope/vim-fugitive",
		config = function()
			vim.keymap.set("n", "<leader>go", ":GBrowse!<CR>", { silent = true, noremap = true })
			vim.keymap.set("v", "<leader>go", ":GBrowse!<CR>", { silent = true, noremap = true })
			vim.keymap.set("n", "<leader>gr", ":Gread<CR>", { silent = true, noremap = true })
			vim.keymap.set("n", "<leader>gb", ":Git blame<CR>", { silent = true, noremap = true })
			vim.keymap.set("n", "<leader>gp", ":Git push<CR>", { silent = true, noremap = true })
			vim.keymap.set("n", "<leader>gt", ":Git commit -am'wip'<CR>", { silent = true, noremap = true })
			vim.keymap.set("n", "<leader>gu", ":Git add -u<CR>", { silent = true, noremap = true })
		end,
	},
	"tpope/vim-eunuch",
	{
		"kylechui/nvim-surround",
		version = "*", -- Use for stability; omit to use `main` branch for the latest features
		event = "VeryLazy",
		config = true,
	},
	"tpope/vim-rhubarb",
	"tpope/vim-repeat",
	{ "norcalli/nvim-colorizer.lua", dependencies = "nvim-treesitter/nvim-treesitter" },
	{
		"JMarkin/gentags.lua",
		cond = vim.fn.executable("ctags") == 1,
		dependencies = { "nvim-lua/plenary.nvim" },
		config = function()
			require("gentags").setup({})
		end,
		event = "VeryLazy",
	},
	"vim-test/vim-test",
	"junegunn/vim-easy-align",
	{
		"lewis6991/gitsigns.nvim",
		dependencies = { "nvim-lua/plenary.nvim" },
		tag = "release",
		config = function()
			require("gitsignsconfig")
		end,
	},
	{
		"nvim-tree/nvim-tree.lua",
		dependencies = "nvim-tree/nvim-web-devicons",
		config = function()
			require("nvim-tree-config")
		end,
	},
	{
		"subnut/nvim-ghost.nvim",
		cond = vim.env.SSH_TTY == nil,
		event = "VeryLazy",
		init = function()
			vim.g.nvim_ghost_autostart = 1

			-- SEE: https://github.com/subnut/nvim-ghost.nvim/issues/38
			vim.g.nvim_ghost_super_quiet = 1
		end,
	},
	{
		"folke/todo-comments.nvim",
		config = function()
			require("todo-comments").setup({
				keywords = {
					WTF = { icon = "🤨", color = "warning", alt = { "DAFUQ", "GAH" } },
					SEE = { icon = "👀", color = "info", alt = { "REF" } },
				},
			})
		end,
	},
	{
		"smjonas/inc-rename.nvim",
		config = function()
			require("inc_rename").setup({})
			vim.keymap.set("n", "<leader>ri", ":IncRename ")
		end,
	},
	-- {
	-- 	"nvim-neotest/neotest",
	-- 	cond = false, -- This can cause neovim to lockup on boot
	-- 	dependencies = {
	-- 		"nvim-neotest/nvim-nio",
	-- 		"nvim-lua/plenary.nvim",
	-- 		"antoinemadec/FixCursorHold.nvim",
	-- 		"nvim-treesitter/nvim-treesitter",
	-- 		"nvim-neotest/neotest-jest",
	-- 	},
	-- 	config = function()
	-- 		require("neotest").setup({
	-- 			adapters = {
	-- 				require("neotest-jest")({
	-- 					jestCommand = require("neotest-jest.jest-util").getJestCommand(vim.fn.expand("%:p:h"))
	-- 						.. " --watch",
	-- 					-- jestConfigFile = "custom.jest.config.ts",
	-- 					-- env = { CI = true },
	-- 					cwd = function(path)
	-- 						return vim.fn.getcwd()
	-- 					end,
	-- 				}),
	-- 			},
	-- 		})
	--
	-- 		vim.keymap.set("n", "<leader>tw", require("neotest").watch.watch, { silent = true, noremap = true })
	-- 		vim.keymap.set("n", "<leader>tr", require("neotest").run.run, { silent = true, noremap = true })
	-- 		vim.keymap.set("n", "<leader>ta", require("neotest").run.attach, { silent = true, noremap = true })
	-- 		vim.keymap.set("n", "]t", require("neotest").jump.next, { silent = true, noremap = true })
	-- 		vim.keymap.set("n", "[t", require("neotest").jump.prev, { silent = true, noremap = true })
	-- 	end,
	-- },
	{
		"zbirenbaum/copilot.lua",
		cmd = "Copilot",
		event = "InsertEnter",
		config = function()
			require("copilot").setup({
				suggestion = { enabled = false },
				panel = { enabled = false },
				-- copilot_node_command = vim.fn.expand("$HOME") .. "/.config/nvm/versions/node/v18.18.2/bin/node", -- Node.js version must be > 18.x
			})
		end,
	},
	{
		"CopilotC-Nvim/CopilotChat.nvim",
		event = "VeryLazy",
		build = "make tiktoken", -- Only on MacOS or Linux
		branch = "main",
		dependencies = {
			{ "zbirenbaum/copilot.lua" }, -- or github/copilot.vim
			{ "nvim-lua/plenary.nvim" }, -- for curl, log wrapper
		},
		opts = {
			debug = true, -- Enable debugging
		},
		config = function()
			vim.keymap.set({ "n", "v" }, "<leader>co", ":CopilotChat<cr>", { silent = true, noremap = true })
			require("CopilotChat").setup({
				window = {
					layout = "float",
				},
				auto_insert_mode = true,
				title = "athena",
				prompts = {
					Commit = {
						prompt = "Write a commit message for the change with commitizen convention. Make sure the title has maximum 50 characters and message is wrapped at 72 characters. Wrap the whole message in code block with language gitcommit.  Keep the message concise and clear.",
						mapping = "<leader>ccc",
					},
					Fix = {
						-- prompt =
						-- 'Fix the following code. Only output the result in format ```$filetype\n...\n```:\n```$filetype\n$text\n```',
						mapping = "<leader>ccf",
					},
					CommitStaged = {
						prompt = "Write a commit message for the change with commitizen convention. Make sure the title has maximum 50 characters and message is wrapped at 72 characters. Wrap the whole message in code block with language gitcommit.  Make the message very concise.  Make sure the message does not exceed 128 characters. Make sure the message is terse and clear.  Make sure the message is written in active tense.  Make sure the message starts with a verb in the present tense",
						mapping = "<leader>ccs",
					},
					Docs = {
						mapping = "<leader>ccd",
					},
					-- FixDiagnostic = {
					--   mapping = "<leader>ccx"
					-- },
				},
				mappings = {
					complete = {
						insert = "",
					},
					reset = {
						normal = "<C-p>",
						insert = "<C-p>",
					},
				},
			})
		end,
	},
	{ "github/copilot.vim" },
	{
		"iamcco/markdown-preview.nvim",
		cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
		ft = { "markdown" },
		build = function()
			vim.fn["mkdp#util#install"]()
		end,
	},
	{
		"pwntester/octo.nvim",
		requires = {
			"nvim-lua/plenary.nvim",
			"ibhagwan/fzf-lua",
			"nvim-tree/nvim-web-devicons",
		},
		config = function()
			require("octo").setup({
				picker = "fzf-lua",
			})
		end,
	},
	{
		"OXY2DEV/markview.nvim",
		lazy = true, -- Recommended
		ft = "markdown", -- If you decide to lazy-load anyway
		dependencies = {
			-- You will not need this if you installed the
			-- parsers manually
			-- Or if the parsers are in your $RUNTIMEPATH
			"nvim-treesitter/nvim-treesitter",

			"nvim-tree/nvim-web-devicons",
		},
		opts = {
			headings = {
				shift_width = 0,
			},
			list_items = {
				shift_width = 1,
				indent_size = 1,
			},
		},
	},
	{
		"stevearc/conform.nvim",
		config = function()
			require("conform").setup({
				formatters_by_ft = {
					lua = { "stylua" },
					-- Conform will run multiple formatters sequentially
					python = { "isort", "black" },
					-- You can customize some of the format options for the filetype (:help conform.format)
					rust = { "rustfmt", lsp_format = "fallback" },
					sh = { "shfmt" },
					-- Conform will run the first available formatter
					javascript = { "prettierd", "prettier", stop_after_first = true },
					typescript = { "prettierd", "prettier", stop_after_first = true },
				},
			})
			vim.keymap.set("n", "<leader>bf", function()
				require("conform").format({ timeout_ms = 500, lsp_format = "fallback" })
			end, {
				noremap = false,
				silent = true,
			})
			vim.api.nvim_create_autocmd("BufWritePre", {
				pattern = { "*.ts", "*.rs", "*.py", "*.lua", "*.js" },
				callback = function()
					require("conform").format({ timeout_ms = 500, lsp_format = "fallback" })
				end,
			})
		end,
	},
	{
		-- use oil.nvim for mass file / directory editing
		"stevearc/oil.nvim",
		---@module 'oil'
		---@type oil.SetupOpts
		opts = {},
		-- Optional dependencies
		dependencies = {
			{ "echasnovski/mini.icons", opts = {} },
			"nvim-lua/plenary.nvim",
			"nvim-tree/nvim-web-devicons",
		},
		-- dependencies = { "nvim-tree/nvim-web-devicons" }, -- use if prefer nvim-web-devicons
		config = function()
			require("oil").setup({
				float = {
					border = "rounded",
					winblend = 10,
					padding = 5,
					highlights = {
						border = "Normal",
						background = "Normal",
					},
				},
			})
			vim.keymap.set("n", "<leader>wo", require("oil").open_float, { desc = "Open parent directory" })
		end,
		opts_extend = { "sources.default" },
	},
	{
		"folke/lazydev.nvim",
		ft = "lua", -- only load on lua files
		opts = {
			library = {
				-- See the configuration section for more details
				-- Load luvit types when the `vim.uv` word is found
				{ path = "${3rd}/luv/library", words = { "vim%.uv" } },
			},
		},
	},
})

vim.keymap.set("n", "<leader>vpu", ":Lazy update<CR>", { silent = true, noremap = true })
vim.keymap.set("n", "<leader>vpi", ":Lazy home<CR>", { silent = true, noremap = true })
vim.keymap.set("n", "<leader>vpc", ":Lazy clean<CR>", { silent = true, noremap = true })

vim.cmd([[set secure]])
