-- nvim --headless -u NONE -i NONE -n -l nvim/tests/git-signs.lua
local checkout = vim.fn.getcwd()
vim.opt.rtp:append(checkout .. "/nvim")
vim.opt.rtp:append(vim.fn.stdpath("data") .. "/lazy/gitsigns.nvim")
local repo = vim.fn.tempname()
vim.fn.mkdir(repo, "p")
local function git(...)
	local result = vim.system(vim.list_extend({ "git", "-C", repo }, { ... }), { text = true }):wait()
	assert(result.code == 0, result.stderr)
	return vim.trim(result.stdout)
end
local function write(lines)
	vim.fn.writefile(lines, repo .. "/sample.txt")
end
local function workflow()
	git("init", "-b", "main")
	git("config", "user.name", "Test")
	git("config", "user.email", "test@example.invalid")
	local lines = { "one", "two", "three", "four", "five", "six", "seven", "eight", "nine" }
	for line = 10, 300 do
		lines[line] = "line " .. line
	end
	write(lines)
	git("add", ".")
	git("commit", "-m", "baseline")
	git("update-ref", "refs/remotes/origin/main", "HEAD")
	git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
	git("switch", "-c", "feature")
	lines[2] = "committed"
	lines[100] = "committed far away"
	lines[200] = "another committed change"
	write(lines)
	git("commit", "-am", "branch change")
	lines[5] = "staged"
	write(lines)
	git("add", ".")
	lines[8] = "unstaged"
	lines[100] = "line 100" -- Revert a committed change, leaving no branch sign.
	write(lines)
	vim.cmd.cd(repo)
	require("gitsignsconfig")
	vim.cmd.edit(repo .. "/sample.txt")
	local buf = vim.api.nvim_get_current_buf()
	local function signs()
		local result = {}
		for _, marks in pairs(vim.api.nvim_get_namespaces()) do
			for _, mark in ipairs(vim.api.nvim_buf_get_extmarks(buf, marks, 0, -1, { details = true })) do
				local detail = mark[4]
				if detail.sign_hl_group then
					local line = mark[2] + 1
					if not result[line] or detail.priority > result[line].priority then
						result[line] = detail
					end
				end
			end
		end
		return result
	end
	local function expect(expected)
		assert(
			vim.wait(5000, function()
				local actual = signs()
				for line, group in pairs(expected) do
					if not actual[line] or actual[line].sign_hl_group ~= group then
						return false
					end
				end
				return true
			end, 20),
			vim.inspect(signs())
		)
	end
	expect({
		[2] = "GitSignsStagedChange",
		[5] = "GitSignsStagedChange",
		[8] = "GitSignsChange",
		[200] = "GitSignsStagedChange",
	})
	assert(
		vim.wait(5000, function()
			for _, hunk in ipairs(require("gitsigns").get_hunks(buf) or {}) do
				if hunk.added.start == 100 then
					return true
				end
			end
		end, 20),
		"offscreen unstaged change must be ready"
	)
	vim.api.nvim_win_set_cursor(0, { 1, 0 })
	vim.cmd.normal("]c")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 2, "next committed change")
	vim.cmd.normal("]c")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 5, "next staged change")
	vim.cmd.normal("]c")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 8, "next unstaged change")
	vim.cmd.normal("]c")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 100, "next offscreen reverted committed change")
	vim.cmd.normal("]c")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 200, "next offscreen committed change")
	vim.cmd.normal("[c")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 100, "previous reverted committed change")
	vim.cmd.normal("[c")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 8, "previous unstaged change")
	vim.cmd.normal("[c")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 5, "previous staged change")
	vim.cmd.normal("[c")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 2, "previous committed change")
	-- Editing over a committed change must make its sign bright.
	vim.api.nvim_buf_set_lines(buf, 1, 2, false, { "edited again" })
	vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf })
	expect({ [2] = "GitSignsChange", [5] = "GitSignsStagedChange", [8] = "GitSignsChange" })
	vim.cmd.write()
	git("add", ".")
	git("commit", "-m", "remaining changes")
	vim.api.nvim_exec_autocmds("FocusGained", { buffer = buf })
	expect({ [2] = "GitSignsStagedChange", [5] = "GitSignsStagedChange", [8] = "GitSignsStagedChange" })
	assert(
		vim.api.nvim_get_hl(0, { name = "GitSignsChange" }).fg
			~= vim.api.nvim_get_hl(0, { name = "GitSignsStagedChange" }).fg
	)
	print("Git gutter workflow passed")
end
local ok, err = xpcall(workflow, debug.traceback)
vim.cmd("silent! %bwipeout!")
vim.fn.delete(repo, "rf")
if not ok then
	error(err)
end
