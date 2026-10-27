-- Isolated acceptance run: uv run --no-project scripts/test-nvim-navigation.py
local repo = vim.fn.getcwd()
local temp = vim.fn.tempname()
vim.fn.mkdir(temp, "p")
temp = assert(vim.uv.fs_realpath(temp))
local lazy = vim.env.NVIM_TEST_PLUGIN_ROOT or vim.fn.expand("~/.local/share/nvim/lazy")
vim.opt.runtimepath:prepend(repo .. "/nvim")
vim.opt.runtimepath:append(lazy .. "/todo-comments.nvim")
vim.opt.runtimepath:append(lazy .. "/plenary.nvim")
vim.opt.runtimepath:append(lazy .. "/fzf-lua")
vim.opt.runtimepath:append(lazy .. "/nvim-treesitter/runtime")
vim.opt.runtimepath:append(vim.env.NVIM_TEST_SITE or vim.fn.expand("~/.local/share/nvim/site"))
vim.g.mapleader = ","
vim.o.swapfile = false
require("annotations").setup()
vim.cmd("runtime plugin/todo.vim")

local function wait(predicate, message)
	assert(vim.wait(5000, predicate, 10), message)
end

local function workflow()
	wait(function()
		return require("todo-comments.config").loaded
	end, "Annotation setup did not load")
	local source = temp .. "/annotations.lua"
	vim.fn.writefile({
		"-- WHY: Preserve ordering because callers use the first match.",
		"local value = 1",
		"-- FIXME: Expired credentials bypass refresh.",
		"local expired = true",
		"-- GAH: Keep the legacy workaround visible.",
		"return value, expired",
	}, source)
	vim.cmd.cd(vim.fn.fnameescape(temp))
	vim.cmd.edit(vim.fn.fnameescape(source))
	vim.bo.filetype = "lua"
	vim.treesitter.start(0, "lua")
	vim.cmd.redraw()
	local buf = vim.api.nvim_get_current_buf()
	local ns = vim.api.nvim_get_namespaces()["todo-comments"]
	local function highlighted(row, group)
		for _, mark in ipairs(vim.api.nvim_buf_get_extmarks(buf, ns, { row, 0 }, { row, -1 }, { details = true })) do
			if mark[4].hl_group == group then
				return true
			end
		end
		return false
	end
	wait(function()
		return highlighted(0, "TodoBgWHY") and highlighted(2, "TodoBgFIX") and highlighted(4, "TodoBgWTF")
	end, "Rationale, defect, or legacy comment lost its highlight")
	assert(
		vim.api.nvim_get_hl(0, { name = "TodoFgWHY" }).fg == vim.api.nvim_get_hl(0, { name = "TodoFgNOTE" }).fg,
		"Rationale comments lost hint styling"
	)

	vim.cmd.TodoQuickFix()
	wait(function()
		return #vim.fn.getqflist() == 3
	end, "Annotation search did not populate quickfix")
	local matches = vim.fn.getqflist()
	assert(matches[1].lnum == 1 and matches[2].lnum == 3 and matches[3].lnum == 5, "Search lost source rows")
	vim.cmd.cclose()
	vim.cmd.cfirst()
	vim.cmd.cnext()
	assert(vim.api.nvim_buf_get_name(0) == source, "Quickfix navigation lost the source file")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 3, "Quickfix navigation did not reach the defect")

	vim.cmd.normal(vim.api.nvim_replace_termcodes(",an", true, false, true))
	wait(function()
		return vim.bo.buftype == "terminal"
			and table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n"):find("Preserve ordering", 1, true)
	end, "Annotation mapping did not display real FzfLua results")
	vim.api.nvim_chan_send(vim.bo.channel, "Preserve ordering")
	vim.wait(400)
	vim.api.nvim_chan_send(vim.bo.channel, "\r")
	wait(function()
		return vim.bo.buftype ~= "terminal"
	end, "Annotation picker did not accept selection")
	assert(vim.api.nvim_buf_get_name(0) == source, "Annotation picker lost the source file")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 1, "Annotation picker did not reach the rationale")
	print("Annotation highlight, quickfix, and picker workflow passed")
end

local ok, err = xpcall(workflow, debug.traceback)
vim.fn.delete(temp, "rf")
if not ok then
	io.stderr:write(err .. "\n")
	vim.cmd.cquit(1)
end
vim.cmd("qa!")
