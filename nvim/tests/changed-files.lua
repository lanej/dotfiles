-- Isolated acceptance: uv run --no-project scripts/test-nvim-navigation.py --check changed-files
local checkout = vim.fn.getcwd()
local plugins = vim.env.NVIM_TEST_PLUGIN_ROOT or vim.fn.expand("~/.local/share/nvim/lazy")
vim.opt.runtimepath:prepend(checkout .. "/nvim")
vim.opt.runtimepath:append(plugins .. "/fzf-lua")
vim.opt.runtimepath:append(plugins .. "/gitsigns.nvim")
vim.opt.runtimepath:append(vim.env.NVIM_TEST_SITE or vim.fn.expand("~/.local/share/nvim/site"))
vim.g.mapleader = ","
vim.o.columns = 160
vim.o.lines = 45
vim.o.hidden = true
vim.o.swapfile = false
vim.cmd("syntax on")
require("gitsignsconfig")
require("fzfconfig")
local fzf = require("fzf-lua")
local repo = vim.fn.tempname() .. " with spaces"
vim.fn.mkdir(repo, "p")
repo = assert(vim.uv.fs_realpath(repo))
local function git(...)
	local result = vim.system(vim.list_extend({ "git", "-C", repo }, { ... }), {}):wait()
	assert(result.code == 0, result.stderr)
end
local function write(file, lines)
	vim.fn.writefile(lines, repo .. "/" .. file)
end
local function wait(predicate, message)
	assert(vim.wait(5000, predicate, 10), message .. "\n" .. vim.fn.execute("messages"))
end
local function keys(mapping)
	vim.cmd.normal(vim.api.nvim_replace_termcodes(mapping, true, false, true))
