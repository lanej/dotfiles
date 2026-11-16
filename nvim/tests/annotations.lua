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
	if not vim.wait(5000, predicate, 10) then
		local detail = type(message) == "function" and message() or message
		error(detail .. "\n" .. table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n"))
	end
end

local function workflow()
	wait(function()
		return require("todo-comments.config").loaded
	end, "Annotation setup did not load")
	local source = temp .. "/annotations.lua"
	local annotations = {
		{ "WHY: Preserve ordering because callers use the first match.", "WHY" },
		{ "FIXME: Expired credentials bypass refresh.", "FIX" },
		{ "GAH: Keep the legacy workaround visible.", "WTF" },
		{ "rationale(cache): Leave misses uncached so newly created accounts appear immediately.", "rationale" },
		{ "warning: Reconcile an unknown payment outcome before retrying.", "warning" },
		{ "workaround(parser): Strip the BOM until upstream/repo#123 is fixed.", "workaround" },
		{ "todo(exports): Support cancellation.", "todo" },
		{ "fixme: Expired credentials currently bypass refresh.", "fixme" },
		{ "TODO:compact legacy annotation", "TODO" },
		{ "NOTE:  Legacy annotations can use extra spaces.", "NOTE" },
		{ "TODO:", "TODO" },
	}
	local lines = {}
	for _, annotation in ipairs(annotations) do
		table.insert(lines, "-- " .. annotation[1])
		table.insert(lines, "local value = 1")
	end
	local ordinary = {
		"Resolve eligibility before reserving any inventory.",
		"rationale(): Empty scopes are invalid.",
		"rationale(Cache): Scopes use lowercase.",
		"warning(retries)!: Breaking markers do not apply.",
		"fixme:Missing space.",
		"todo: ",
		"notrationale: This is not an annotation type.",
	}
	for _, comment in ipairs(ordinary) do
		table.insert(lines, "-- " .. comment)
		table.insert(lines, "local value = 1")
	end
	vim.fn.writefile(lines, source)
	vim.cmd.cd(vim.fn.fnameescape(temp))
	vim.cmd.edit(vim.fn.fnameescape(source))
	vim.bo.filetype = "lua"
	vim.treesitter.start(0, "lua")
	vim.o.lines = 60
	vim.cmd.redraw()
	local buf = vim.api.nvim_get_current_buf()
	local ns = vim.api.nvim_get_namespaces()["todo-comments"]
	local function highlighted(row, group)
		for _, mark in ipairs(vim.api.nvim_buf_get_extmarks(buf, ns, { row, 0 }, { row, -1 }, { details = true })) do
			if vim.fn.hlID(mark[4].hl_group) == vim.fn.hlID(group) then
				return true
			end
		end
		return false
	end
	local missing = {}
	wait(function()
		missing = {}
		for index, annotation in ipairs(annotations) do
			if not highlighted((index - 1) * 2, "TodoBg" .. annotation[2]) then
				table.insert(missing, annotation[2])
			end
		end
		return #missing == 0
	end, function()
		return "Annotations lost their highlight: "
			.. table.concat(missing, ", ")
			.. "\n"
			.. vim.inspect(vim.fn.winsaveview())
	end)
	for index in ipairs(ordinary) do
		local row = (#annotations + index - 1) * 2
		assert(
			#vim.api.nvim_buf_get_extmarks(buf, ns, { row, 0 }, { row, -1 }, {}) == 0,
			"Ordinary prose or malformed annotation received annotation styling: " .. ordinary[index]
		)
	end
	assert(
		vim.api.nvim_get_hl(0, { name = "TodoFgrationale" }).fg == vim.api.nvim_get_hl(0, { name = "TodoFgNOTE" }).fg,
		"Rationale comments lost hint styling"
	)

	vim.cmd.TodoQuickFix()
	wait(function()
		return #vim.fn.getqflist() == #annotations
	end, "Annotation search did not populate quickfix")
	local matches = vim.fn.getqflist()
	for index, annotation in ipairs(annotations) do
		assert(matches[index].lnum == (index - 1) * 2 + 1, "Search lost source rows")
		assert(matches[index].text:find(annotation[1], 1, true), "Search lost the annotation scope or explanation")
	end
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
	vim.api.nvim_chan_send(vim.bo.channel, "Leave misses uncached")
	wait(function()
		local screen = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
		local results = 0
		for _ in screen:gmatch("annotations%.lua:%d+:%d+:") do
			results = results + 1
		end
		return results == 1
			and screen:find("annotations.lua:7:", 1, true)
			and screen:find("Leave misses uncached", 1, true)
	end, "Annotation picker did not settle on a single scoped rationale result")
	vim.api.nvim_chan_send(vim.bo.channel, "\r")
	wait(function()
		return vim.bo.buftype ~= "terminal"
	end, "Annotation picker did not accept selection")
	assert(vim.api.nvim_buf_get_name(0) == source, "Annotation picker lost the source file")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 7, "Annotation picker did not reach the scoped rationale")
	print("Annotation highlight, quickfix, and picker workflow passed")
end

local ok, err = xpcall(workflow, debug.traceback)
vim.fn.delete(temp, "rf")
if not ok then
	io.stderr:write(err .. "\n")
	vim.cmd.cquit(1)
end
vim.cmd("qa!")
