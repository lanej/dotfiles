---@diagnostic disable: missing-fields
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

-- Set minimum window sizes early to allow session restoration and focus.nvim
vim.opt.winminheight = 1
vim.opt.winminwidth = 1

-- equalalways: conditionally set based on focus.nvim availability
vim.api.nvim_create_autocmd("VimEnter", {
	callback = function()
		local has_focus = pcall(require, "focus")
		if has_focus then
			vim.opt.equalalways = false
		else
			vim.opt.equalalways = true
		end
	end,
})

-- Highlight active window by dimming inactive ones
vim.api.nvim_create_autocmd({ "WinEnter", "BufWinEnter" }, {
	callback = function()
		vim.wo.winhighlight = ""
	end,
})

vim.api.nvim_create_autocmd("WinLeave", {
	callback = function()
		vim.wo.winhighlight = "Normal:NormalNC,NormalFloat:NormalNC"
	end,
})

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
vim.opt.listchars = { tab = "⇛ ", nbsp = "␣", trail = "•", precedes = "«", extends = "»" }
vim.cmd("set cedit=<C-v>")

vim.g.mapleader = ","

vim.opt.inccommand = "nosplit" -- live replace
vim.opt.termguicolors = true

-- searching stuff
vim.keymap.set("n", "<C-\\>", ":nohls<CR>", { noremap = true, silent = true })
vim.keymap.set("i", "<C-\\>", "<C-O>:nohls<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "*", "*``", { noremap = true, silent = true })

-- Edit the vimrc file
vim.keymap.set("n", "ev", ":e $MYVIMRC<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "evr", ":source $MYVIMRC<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "tt", ":tablast<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "te", ":tabedit<Space>", { noremap = true, silent = true })
vim.keymap.set("n", "tn", ":tabnext<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "tp", ":tabprev<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "tc", ":tabnew<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "tm", ":tabm<Space>", { noremap = true, silent = true })
vim.keymap.set("n", "tx", ":tabclose<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "t1", "1gt<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "t2", "2gt<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "t3", "3gt<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "t4", "4gt<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "t5", "5gt<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "t6", "6gt<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "fbk", ":bd!<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "fak", ":%bd!|e#<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bo", ":bp<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bi", ":bn<CR>", { noremap = true, silent = true })

-- Enable filetype plugins to handle indents
vim.cmd("filetype plugin indent on")

-- plugin-config start
vim.keymap.set("n", "<leader>w", ":w<CR>", { noremap = true, silent = true })
-- vim.keymap.set('n', '<leader>w!', ':SudoWrite<CR>', { noremap = true, silent = true })
vim.keymap.set({ "n", "i", "v" }, "<leader>x", ":x<CR>", { noremap = true, silent = true })

-- replace current word
vim.keymap.set("n", "<leader>rw", ":%s/<C-r><C-w>//gc<left><left><left>", { noremap = true })
vim.keymap.set("v", "<leader>rw", ":s/<C-r><C-w>//gc<left><left><left>", { noremap = true })

-- legacy support for the muscle memory
vim.keymap.set("n", "<leader>rb", ":%s/<C-r><C-w>//gc<left><left><left>", { noremap = true })
vim.keymap.set("v", "<leader>rb", ":s/<C-r><C-w>//gc<left><left><left>", { noremap = true })

-- replace current selection
vim.keymap.set("n", "<leader>rs", '"hy:%s/<C-r>h//gc<left><left><left>', { noremap = true })
vim.keymap.set("v", "<leader>rs", '""hy:s/<C-r>h//gc<left><left><left>', { noremap = true })

-- replace current word in all quicklist files
vim.keymap.set("n", "<leader>rq", ":%cfdo s/<C-r><C-w>/", { noremap = true })
vim.keymap.set("v", "<leader>rq", ":cfdo s/<C-r><C-w>/", { noremap = true })

-- quickfix nav
vim.keymap.set("n", "]q", ":cnext<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "[q", ":cprev<CR>", { noremap = true, silent = true })

-- NOTE: Map <leader>y to yank to system clipboard in normal and visual modes
vim.keymap.set({ "n", "v" }, "<leader>y", '"+y', { noremap = true, silent = true })

-- NOTE: Map <leader>yy to yank the current line to system clipboard in normal mode
vim.keymap.set("n", "<leader>yy", '"+yy', { noremap = true, silent = true })

-- NOTE: Map <leader>Y to yank to the end of the line to system clipboard in normal mode
vim.keymap.set("n", "<leader>Y", '"+yg_', { noremap = true, silent = true })

-- NOTE: Map <leader>p to paste from system clipboard in normal and visual modes
vim.keymap.set({ "n", "v" }, "<leader>p", '"+p', { noremap = true, silent = true })

-- NOTE: Map <leader>P to paste before cursor from system clipboard in normal and visual modes
vim.keymap.set({ "n", "v" }, "<leader>P", '"+P', { noremap = true, silent = true })

-- Set leader key
vim.g.mapleader = ","

-- NvimTree mappings
vim.keymap.set("n", "<leader>ntt", ":NvimTreeToggle<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "<leader>ntc", ":NvimTreeClose<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "<leader>ntf", ":NvimTreeFindFile<CR>", { noremap = true, silent = true })

-- Rename mapping
vim.keymap.set("n", "<leader>re", ":Rename ", { noremap = true })

-- Terminal mode escape
vim.keymap.set("t", "<C-o>", "<C-\\><C-n>", { noremap = true })

-- Yank current file path (full absolute path to clipboard)
vim.keymap.set("n", "yd", ':let @+ = expand("%:p")<CR>', { noremap = true })

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
vim.keymap.set("n", "<leader>cd", ":cd %:p:h<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "<leader>cg", ":Gcd<CR>", { noremap = true, silent = true })

-- Disable Ex mode
vim.keymap.set("n", "Q", "<Nop>", { noremap = true })

-- Helpers
vim.keymap.set({ "v" }, "<leader>srt", ":!sort<CR>", { noremap = true, silent = true })
vim.keymap.set({ "v" }, "<leader>uq", ":!uniq<CR>", { noremap = true, silent = true })

-- Wrapped lines navigation
vim.keymap.set("n", "j", "gj", { noremap = true })
vim.keymap.set("n", "k", "gk", { noremap = true })

-- Command aliases
vim.api.nvim_create_user_command("Q", "q", {})
vim.api.nvim_create_user_command("Qa", "qa", {})
vim.api.nvim_create_user_command("W", "w", {})
vim.api.nvim_create_user_command("Wa", "wa", {})
vim.api.nvim_create_user_command("Wqa", "wqa", {})
vim.api.nvim_create_user_command("Qwa", "wqa", {})
vim.api.nvim_create_user_command("E", "e", {})

-- Command-line abbreviations for common typos with bang
vim.cmd("cnoreabbrev E! e!")
vim.cmd("cnoreabbrev W! w!")
vim.cmd("cnoreabbrev Q! q!")
vim.cmd("cnoreabbrev Wq wq")
vim.cmd("cnoreabbrev WQ wq")
vim.cmd("cnoreabbrev Wq! wq!")
vim.cmd("cnoreabbrev WQ! wq!")

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

-- Realign the whole file
vim.keymap.set("n", "<leader>D", "ggVG=<CR>", { noremap = true, silent = true })

-- Clang format style options
vim.g.clang_format_style_options = {
	AccessModifierOffset = -4,
	AllowShortIfStatementsOnASingleLine = "true",
	AlwaysBreakTemplateDeclarations = "true",
	Standard = "C++11",
}

-- Set make program
vim.opt.makeprg = "make -j9"
vim.keymap.set("n", "<Leader>m", ":make!<CR>", { noremap = true, silent = true })

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
vim.keymap.set("n", "<space>th", ":TSHighlightCapturesUnderCursor<CR>", { noremap = true, silent = true })

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

vim.keymap.set("n", "<leader>se", ":lua SourceEnv()<CR>", { noremap = true, silent = true })

-- Print environment variables
function _G.Env()
	local evars = vim.fn.environ()
	for _, var in ipairs(vim.fn.sort(vim.tbl_keys(evars))) do
		print(var .. "=" .. evars[var])
	end
end

vim.keymap.set("n", "<leader>ee", ":e .env<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "<leader>eo", ":e .env-override<CR>", { noremap = true, silent = true })

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
	command = "setlocal tabstop=2 shiftwidth=2 expandtab autoindent spell conceallevel=0",
})

-- Treat .jsonl files as JSON (JSON Lines format)
vim.filetype.add({
	extension = {
		jsonl = "json",
	},
})

vim.api.nvim_create_augroup("filetype_typespec", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_typespec",
	pattern = "typespec",
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

vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_ruby",
	pattern = "ruby",
	callback = function()
		vim.keymap.set("n", "<leader>tn", ":TestLast -n<CR>", { noremap = true, silent = true, buffer = true })
		vim.keymap.set("n", "<leader>tq", ":TestLast --fail-fast<CR>", { noremap = true, silent = true, buffer = true })
		vim.keymap.set(
			"n",
			"<leader>to",
			":TestLast --only-failures<CR>",
			{ noremap = true, silent = true, buffer = true }
		)
		vim.keymap.set("n", "<leader>tv", function()
			vim.env.VCR_RECORD = "all"
			vim.cmd("TestLast")
			vim.env.VCR_RECORD = nil
		end, { noremap = true, silent = true, buffer = true })
	end,
})

-- RSpec settings
-- TODO: replace formatting with conform.nvim config
-- vim.keymap.set('n', '<leader>da', ':!bundle exec rubocop -ADES %:p<CR>', { noremap = true, silent = true })
-- vim.keymap.set('v', '<Bslash>hl', ':s/\\v:([^ ]*)\\s\\=\\>/\\1:/g<CR>', { noremap = true, silent = true })
-- vim.keymap.set('v', '<Bslash>hr', ':s/\\v(\\w+):/"\\1" =>/g<CR>', { noremap = true, silent = true })
-- vim.keymap.set('v', '<Bslash>hs', ':s/\\v[\\\"\\'](\\w+)[\\\"\\']\\s+\\=\\>\\s+/\\1\\: /g<CR>', { noremap = true, silent = true })
-- vim.keymap.set('v', '<Bslash>hj', ':s/\\v\\"(\\w+)\\":\\s+/"\\1" => /g<CR>', { noremap = true, silent = true })

-- Python settings
vim.api.nvim_create_augroup("filetype_python", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_python",
	pattern = "python",
	command = "setlocal tabstop=4 shiftwidth=4 expandtab autoindent",
})

-- Lua settings
vim.api.nvim_create_augroup("filetype_lua", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_lua",
	pattern = "lua",
	command = "setlocal colorcolumn=122 tabstop=2 shiftwidth=2 expandtab autoindent nospell",
})
vim.keymap.set("n", "<leader>tj", ":TestFile --no-keep-going<CR>", { noremap = true, silent = true })

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
vim.keymap.set("n", "<leader><t-d>", ":lua DebugNearest()<CR>", { noremap = true, silent = true })

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

vim.api.nvim_create_autocmd({ "BufNewFile", "BufRead" }, {
	group = "filetype_javascript",
	pattern = ".jsonl",
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

-- Typst settings
vim.api.nvim_create_augroup("filetype_typst", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
	group = "filetype_typst",
	pattern = "typst",
	command = "setlocal tabstop=2 shiftwidth=2 expandtab autoindent spell wrap linebreak",
})
vim.api.nvim_create_autocmd({ "BufNewFile", "BufRead" }, {
	group = "filetype_typst",
	pattern = "*.typ",
	command = "set filetype=typst",
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

--- Attempts to require a module and returns nil and the error message if it fails.
-- @param m The name of the module to require.
-- @return The module if it was successfully required, or nil and the error message if it failed.
local function prequire(m)
	local ok, err = pcall(require, m)
	if not ok then
		return nil, err
	end
	return err
end

--- Set neovide configuration
if vim.g.neovide then
	vim.g.neovide_transparency = 0.8
	vim.g.neovide_cursor_antialiasing = true
	vim.g.neovide_cursor_vfx_mode = "railgun"
	vim.g.neovide_show_border = false
end

-- secrets, unversioned local configs, etc.
prequire("local")

---@diagnostic disable: missing-fields
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
		"lanej/hotreload.nvim",
		opts = {
			-- Uses fs_event watchers by default (no polling)
			silent = true,
		},
	},
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
		"lanej/vim-phabricator",
		dependencies = {
			"tpope/vim-fugitive",
		},
		enabled = function()
			return vim.fn.filereadable(vim.fn.expand("~/.arcrc")) == 1
		end,
		config = function()
			-- Read the arcrc file, parse the json into a lua table
			local arcrc = vim.fn.json_decode(vim.fn.readfile(vim.fn.expand("~/.arcrc")))
			-- The base url is the config.default value
			vim.g.phabricator_hosts = { arcrc.config.default }
			-- The Token is is in the hosts table, with a key of the base url + "/api/"
			vim.g.phabricator_api_token = arcrc.hosts[arcrc.config.default .. "/api/"].token
		end,
	},
	{
		"rachartier/tiny-inline-diagnostic.nvim",
		event = "VeryLazy", -- Or `LspAttach`
		priority = 1000, -- needs to be loaded in first
		opts = { preset = "powerline" },
		config = function(opts)
			require("tiny-inline-diagnostic").setup(opts)
			vim.diagnostic.config({ virtual_text = false })
		end,
	},
	{
		"saghen/blink.cmp",
		-- optional: provides snippets for the snippet source
		dependencies = {
			"rafamadriz/friendly-snippets",
			"xzbdmw/colorful-menu.nvim",
			"mikavilpas/blink-ripgrep.nvim",
			{
				"Kaiser-Yang/blink-cmp-dictionary",
				dependencies = { "nvim-lua/plenary.nvim" },
			},
			{
				"moyiz/blink-emoji.nvim",
			},
		},
		-- use a release tag to download pre-built binaries
		version = "*",
		-- AND/OR build from source, requires nightly: https://rust-lang.github.io/rustup/concepts/channels.html#working-with-nightly-rust
		-- build = 'cargo build --release',
		-- If you use nix, you can build from source using latest nightly rust with:
		-- build = 'nix run .#build-plugin',
		config = function()
			---@module 'blink.cmp'
			---@type blink.cmp.Config
			require("blink.cmp").setup({
				-- Experimental signature help support
				signature = {
					enabled = true,
					window = {
						border = "rounded",
					},
				},
				completion = {
					documentation = {
						auto_show = true,
						auto_show_delay_ms = 100,
						update_delay_ms = 100,
						window = {
							max_width = math.min(64, vim.o.columns),
							border = "rounded",
						},
					},
					list = {
						selection = {
							preselect = false,
							auto_insert = true,
						},
					},
					keyword = {
						range = "full",
					},
					accept = {
						auto_brackets = {
							enabled = true,
							override_brackets_for_filetypes = {
								tex = { "{", "}" },
							},
						},
					},
					menu = {
						draw = {
							treesitter = {
								"lsp",
							},
							columns = { { "kind_icon" }, { "label", gap = 1 } },
							components = {
								label = {
									text = require("colorful-menu").blink_components_text,
									highlight = require("colorful-menu").blink_components_highlight,
								},
								source = {
									text = function(ctx)
										local map = {
											["lazydev"] = "[💤]",
											["lsp"] = "[]",
											["path"] = "[󰉋]",
											["snippets"] = "[]",
											["ripgrep"] = "[]",
											["buffer"] = "[]",
											["emoji"] = "[]",
										}

										-- return the override or the item source
										return map[ctx.item.source_id] or ctx.item.source_name
									end,
									highlight = "BlinkCmpSource",
								},
							},
						},
					},
				},
				-- 'default' for mappings similar to built-in completion
				-- 'super-tab' for mappings similar to vscode (tab to accept, arrow keys to navigate)
				-- 'enter' for mappings similar to 'super-tab' but with 'enter' to accept
				-- See the full "keymap" documentation for information on defining your own keymap.
				cmdline = {
					keymap = {
						-- recommended, as the default keymap will only show and select the next item
						["<Tab>"] = { "show", "accept" },
					},
					completion = {
						menu = {
							auto_show = true,
						},
					},
				},
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
					default = { "lazydev", "lsp", "dictionary", "emoji", "path", "snippets", "buffer" },
					per_filetype = {
						codecompanion = { "codecompanion" },
					},
					providers = {
						lazydev = {
							name = "LazyDev",
							module = "lazydev.integrations.blink",
							score_offset = 100,
							fallbacks = { "lsp" },
						},
						lsp = {
							score_offset = 99,
						},
						buffer = {
							opts = {
								-- or (recommended) filter to only "normal" buffers
								get_bufnrs = function()
									return vim.tbl_filter(function(bufnr)
										return vim.bo[bufnr].buftype == ""
									end, vim.api.nvim_list_bufs())
								end,
							},
						},
						dictionary = {
							module = "blink-cmp-dictionary",
							name = "Dict",
							-- Make sure this is at least 2.
							-- 3 is recommended
							min_keyword_length = 5,
							opts = {
								-- options for blink-cmp-dictionary
							},
						},
						-- git = {
						-- 	module = "blink-cmp-git",
						-- 	name = "Git",
						-- 	opts = {
						-- 		-- options for the blink-cmp-git
						-- 	},
						-- },
						emoji = {
							module = "blink-emoji",
							name = "Emoji",
							score_offset = 15,
							opts = {
								insert = true,
							},
						},
						ripgrep = {
							module = "blink-ripgrep",
							name = "Ripgrep",
							-- the options below are optional, some default values are shown
							---@module "blink-ripgrep"
							---@type blink-ripgrep.Options
							opts = {
								prefix_min_len = 7,
								context_size = 5,
								max_filesize = "4K",
							},
						},
					},
				},
			})
		end,
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
		"yetone/avante.nvim",
		event = "VeryLazy",
		version = false, -- Never set this value to "*"! Never!
		enabled = false,
		opts = {
			provider = "gemini",
			gemini = {
				api_key_name = "GEMINI_API_KEY",
				model = "gemini-2.5-pro-preview-03-25", -- your desired model (or use gpt-4o, etc.)
				timeout = 30000, -- Timeout in milliseconds, increase this for reasoning models
				temperature = 0,
				max_completion_tokens = 8192, -- Increase this to include reasoning tokens (for reasoning models)
				--reasoning_effort = "medium", -- low|medium|high, only used for reasoning models
			},
		},
		-- if you want to build from source then do `make BUILD_FROM_SOURCE=true`
		build = "make",
		-- build = "powershell -ExecutionPolicy Bypass -File Build.ps1 -BuildFromSource false" -- for windows
		dependencies = {
			"nvim-treesitter/nvim-treesitter",
			"stevearc/dressing.nvim",
			"nvim-lua/plenary.nvim",
			"MunifTanjim/nui.nvim",
			--- The below dependencies are optional,
			"echasnovski/mini.pick", -- for file_selector provider mini.pick
			-- "nvim-telescope/telescope.nvim", -- for file_selector provider telescope
			"hrsh7th/nvim-cmp", -- autocompletion for avante commands and mentions
			"ibhagwan/fzf-lua", -- for file_selector provider fzf
			"nvim-tree/nvim-web-devicons", -- or echasnovski/mini.icons
			"zbirenbaum/copilot.lua", -- for providers='copilot'
			{
				-- support for image pasting
				"HakonHarnes/img-clip.nvim",
				event = "VeryLazy",
				opts = {
					-- recommended settings
					default = {
						embed_image_as_base64 = false,
						prompt_for_file_name = false,
						drag_and_drop = {
							insert_mode = true,
						},
						-- required for Windows users
						use_absolute_path = true,
					},
				},
			},
			{
				-- Make sure to set this up properly if you have lazy=true
				"MeanderingProgrammer/render-markdown.nvim",
				opts = {
					file_types = { "markdown", "Avante" },
				},
				ft = { "markdown", "Avante" },
			},
		},
		config = function(opts)
			require("avante").setup(opts)

			-- Removed in favor of CodeCompanion commit message generation
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
		"nvim-telescope/telescope-fzf-native.nvim",
		build = "make",
		enabled = false,
	},
	{
		"nvim-telescope/telescope.nvim",
		dependencies = {
			"nvim-lua/plenary.nvim",
			-- "nvim-telescope/telescope-fzf-native.nvim",
		},
		enabled = false,
		config = function()
			require("telescopeconfig")
		end,
	},
	{
		"ibhagwan/fzf-lua",
		dependencies = { "nvim-tree/nvim-web-devicons" },
		config = function()
			require("fzfconfig")
		end,
	},
	{
		"folke/noice.nvim",
		branch = "main",
		config = function()
			require("noice").setup({
				routes = {
					-- filter write messages "xxxL, xxxB"
					{ filter = { event = "msg_show", find = "%dL" }, opts = { skip = true } },
					-- filter yank messages
					{ filter = { event = "msg_show", find = "%d lines yanked" }, opts = { skip = true } },
					-- filter undo messages
					{ filter = { event = "msg_show", find = "%d change" }, opts = { skip = true } },
					{ filter = { event = "msg_show", find = "%d more line" }, opts = { skip = true } },
					{ filter = { event = "msg_show", find = "%d fewer line" }, opts = { skip = true } },
					{ filter = { event = "msg_show", find = "Already at newest change" }, opts = { skip = true } },
					{ filter = { event = "msg_show", find = "Already at oldest change" }, opts = { skip = true } },
					{
						filter = { event = "msg_show", find = "File changed on disk. Buffer reloaded." },
						opts = { skip = true },
					},
				},
				popupmenu = { enabled = false },
				-- cmdline = {
				-- 	format = {
				-- 		conceal = false,
				-- 	},
				-- },
				-- lsp = {
				-- 	override = {
				-- 		["vim.lsp.util.convert_input_to_markdown_lines"] = true,
				-- 		["vim.lsp.util.stylize_markdown"] = true,
				-- 		["cmp.entry.get_documentation"] = true,
				-- 	},
				-- },
				notify = {
					enabled = true,
					timeout_ms = 500,
				},
				presets = { inc_rename = true },
				views = {
					cmdline_popup = {
						border = {
							style = "none",
							-- padding = { 2, 3 },
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
		"kaarmu/typst.vim",
		ft = "typst",
		lazy = false,
	},
	{
		"williamboman/mason.nvim",
		config = function()
			require("mason").setup()
		end,
	},
	{
		"williamboman/mason-lspconfig.nvim",
		dependencies = { "williamboman/mason.nvim" },
		config = function()
			require("mason-lspconfig").setup({
				automatic_installation = true,
			})
		end,
	},
	{
		"neovim/nvim-lspconfig",
		dependencies = {
			"saghen/blink.cmp",
			"nvim-tree/nvim-web-devicons",
			"onsails/lspkind.nvim",
			"netmute/ctags-lsp.nvim",
			"Decodetalkers/csharpls-extended-lsp.nvim",
			"williamboman/mason-lspconfig.nvim",
		},
		opts = {
			servers = {
				lua_ls = {
					settings = {
						Lua = {
							hint = {
								enable = true,
								enableType = true,
								enableFunction = true,
							},
						},
					},
					capabilities = {
						textDocument = {
							semanticTokens = {
								full = false,
								delta = false,
							},
						},
					},
				},
				csharp_ls = {
					capabilities = {
						textDocument = {
							semanticTokens = {
								full = false,
								delta = false,
							},
						},
					},
					settings = {
						csharp = {
							enableRoslynAnalyzers = true,
							enableEditorConfigSupport = true,
							enableMsBuildLoadProjectsOnDemand = true,
							enableImportCompletion = true,
							enableFormatOnType = true,
							enableFormatOnSave = true,
						},
					},
				},
				ts_ls = {
					settings = {
						completions = {
							completeFunctionCalls = true,
						},
						typescript = {
							inlayHints = {
								includeInlayParameterNameHints = "all",
								includeInlayParameterNameHintsWhenArgumentMatchesName = false,
								includeInlayFunctionParameterTypeHints = true,
								includeInlayVariableTypeHints = true,
								includeInlayVariableTypeHintsWhenTypeMatchesName = false,
								includeInlayPropertyDeclarationTypeHints = true,
								includeInlayFunctionLikeReturnTypeHints = true,
								includeInlayEnumMemberValueHints = true,
							},
						},
						javascript = {
							inlayHints = {
								includeInlayParameterNameHints = "all",
								includeInlayParameterNameHintsWhenArgumentMatchesName = false,
								includeInlayFunctionParameterTypeHints = true,
								includeInlayVariableTypeHints = true,
								includeInlayVariableTypeHintsWhenTypeMatchesName = false,
								includeInlayPropertyDeclarationTypeHints = true,
								includeInlayFunctionLikeReturnTypeHints = true,
								includeInlayEnumMemberValueHints = true,
							},
						},
					},
					capabilities = {
						textDocument = {
							semanticTokens = {
								full = false,
								delta = false,
							},
						},
					},
				},
				gopls = {
					hints = {
						rangeVariableTypes = true,
						parameterNames = true,
						constantValues = true,
						assignVariableTypes = true,
						compositeLiteralFields = true,
						compositeLiteralTypes = true,
						functionTypeParameters = true,
					},
				},
				ruby_lsp = {},
				jsonls = {
					settings = {
						json = {
							format = {
								enable = true,
							},
						},
						validate = { enable = true },
					},
				},
				-- marksman = {},
				-- 				pkm_lsp = {
				-- 					cmd = { "pkm", "lsp" },
				-- 					filetypes = { "markdown" },
				-- 					autostart = true,
				-- 					single_file_support = true,
				-- 					root_dir = function(fname)
				-- 						return vim.fs.root(fname, { ".lancedb", ".git" }) or vim.fn.getcwd()
				-- 					end,
				-- 					init_options = {
				-- 						dbPath = ".lancedb",
				-- 						debounceMs = 1000,
				-- 					},
				-- 					settings = {},
				-- 				},
				bigquery_lsp = {
					cmd = { "bigquery", "lsp" },
					filetypes = { "sql", "bq", "bigquery" },
					autostart = true,
					single_file_support = true,
					root_dir = function(fname)
						-- Look for BigQuery project markers or fall back to git root / cwd
						return vim.fs.root(
							fname,
							{ ".bigqueryrc", ".bqproject", ".git", "pyproject.toml", "Cargo.toml" }
						) or vim.fn.getcwd()
					end,
					init_options = {},
					settings = {},
					on_attach = function(client, bufnr)
						-- Optional: Add buffer-specific keymaps here
						vim.notify("BigQuery LSP attached to buffer " .. bufnr, vim.log.levels.INFO)
					end,
				},
				pylsp = {},
				html = {},
				yamlls = {},
				bashls = {
					filetypes = { "sh", "zsh", "bash" },
				},
				zls = {},
				tinymist = {},
				lemminx = {
					-- XML Language Server
					init_options = {
						settings = {
							xml = {
								format = {
									enabled = true,
									splitAttributes = false,
									joinCDATALines = false,
									joinCommentLines = false,
									joinContentLines = false,
									spaceBeforeEmptyCloseTag = true,
									preservedNewlines = 1,
								},
								completion = {
									autoCloseTags = true,
								},
								validation = {
									enabled = true,
								},
								symbols = {
									enabled = true,
								},
							},
						},
					},
				},
			},
			opts = {
				inlay_hints = { enabled = true },
			},
		},
		config = function(_, opts)
			require("lsp") -- NOTE: this is requried to get keybinds for fallback registration
			for server, config in pairs(opts.servers) do
				-- passing config.capabilities to blink.cmp merges with the capabilities in your
				-- `opts[server].capabilities, if you've defined it
				config.capabilities = require("blink.cmp").get_lsp_capabilities(config.capabilities)
				vim.lsp.config(server, config)

				-- Skip auto-enabling markdown LSPs - our autocmd handles them conditionally
				if server ~= "marksman" then
					vim.lsp.enable(server)
				end
			end

			-- Capture server configs for autocmd closure
			-- 			local pkm_config = opts.servers.pkm_lsp
			-- 			local marksman_config = opts.servers.marksman
			--
			-- 			-- Smart LSP selection: pkm_lsp in PKM workspaces, Marksman elsewhere
			-- 			vim.api.nvim_create_autocmd("FileType", {
			-- 				pattern = "markdown",
			-- 				callback = function(args)
			-- 					local root_dir = vim.fs.root(args.file, { ".lancedb", ".git", ".marksman.toml" })
			-- 					local is_pkm_workspace = root_dir and vim.fn.isdirectory(root_dir .. "/.lancedb") == 1
			--
			-- 					if is_pkm_workspace and pkm_config then
			-- 						-- PKM workspace: use pkm_lsp for wikilink completions
			-- 						local config = vim.tbl_deep_extend("force", {
			-- 							name = "pkm_lsp",
			-- 							cmd = pkm_config.cmd,
			-- 							filetypes = pkm_config.filetypes,
			-- 							root_dir = root_dir,
			-- 							init_options = pkm_config.init_options,
			-- 							settings = pkm_config.settings,
			-- 						}, { capabilities = require("blink.cmp").get_lsp_capabilities(pkm_config.capabilities) })
			--
			-- 						vim.lsp.start(config)
			-- 					elseif marksman_config and root_dir then
			-- 						-- Regular markdown: use Marksman
			-- 						local config = vim.tbl_deep_extend("force", {
			-- 							name = "marksman",
			-- 							cmd = marksman_config.cmd or { "marksman", "server" },
			-- 							filetypes = { "markdown" },
			-- 							root_dir = root_dir,
			-- 						}, {
			-- 							capabilities = require("blink.cmp").get_lsp_capabilities(marksman_config.capabilities),
			-- 						})
			--
			-- 						vim.lsp.start(config)
			-- 					end
			-- 				end,
			-- 			})
			-- NOTE: Smart LSP selection for pkm-lsp and Marksman moved to ~/.config/nvim/lua/pkm-lsp.lua (loaded via require)

			-- Auto-start BigQuery LSP for SQL files
			vim.api.nvim_create_autocmd("FileType", {
				pattern = { "sql", "bq", "bigquery" },
				callback = function(args)
					local bigquery_config = opts.servers.bigquery_lsp
					if bigquery_config then
						local root_dir = bigquery_config.root_dir and bigquery_config.root_dir(args.file)
							or vim.fn.getcwd()
						local config = vim.tbl_deep_extend("force", {
							name = "bigquery_lsp",
							cmd = bigquery_config.cmd,
							filetypes = bigquery_config.filetypes,
							root_dir = root_dir,
							init_options = bigquery_config.init_options,
							settings = bigquery_config.settings,
							on_attach = bigquery_config.on_attach,
						}, {
							capabilities = require("blink.cmp").get_lsp_capabilities(bigquery_config.capabilities),
						})

						vim.lsp.start(config)
					end
				end,
			})

			-- User command to manually enable BigQuery LSP for current buffer
			vim.api.nvim_create_user_command("BigQueryLspStart", function()
				local bigquery_config = opts.servers.bigquery_lsp
				if bigquery_config then
					local config = vim.tbl_deep_extend("force", {
						name = "bigquery_lsp",
						cmd = bigquery_config.cmd,
						filetypes = bigquery_config.filetypes,
						root_dir = vim.fn.getcwd(),
						init_options = bigquery_config.init_options,
						settings = bigquery_config.settings,
						on_attach = bigquery_config.on_attach,
					}, { capabilities = require("blink.cmp").get_lsp_capabilities(bigquery_config.capabilities) })

					vim.lsp.start(config)
					vim.notify("BigQuery LSP started", vim.log.levels.INFO)
				else
					vim.notify("BigQuery LSP config not found", vim.log.levels.ERROR)
				end
			end, { desc = "Manually start BigQuery LSP for current buffer" })

			require("csharpls_extended").buf_read_cmd_bind()
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
		main = "ibl",
		---@module "ibl"
		---@type ibl.config
		opts = {},
	},
	{
		"christoomey/vim-tmux-navigator",
		init = function()
			vim.g.tmux_navigator_no_mappings = 1
			vim.g.tmux_navigator_save_on_switch = 1
		end,
		config = function()
			-- Use <Cmd> instead of : to execute commands without changing modes
			-- This prevents literal text insertion in insert mode
			vim.keymap.set({ "i", "n" }, "<C-h>", "<Cmd>TmuxNavigateLeft<cr>", { noremap = true, silent = true })
			vim.keymap.set({ "i", "n" }, "<C-j>", "<Cmd>TmuxNavigateDown<cr>", { noremap = true, silent = true })
			vim.keymap.set({ "i", "n" }, "<C-k>", "<Cmd>TmuxNavigateUp<cr>", { noremap = true, silent = true })
			vim.keymap.set({ "i", "n" }, "<C-l>", "<Cmd>TmuxNavigateRight<cr>", { noremap = true, silent = true })
		end,
	},
	{
		"lanej/vim-prosession",
		dependencies = "tpope/vim-obsession",
		init = function()
			-- Set minimum window sizes before session restoration
			vim.opt.winminheight = 1
			vim.opt.winminwidth = 1

			-- Don't save window sizes in sessions - let focus.nvim handle sizing
			vim.opt.sessionoptions:remove("winsize")

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
		"sindrets/diffview.nvim",
		config = function()
			require("diffview").setup({})

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
			vim.keymap.set("n", "<leader>bu", ":UndotreeToggle<CR>", { silent = true, noremap = true })
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
			vim.keymap.set("n", "<leader>gv", ":Git commit -v<CR>", { silent = true, noremap = true })
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
	{
		"vim-test/vim-test",
		config = function()
			vim.g["test#strategy"] = "neovim"

			-- Set test executable for various languages
			vim.g["test#ruby#minitest#executable"] = "bundle exec ruby -Itest/"

			-- Use gotestsum instead of go test for colorful output
			vim.g["test#go#gotest#executable"] = "gotestsum --"
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
			vim.keymap.set("n", "<leader>tf", ":TestFile<CR>", { noremap = true, silent = true })
			vim.keymap.set("n", "<leader>tl", ":TestLast<CR>", { noremap = true, silent = true })
			vim.keymap.set("n", "<leader>ts", ":TestSuite<CR>", { noremap = true, silent = true })
			vim.keymap.set("n", "<leader>tt", ":TestNearest<CR>", { noremap = true, silent = true })
			vim.keymap.set("n", "<leader>tu", ":TestNearest<CR>", { noremap = true, silent = true })
			-- Go debug nearest
			function _G.GoDebugNearest()
				vim.g.test_go_runner = "delve"
				vim.cmd("TestNearest")
				vim.cmd("unlet g:test_go_runner")
			end
		end,
	},
	{
		"junegunn/vim-easy-align",
		config = function()
			vim.keymap.set({ "n", "x" }, "ga", "<Plug>(EasyAlign)")
		end,
	},
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
					TODO = { icon = "🫥", color = "info", alt = { "FIXME" } },
				},
			})
		end,
	},
	{
		"smjonas/inc-rename.nvim",
		config = function()
			require("inc_rename").setup({})
			vim.keymap.set({ "n", "v" }, "<leader>ri", ":IncRename ", {
				noremap = true,
				silent = true,
			})
			vim.keymap.set({ "n", "v" }, "<leader>rn", ":IncRename ", {
				noremap = true,
				silent = true,
			})
		end,
	},
	{
		"nvim-neotest/neotest",
		dependencies = {
			"nvim-neotest/nvim-nio",
			"nvim-lua/plenary.nvim",
			"antoinemadec/FixCursorHold.nvim",
			"nvim-treesitter/nvim-treesitter",
			"fredrikaverpil/neotest-golang",
			-- "nvim-neotest/neotest-jest",
		},
		enabled = false,
		config = function()
			require("neotest").setup({
				adapters = {
					require("neotest-golang")({ runner = "gotestsum", sanitize_output = true }), -- Apply configuration
					require("rustaceanvim.neotest"),
					-- require("neotest-jest")({
					-- 	jestCommand = require("neotest-jest.jest-util").getJestCommand(vim.fn.expand("%:p:h"))
					-- 		.. " --watch",
					-- 	-- jestConfigFile = "custom.jest.config.ts",
					-- 	-- env = { CI = true },
					-- 	---@diagnostic disable-next-line: unused-local
					-- 	cwd = function(path)
					-- 		return vim.fn.getcwd()
					-- 	end,
					-- }),
				},
			})

			vim.keymap.set("n", "<leader>tw", require("neotest").watch.watch, { silent = true, noremap = true })
			vim.keymap.set("n", "<leader>tru", require("neotest").run.run, { silent = true, noremap = true })
			vim.keymap.set("n", "<leader>trf", function()
				require("neotest").run.run(vim.fn.expand("%"))
			end, { silent = true, noremap = true })
			vim.keymap.set("n", "<leader>ta", require("neotest").run.attach, { silent = true, noremap = true })
			vim.keymap.set("n", "]t", require("neotest").jump.next, { silent = true, noremap = true })
			vim.keymap.set("n", "[t", require("neotest").jump.prev, { silent = true, noremap = true })
		end,
	},
	{
		name = "copilot.lua",
		url = "git@github.com:zbirenbaum/copilot.lua",
		cmd = "Copilot",
		event = "InsertEnter",
		cond = function()
			-- check that node is installed and is greater >= 20.x
			return vim.fn.executable("node") == 1 and vim.fn.system("node -v") >= "v20.0.0"
		end,
		config = function()
			require("copilot").setup({
				suggestion = { enabled = false },
				panel = { enabled = false },
			})
		end,
	},
	{
		"github/copilot.vim",
		cond = function()
			-- check that node is installed and is greater >= 20.x
			return vim.fn.executable("node") == 1 and vim.fn.system("node -v") >= "v20.0.0"
		end,
	},
	{
		"iamcco/markdown-preview.nvim",
		cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
		build = function()
			vim.fn["mkdp#util#install"]()
		end,
		ft = { "markdown" },
	},
	{
		"pwntester/octo.nvim",
		dependencies = {
			"nvim-lua/plenary.nvim",
			"ibhagwan/fzf-lua",
			"nvim-tree/nvim-web-devicons",
		},
		cmd = "Octo",
		config = function()
			require("octo").setup({
				picker = "fzf-lua",
				picker_config = {
					use_emojis = false,
					mappings = {
						open_in_browser = { lhs = "<C-b>", desc = "open issue in browser" },
					},
				},
			})
		end,
	},
	{
		"OXY2DEV/markview.nvim",
		lazy = true, -- Recommended
		enabled = false,
		ft = "markdown", -- If you decide to lazy-load anyway
		dependencies = {
			-- You will not need this if you installed the
			-- parsers manually
			-- Or if the parsers are in your $RUNTIMEPATH
			"nvim-treesitter/nvim-treesitter",
			"nvim-tree/nvim-web-devicons",
		},
		opts = {
			preview = {
				filetypes = { "markdown", "codecompanion" },
				ignore_buftypes = {},
			},
			markdown = {
				headings = {
					shift_width = 0,
				},
				list_items = {
					shift_width = 1,
					indent_size = 1,
				},
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
					go = { "gofmt", "goimports", "gci" },
					-- Conform will run the first available formatter
					ruby = {
						"prettierd",
						"prettier",
						"rufo",
						"rubyfmt",
						"rubocop",
						"solargraph",
						timeout_ms = 7000,
						stop_after_first = true,
						lsp_format = "prefer",
					},
					javascript = { "prettierd", "prettier", stop_after_first = true },
					typescript = { "prettierd", "prettier", stop_after_first = true },
				},
				log_level = vim.log.levels.DEBUG,
				formatters = {
					rubocop = {
						command = "rubocop",
						inherit = false,
						stdin = false,
						args = { "-A", "-f", "quiet", "$FILENAME" },
					},
				},
			})

			vim.keymap.set("n", "<leader>bf", function()
				require("conform").format()
			end, {
				noremap = false,
				silent = true,
			})
			vim.api.nvim_create_autocmd("BufWritePre", {
				pattern = { "*.ts", "*.rs", "*.py", "*.lua", "*.js", "*.sh", "*.go" },
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
	{
		"chrisgrieser/nvim-lsp-endhints",
		event = "LspAttach",
		opts = {
			icons = {
				type = " ",
				parameter = " ",
				offspec = " ", -- hint kind not defined in official LSP spec
				unknown = " ", -- hint kind is nil
			},
			label = {
				truncateAtChars = 20,
				padding = 1,
				marginLeft = 0,
				sameKindSeparator = ", ",
			},
			extmark = {
				priority = 50,
			},
			autoEnableHints = true,
		},
	},
	{
		"nvim-treesitter/nvim-treesitter-context",
		opts = {
			enable = true, -- Enable this plugin (Can be enabled/disabled later via commands)
			multiwindow = true, -- Enable multiwindow support.
			max_lines = 0, -- How many lines the window should span. Values <= 0 mean no limit.
			min_window_height = 32, -- Minimum editor window height to enable context. Values <= 0 mean no limit.
			line_numbers = true,
			multiline_threshold = 20, -- Maximum number of lines to show for a single context
			separator = "⎯", -- Separator between context and line number
			trim_scope = "outer", -- Which context lines to discard if `max_lines` is exceeded. Choices: 'inner', 'outer'
			mode = "cursor", -- Line used to calculate context. Choices: 'cursor', 'topline'
		},
	},
	{
		"olimorris/codecompanion.nvim",
		dependencies = {
			"nvim-lua/plenary.nvim",
			"nvim-treesitter/nvim-treesitter",
			"echasnovski/mini.diff",
			"copilot.lua",
		},
		enabled = true,
		config = function()
			require("codecompanion").setup({
				display = {
					diff = {
						provider = "mini_diff",
					},
					chat = {
						window = {
							layout = "float",
							border = "double",
						},
						icons = {
							pinned_buffer = " ",
							watched_buffer = "👀 ",
						},
					},
				},
				adapters = {
					http = {
						openai = function()
							return require("codecompanion.adapters").extend("openai", {
								env = {
									api_key = os.getenv("OPENAI_API_KEY"),
								},
							})
						end,
					},
				},
				strategies = {
					inline = {
						adapter = "copilot",
						keymaps = {
							accept_change = {
								modes = { n = "ga" },
								description = "Accept the suggested change",
							},
							reject_change = {
								modes = { n = "gr" },
								description = "Reject the suggested change",
							},
						},
					},
					chat = {
						adapter = "copilot",
						slash_commands = {
							["file"] = {
								callback = "strategies.chat.slash_commands.file",
								description = "Select a file using fzf-lua",
								opts = {
									-- provider = "fzf_lua", -- Other options include 'default', 'mini_pick', 'fzf_lua', snacks
									contains_code = true,
								},
							},
						},
						keymaps = {
							send = {
								modes = { n = "<C-s>", i = "<C-s>" },
							},
							close = {
								modes = { n = "<C-c>", i = "<C-c>" },
							},
						},
					},
				},
			})

			vim.keymap.set({ "n", "v" }, "<leader>co", ":CodeCompanionChat<CR>", { silent = true, noremap = true })
			vim.keymap.set({ "n", "v" }, "<leader>ccf", ":CodeCompanion /lsp<CR>", { silent = true, noremap = true })
			vim.keymap.set({ "n", "v" }, "<leader>ccx", ":CodeCompanion /fix<CR>", { silent = true, noremap = true })

			-- Generate commit message using CodeCompanion with Copilot
			vim.keymap.set("n", "<leader>ccm", function()
				local bufname = vim.api.nvim_buf_get_name(0)
				local is_commit_buffer = bufname:match("COMMIT_EDITMSG$") or vim.bo.filetype == "gitcommit"

				if not is_commit_buffer then
					vim.notify("Use this in a git commit buffer (run 'git commit' first)", vim.log.levels.WARN)
					return
				end

				-- Check if there are staged changes
				local diff_check = vim.fn.system("git diff --cached --quiet")
				if vim.v.shell_error == 0 then
					vim.notify("No staged changes to commit", vim.log.levels.WARN)
					return
				end

				vim.notify("Generating commit message with Copilot...", vim.log.levels.INFO)

				-- Save current git comments before clearing
				local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
				local comment_lines = {}
				local found_comment = false
				for _, line in ipairs(lines) do
					if line:match("^#") then
						found_comment = true
					end
					if found_comment then
						table.insert(comment_lines, line)
					end
				end

				-- Get current buffer content (may have partial message)
				-- Filter out git comment lines (starting with #)
				local all_lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
				local content_lines = {}
				for _, line in ipairs(all_lines) do
					if not line:match("^#") then
						table.insert(content_lines, line)
					end
				end
				local current_content = table.concat(content_lines, "\n"):gsub("^%s+", ""):gsub("%s+$", "")

				-- Debug: show what content was found
				if current_content ~= "" then
					vim.notify("Found existing content (" .. #current_content .. " chars): " .. vim.fn.trim(current_content:sub(1, 60)) .. (#current_content > 60 and "..." or ""), vim.log.levels.INFO)
				else
					vim.notify("No existing content found, generating fresh message", vim.log.levels.INFO)
				end

				-- Get the staged diff
				local diff = vim.fn.system("git diff --cached")

				-- Build prompt with buffer content and diff
				local has_existing_content = current_content ~= ""
				local prompt
				if has_existing_content then
					prompt = string.format([[You are an expert Git commit message specialist. Generate a commit message following Commitizen conventional format.

**IMPORTANT:** The user has started writing a commit message. Use their draft as context and improve it while preserving their intent and any specific details they included.

Existing draft in buffer:
%s

Staged changes:
%s

**Commit Message Structure:**
- Format: `<type>(<scope>): <subject>`
- Subject line: Maximum 50 characters
- Body (when needed): Wrap at 72 characters

**Valid Types:**
- feat: New features
- fix: Bug fixes
- docs: Documentation changes
- style: Code style changes
- refactor: Code refactoring
- perf: Performance improvements
- test: Adding/updating tests
- build: Build system or dependency changes
- ci: CI/CD configuration
- chore: Maintenance tasks

**Scope Guidelines:**
- Use lowercase
- Be specific but concise (e.g., 'auth', 'api', 'cli', 'config')
- Omit scope if change affects multiple areas broadly

**Subject Line Rules:**
- Use imperative mood ('add', 'fix', 'update', not 'added', 'fixed', 'updated')
- Start with lowercase letter
- No period at the end
- Focus on what the change does, not how

**Quality Standards:**
- Subject must be under 50 characters
- Use present tense, imperative mood
- Be specific about what changed
- Avoid generic terms when more specific verbs apply
- NEVER mention AI, Claude, or automated generation

**Output Format:**
Provide ONLY the raw commit message text with NO code fences, NO markdown formatting, NO commentary.]], current_content, diff)
				else
					prompt = string.format([[You are an expert Git commit message specialist. Generate a commit message following Commitizen conventional format.

Staged changes:
%s

**Commit Message Structure:**
- Format: `<type>(<scope>): <subject>`
- Subject line: Maximum 50 characters
- Body (when needed): Wrap at 72 characters

**Valid Types:**
- feat: New features
- fix: Bug fixes
- docs: Documentation changes
- style: Code style changes
- refactor: Code refactoring
- perf: Performance improvements
- test: Adding/updating tests
- build: Build system or dependency changes
- ci: CI/CD configuration
- chore: Maintenance tasks

**Scope Guidelines:**
- Use lowercase
- Be specific but concise (e.g., 'auth', 'api', 'cli', 'config')
- Omit scope if change affects multiple areas broadly

**Subject Line Rules:**
- Use imperative mood ('add', 'fix', 'update', not 'added', 'fixed', 'updated')
- Start with lowercase letter
- No period at the end
- Focus on what the change does, not how

**Quality Standards:**
- Subject must be under 50 characters
- Use present tense, imperative mood
- Be specific about what changed
- Avoid generic terms when more specific verbs apply
- NEVER mention AI, Claude, or automated generation

**Output Format:**
Provide ONLY the raw commit message text with NO code fences, NO markdown formatting, NO commentary.]], diff)
				end

				-- Use CodeCompanion's inline strategy with Copilot adapter
				require("codecompanion").inline({
					adapter = "copilot",
					prompt = prompt,
					callback = function(result)
						local output = result

						-- Strip code fences if present
						output = output:gsub("^```%w*\n", "") -- Remove opening fence
						output = output:gsub("\n```$", "") -- Remove closing fence
						output = output:gsub("^%s+", ""):gsub("%s+$", "") -- Trim whitespace

						if output == "" then
							vim.notify("Copilot returned empty response", vim.log.levels.ERROR)
							return
						end

						-- Split message into lines and add blank line separator
						local msg_lines = vim.split(output, "\n", { plain = true })
						table.insert(msg_lines, "")

						-- Combine with preserved git comments
						for _, line in ipairs(comment_lines) do
							table.insert(msg_lines, line)
						end

						-- Replace entire buffer content
						vim.api.nvim_buf_set_lines(0, 0, -1, false, msg_lines)
						vim.api.nvim_win_set_cursor(0, { 1, 0 })
						vim.notify("Commit message generated!", vim.log.levels.INFO)
					end,
				})
			end, { desc = "Generate commit message with Copilot" })

			vim.keymap.set(
				{ "n", "v" },
				"<leader>ccu",
				":CodeCompanion @editor #buffer",
				{ silent = true, noremap = true }
			)

			-- NOTE: This keymap sets a command to request a comment for the selected code.
			-- The comment should provide clarity and remove surprises, using tags like `NOTE:`, `PERF:`, `WTF:`, `WARN:`, etc.
			-- The command is executed in visual mode with the leader key followed by `cco`.
			vim.keymap.set(
				{ "v" },
				"<leader>cco",
				":CodeCompanion #buffer @editor You are a software engineer that is committed to commenting code to provide clarity and remove suprises.  Please provide a comment for this code, using `NOTE:`, `PERF:`, `WTF:`, `WARN:`, etc where appropriate.  If an entire method or function is detected, provide a comment only for the top-level entity.<CR>",
				{ silent = true, noremap = true }
			)

			vim.keymap.set(
				{ "n", "v" },
				"<leader>cce",
				":CodeCompanion /explain<CR>",
				{ silent = true, noremap = true }
			)
		end,
	},
	{
		"epwalsh/obsidian.nvim",
		version = "*", -- recommended, use latest release instead of latest commit
		lazy = true,
		enabled = false,
		ft = "markdown",
		-- Replace the above line with this if you only want to load obsidian.nvim for markdown files in your vault:
		-- event = {
		--   -- If you want to use the home shortcut '~' here you need to call 'vim.fn.expand'.
		--   -- E.g. "BufReadPre " .. vim.fn.expand "~" .. "/my-vault/*.md"
		--   -- refer to `:h file-pattern` for more examples
		--   "BufReadPre path/to/my-vault/*.md",
		--   "BufNewFile path/to/my-vault/*.md",
		-- },
		dependencies = {
			-- Required.
			"nvim-lua/plenary.nvim",

			-- see below for full list of optional dependencies 👇
		},
		completion = {
			-- Enables completion using nvim_cmp
			nvim_cmp = false,
			-- Enables completion using blink.cmp
			blink = true,
			-- Trigger completion at 2 chars.
			min_chars = 3,
		},
		opts = {
			disable_frontmatter = false,
			workspaces = {
				{
					name = "work",
					path = "~/share/work",
				},
			},
		},
		config = function(opts)
			require("obsidian").setup(opts)

			local function generate_identifier()
				local date = os.date("%Y%m%d")
				local random = ""
				for _ = 1, 6 do
					local r = math.random(0, 35)
					random = random .. string.char(r < 10 and (r + 48) or (r + 87))
				end
				return date .. "-" .. random
			end

			vim.keymap.set("n", "<leader>ni", function()
				vim.print(vim.inspect(generate_identifier()))
				local inbox_dir = vim.fn.getcwd() .. "/inbox"
				local filename = generate_identifier() .. ".md"
				local full_path = inbox_dir .. "/" .. filename

				if vim.fn.filereadable(full_path) == 0 then
					local f = io.open(full_path, "w")
					if f then
						f:close()
					end
				end

				vim.cmd("edit " .. full_path)
			end, { desc = "New inbox note" })
		end,
	},
	{
		"ravitemer/mcphub.nvim",
		dependencies = {
			"nvim-lua/plenary.nvim", -- Required for Job and HTTP requests
		},
		-- comment the following line to ensure hub will be ready at the earliest
		cmd = "MCPHub", -- lazy load by default
		build = "npm install -g mcp-hub@latest", -- Installs required mcp-hub npm module
		-- uncomment this if you don't want mcp-hub to be available globally or can't use -g
		-- build = "bundled_build.lua",  -- Use this and set use_bundled_binary = true in opts  (see Advanced configuration)
		config = function()
			require("mcphub").setup()
		end,
	},
	{
		-- Make sure to set this up properly if you have lazy=true
		"MeanderingProgrammer/render-markdown.nvim",
		opts = {
			file_types = { "markdown", "Avante" },
			render_modes = { "n", "c", "i" },
			anti_conceal = {
				enabled = true,
			},
			html = {
				enabled = true,
				comment = {
					conceal = false, -- Don't conceal HTML comments - keep them always visible
				},
			},
		},
		ft = { "markdown", "Avante" },
	},
	{
		"3rd/image.nvim",
		build = false,
		-- Disable in tmux due to known issues with allow-passthrough and session switching
		-- See: https://github.com/3rd/image.nvim/issues/145
		-- Images may appear on wrong tmux session when switching sessions
		cond = function()
			return vim.env.TMUX == nil
		end,
		opts = {
			processor = "magick_cli",
			integrations = {
				markdown = {
					enabled = true,
					download_remote_images = true,
					filetypes = { "markdown" },
				},
			},
		},
		ft = { "markdown" },
	},
	{
		"brenoprata10/nvim-highlight-colors",
		opts = {
			render = "background",
			enable_hex = true,
			enable_short_hex = true,
			enable_rgb = true,
			enable_hsl = true,
			enable_var_usage = true,
			enable_named = true,
			enable_tailwind = "normal",
		},
	},
	"cedarbaum/fugitive-azure-devops.vim",
	{
		"s3rvac/vim-syntax-jira",
	},
	{
		"greggh/claude-code.nvim",
		dependencies = {
			"nvim-lua/plenary.nvim", -- Required for git operations
		},
		config = function()
			require("claude-code").setup({
				refresh = {
					show_notifications = false,
				},
			})
		end,
	},
	{
		"lanej/focus.nvim",
		branch = "feature/width-min-columns",
		config = function()
			require("focus").setup({
				autoresize = {
					enable = true,
					width = 0,
					height = 0,
					minwidth = 40,
					minheight = 5,
					equalise_min_cols = 120, -- Use equal splits when terminal >= 120 columns, golden ratio when < 120
				},
				ui = {
					number = false,
					relativenumber = false,
					hybridnumber = false,
					absolutenumber_unfocussed = false,
					cursorline = true,
					cursorcolumn = false,
					colorcolumn = {
						enable = false,
					},
					signcolumn = true,
					winhighlight = false,
				},
			})
		end,
	},
})

vim.keymap.set("n", "<leader>vpu", ":Lazy update<CR>", { silent = true, noremap = true })
vim.keymap.set("n", "<leader>vpi", ":Lazy home<CR>", { silent = true, noremap = true })
vim.keymap.set("n", "<leader>vpc", ":Lazy clean<CR>", { silent = true, noremap = true })

-- XML-specific configuration
vim.api.nvim_create_autocmd("FileType", {
	pattern = { "xml" },
	callback = function()
		-- Format XML with leader-f in normal/visual mode
		vim.keymap.set({ "n", "v" }, "<leader>f", function()
			vim.lsp.buf.format({ async = false })
		end, { buffer = true, desc = "Format XML" })

		-- Better folding for XML
		vim.opt_local.foldmethod = "expr"
		vim.opt_local.foldexpr = "nvim_treesitter#foldexpr()"
		vim.opt_local.foldenable = false -- Start with folds open

		-- Indent settings
		vim.opt_local.shiftwidth = 2
		vim.opt_local.tabstop = 2
		vim.opt_local.softtabstop = 2
	end,
})

-- Load Phabricator LSP configuration
require("phab-lsp")
require("pkm-lsp")

vim.cmd([[set secure]])