end
local function workflow()
	git("init", "-qb", "main")
	git("config", "user.name", "Fixture")
	git("config", "user.email", "fixture@example.invalid")
	git("config", "commit.gpgsign", "false")
	git("config", "core.hooksPath", "/dev/null")
	local lines = {}
	for i = 1, 12 do
		lines[i] = "local value" .. i .. " = " .. i
	end
	vim.fn.writefile(lines, repo .. "/sample.lua", "b")
	vim.fn.writefile({ "local unchanged = true", "local value = 1" }, repo .. "/no-newline.lua", "b")
	local long_line = "local unchanged = '" .. string.rep("x", 5000) .. "'"
	vim.fn.writefile({ long_line .. "\r", "local value = 1" }, repo .. "/crlf.lua", "b")
	write("source.lua", { "return true" })
	write("deleted.lua", { "return false" })
	git("add", ".")
	git("commit", "-qm", "baseline")
	git("update-ref", "refs/remotes/origin/main", "HEAD")
	-- Exercise the supported origin/main fallback without origin/HEAD.
	lines[2] = "local branch_change = 2"
	vim.fn.writefile(lines, repo .. "/sample.lua", "b")
	write("added.lua", { "local added_file = true", "return added_file" })
	git("add", ".")
	git("commit", "-qm", "branch changes")
	lines[5] = "local staged_change = 5"
	vim.fn.writefile(lines, repo .. "/sample.lua", "b")
	git("add", "sample.lua")
	lines[8] = "local unstaged_change = 8"
	vim.fn.writefile(lines, repo .. "/sample.lua", "b")
	vim.fn.writefile({ "local unchanged = true", "local value = 2" }, repo .. "/no-newline.lua", "b")
	vim.fn.writefile({ long_line .. "\r", "local value = 2" }, repo .. "/crlf.lua", "b")
	write("added.lua", { "local added_file = 'edited again'", "return added_file" })
	git("rm", "-q", "deleted.lua")
	write('new "file".lua', { "local new_file = true", "return new_file" })
	vim.cmd.cd(vim.fn.fnameescape(repo))
	vim.cmd.edit("sample.lua")
	local source = vim.api.nvim_get_current_buf()
	vim.bo.filetype = "lua"
	vim.api.nvim_buf_set_lines(source, 7, 8, false, { "local unsaved_change = 8" })
	local previews = {}
	keys(",cf")
	wait(function()
		return vim.bo.buftype == "terminal"
			and table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n"):find("sample.lua", 1, true)
	end, "Changed-file picker did not open")
	local listing = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
	for file, status in pairs({ ["added.lua"] = "A", ["sample.lua"] = "M", ["deleted.lua"] = "D" }) do
		assert(listing:match(status .. "%s+[^\n]*" .. vim.pesc(file)), "Missing status prefix for " .. file)
	end
	assert(listing:match('%?%?[^\n]*new "file"%.lua'), "Missing untracked status or literal filename")
	local function select(file, content, expected, exact)
		vim.api.nvim_chan_send(vim.bo.channel, "\21" .. file)
		local buf
		wait(function()
			local win = fzf.utils.fzf_winobj()
			buf = win and win._previewer and win._previewer.preview_bufnr
			if not buf or not vim.api.nvim_buf_is_valid(buf) then
				return false
			end
			local cache = require("gitsigns.cache").cache[buf]
			return cache
				and cache.file == repo .. "/" .. file
				and table.concat(vim.api.nvim_buf_get_lines(buf, 0, -1, false), "\n"):find(content, 1, true)
		end, "Native file preview missing for " .. file)
		assert(buf ~= source and vim.bo[buf].buftype ~= "terminal", "Preview replaced the editing buffer")
		assert(vim.wo[fzf.utils.fzf_winobj().preview_winid].signcolumn == "yes:1", "Preview hides the Git gutter")
		wait(function()
			return vim.bo[buf].syntax == "lua" or vim.treesitter.highlighter.active[buf] ~= nil
		end, "Native Lua highlighting missing")
		wait(function()
			local groups = {}
			for _, ns in pairs(vim.api.nvim_get_namespaces()) do
				for _, mark in ipairs(vim.api.nvim_buf_get_extmarks(buf, ns, 0, -1, { details = true })) do
					local group = mark[4].sign_hl_group
					if group then
						groups[mark[2] + 1] = groups[mark[2] + 1] or {}
						groups[mark[2] + 1][group] = true
					end
				end
			end
			for line, group in pairs(expected) do
				if not groups[line] or not groups[line][group] then
					return false
				end
			end
			if exact then
				for line in pairs(groups) do
					if not expected[line] then
						return false
					end
				end
			end
			return true
		end, "Git sign layers missing for " .. file)
		previews[buf] = true
		return buf
	end
	local sample = select("sample.lua", "local unsaved_change = 8", {
		[2] = "DotfilesGitBranchChange",
		[5] = "GitSignsStagedChange",
		[8] = "GitSignsChange",
	}, true)
	assert(not vim.bo[sample].endofline, "Loaded preview invented a final newline")
	local no_newline = select("no-newline.lua", "local value = 2", { [2] = "GitSignsChange" }, true)
	assert(not vim.bo[no_newline].endofline, "Disk preview invented a final newline")
	local crlf = select("crlf.lua", "local value = 2", { [2] = "GitSignsChange" }, true)
	assert(vim.bo[crlf].fileformat == "dos", "Disk preview lost CRLF metadata")
	select("added.lua", "local added_file = 'edited again'", { [1] = "DotfilesGitBranchAdd" })
	select('new "file".lua', "local new_file = true", { [1] = "GitSignsUntracked" })
	assert(
		select("sample.lua", "local unsaved_change = 8", { [5] = "GitSignsStagedChange" }) == sample,
		"Revisiting the file did not preserve the native preview cache"
	)
	vim.api.nvim_chan_send(vim.bo.channel, "\r")
	wait(function()
		return vim.api.nvim_get_current_buf() == source
	end, "Status prefix broke file selection")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 2, "Selection did not jump to the first changed line")
	assert(vim.bo[source].modified, "Picker lost unsaved edits")
	assert(vim.api.nvim_buf_get_lines(source, 7, 8, false)[1] == "local unsaved_change = 8")
	vim.api.nvim_buf_set_lines(source, 0, -1, false, { "local shortened = true" })
	keys(",cf")
	wait(function()
		return vim.bo.buftype == "terminal"
			and table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n"):find("sample.lua", 1, true)
	end, "Picker did not reopen for the shortened unsaved buffer")
	select("sample.lua", "local shortened = true", {})
	vim.api.nvim_chan_send(vim.bo.channel, "\r")
	wait(function()
		return vim.api.nvim_get_current_buf() == source
	end, "Shortened unsaved buffer was not selected")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 1, "Disk hunk jumped past the shortened unsaved buffer")
	fzf.fzf_exec({ "cleanup" }, { previewer = false, no_hide = true })
	wait(function()
		return vim.bo.buftype == "terminal"
			and table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n"):find("cleanup", 1, true)
	end, "Cleanup picker did not become ready")
	wait(function()
		for buf in pairs(previews) do
			if vim.api.nvim_buf_is_valid(buf) or require("gitsigns.cache").cache[buf] then
				return false
			end
		end
		return true
	end, "Discarding the picker retained scratch buffers or Git attachments")
	vim.api.nvim_chan_send(vim.bo.channel, "\3")
	wait(function()
		return vim.api.nvim_get_current_buf() == source and not fzf.utils.fzf_winobj()
	end, "Cleanup picker did not close")
	print("Changed files: native syntax, Git sign layers, status prefixes, selection and cleanup passed")
end
local ok, err = xpcall(workflow, debug.traceback)
fzf.win.unhide()
if vim.bo.buftype == "terminal" then
	vim.api.nvim_chan_send(vim.bo.channel, "\3")
	vim.wait(1000, function()
		return not fzf.utils.fzf_winobj()
	end, 10)
end
fzf.win.close()
vim.cmd("silent! %bwipeout!")
vim.fn.delete(repo, "rf")
if not ok then
	io.stderr:write(err .. "\n")
	vim.cmd.cquit(1)
end
vim.cmd("qa!")
