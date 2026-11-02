-- One workflow through the mapped picker, installed fzf, Git and preview renderer.
-- nvim --headless -u NONE -i NONE -n -l nvim/tests/worktree-picker.lua
local checkout = vim.fn.getcwd()
vim.opt.rtp:prepend(checkout .. "/nvim")
local plugins = vim.fn.stdpath("data") .. "/lazy/"
vim.opt.rtp:append(plugins .. "fzf-lua")
vim.opt.rtp:append(plugins .. "nvim-web-devicons")
vim.g.mapleader = " "
vim.env.TERM = "xterm-256color"
require("fzfconfig")

-- Observe the real fzf input; selected entries have their ANSI codes stripped.
local rows = {}
local fzf = require("fzf-lua")
local execute = fzf.fzf_exec
fzf.fzf_exec = function(contents, opts)
	return execute(function(cb)
		rows = {}
		return contents(function(entry, ...)
			if entry then
				table.insert(rows, entry)
			end
			return cb(entry, ...)
		end)
	end, opts)
end

local temporary = vim.fn.tempname()
vim.opt.rtp:append(plugins .. "vim-obsession")
vim.opt.rtp:append(plugins .. "vim-prosession")
vim.g.prosession_dir = temporary .. "/sessions/"
vim.g.prosession_on_startup = 0
vim.g.prosession_per_branch = 1
vim.cmd("runtime plugin/obsession.vim")
vim.cmd("runtime plugin/prosession.vim")
local repo = temporary .. "/repo with spaces"
local linked = repo .. "/.worktrees/task $(touch escaped)"
local codex = temporary .. "/codex-worktrees/session/repo with spaces"
vim.fn.mkdir(repo, "p")
local fixture_date = "2001-01-01T00:00:00Z"
local function git(path, ...)
	local result = vim.system(vim.list_extend({ "git", "-C", path }, { ... }), {
		text = true,
		env = {
			GIT_AUTHOR_DATE = fixture_date,
			GIT_COMMITTER_DATE = fixture_date,
			GIT_CONFIG_GLOBAL = "/dev/null",
			GIT_CONFIG_NOSYSTEM = "1",
		},
	}):wait()
	assert(result.code == 0, result.stderr)
	return vim.trim(result.stdout)
end
local function picker()
	return require("fzf-lua").utils.fzf_winobj()
end
local function terminal()
	local win = picker()
	if not win or not vim.api.nvim_buf_is_valid(win.fzf_bufnr) then
		return ""
	end
	return table.concat(vim.api.nvim_buf_get_lines(win.fzf_bufnr, 0, -1, false), "\n")
end
local function preview()
	local win = picker()
	if not win or not win:validate_preview() then
		return ""
	end
	return table.concat(vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(win.preview_winid), 0, -1, false), "\n")
end
local function send(keys)
	vim.api.nvim_chan_send(vim.b[picker().fzf_bufnr].terminal_job_id, keys)
end
local function wait_for(predicate, message)
	if not vim.wait(10000, predicate, 20) then
		error(message .. "\nResults:\n" .. terminal() .. "\nPreview:\n" .. preview())
	end
end
local function workflow()
	git(repo, "init", "-b", "main")
	git(repo, "config", "user.name", "Test")
	git(repo, "config", "user.email", "test@example.invalid")
	git(repo, "config", "color.status", "auto")
	-- A long file list must not crowd commits and summaries out of the preview.
	vim.fn.mkdir(repo .. "/bulk", "p")
	for file = 1, 12 do
		vim.fn.writefile({ "baseline" }, string.format("%s/bulk/change%02d.txt", repo, file))
	end
	vim.fn.writefile({ "baseline" }, repo .. "/sample file.txt")
	git(repo, "add", ".")
	git(repo, "commit", "-m", "baseline")
	git(repo, "worktree", "add", "-b", "feature/work", linked)
	vim.fn.writefile({ "branch change" }, linked .. "/committed.txt")
	for file = 1, 12 do
		vim.fn.writefile({ "committed" }, string.format("%s/bulk/change%02d.txt", linked, file))
	end
	git(linked, "add", ".")
	git(linked, "commit", "-m", "branch change")
	git(linked, "mv", "sample file.txt", "renamed file.txt")
	for file = 1, 12 do
		vim.fn.writefile({ "staged" }, string.format("%s/bulk/change%02d.txt", linked, file))
	end
	git(linked, "add", "bulk")
	for file = 1, 12 do
		vim.fn.writefile({ "unstaged" }, string.format("%s/bulk/change%02d.txt", linked, file))
	end
	vim.fn.writefile({ "unstaged" }, linked .. "/renamed file.txt")
	vim.fn.writefile({ "untracked" }, linked .. "/new file.txt")
	fixture_date = "2002-01-01T00:00:00Z"
	git(repo, "worktree", "add", "--detach", codex, "main")
	vim.cmd.cd(codex)
	vim.cmd("ProsessionReset")
	vim.cmd.edit(vim.fn.fnameescape(codex .. "/sample file.txt"))
	local codex_session = vim.g.this_obsession
	vim.cmd.cd(linked)
	vim.cmd("ProsessionReset")
	vim.cmd.edit(vim.fn.fnameescape(linked .. "/renamed file.txt"))
	vim.cmd.vsplit(vim.fn.fnameescape(linked .. "/committed.txt"))
	local linked_session = vim.g.this_obsession
	assert(codex_session ~= linked_session, "Worktrees share a session")
	vim.o.columns, vim.o.lines = 240, 50
	vim.fn.maparg(" gw", "n", false, true).callback()
	wait_for(function()
		return picker() and picker().fzf_bufnr
	end, "Picker did not open")
	picker():hide()
	require("fzf-lua").resume()
	wait_for(function()
		return terminal():find("S13 M13 ?1", 1, true)
			and preview():find("branch change", 1, true)
			and picker()._previewer.loaded_entry
			and preview():find("Branch diff vs primary", 1, true)
			and preview():find("13 files changed", 1, true)
	end, "Picker did not render worktree changes and commit preview:\n" .. terminal() .. "\n" .. preview())
	local text = terminal()
	assert(text:find("local/t", 1, true) and text:find("touch escaped)", 1, true), text)
	assert(text:find("codex/session", 1, true), text)
	assert(text:find("primary", 1, true), text)
	assert(text:find("GIT AGE", 1, true), text)
	assert(text:find(math.floor((os.time() - 978307200) / (365 * 86400)) .. "y", 1, true), text)
	assert(text:find("↑1 ↓0", 1, true), text)
	assert(not text:find(temporary, 1, true), "Repeated absolute base path in rows")
	assert(text:find("detached@", 1, true) < text:find("main  ", 1, true), "Other checkouts are not newest first")
	assert(preview():find("bulk/change01.txt", 1, true), preview())
	assert(preview():find("Branch diff vs primary", 1, true), preview())
	assert(preview():find("13 files changed", 1, true), preview())
	local output = vim.system(picker()._previewer.loaded_entry.cmd, { text = true }):wait()
	assert(output.code == 0, output.stderr)
	local hash = git(linked, "rev-parse", "--short", "HEAD")
	assert(output.stdout:match("\27%[[%d;]+m" .. hash), "Commit hash lost its ANSI color in the terminal preview")
	local status = assert(output.stdout:match("Working tree.-\n(.-)\27%[1;36mRecent commits"), output.stdout)
	assert(status:match("\27%[[%d;]+mM"), "Git status lost its ANSI color when piped")
	local plain_status = status:gsub("\27%[[%d;]*m", "")
	local _, shown = plain_status:gsub("\n[ MADRCU?!][ MADRCU?!] ", "")
	local omitted = tonumber(plain_status:match("(%d+) more files"))
	assert(shown >= 1 and shown <= 5 and omitted and shown + omitted == 14, plain_status)
	assert(not preview():find("\27", 1, true), "Preview displayed ANSI escapes instead of interpreting them")
	assert(not vim.uv.fs_stat(linked .. "/escaped"), "Preview executed part of a worktree path")
	local current_preview = picker()._previewer._last_entry
	assert(current_preview:find("● feature/work", 1, true), "Current worktree was not first")
	local input = table.concat(rows, "\n")
	assert(input:find("\27[32mS13\27[0m", 1, true), "Staged count lost its green color")
	assert(input:find("\27[33mM13\27[0m", 1, true), "Unstaged count lost its yellow color")
	assert(input:find("\27[36m?1\27[0m", 1, true), "Untracked count lost its cyan color")
	assert(input:find("\27[32mclean\27[0m", 1, true), "Clean checkout lost its green color")
	assert(not text:find("\27", 1, true), "Results displayed ANSI escapes instead of interpreting them")
	local function layout()
		local win = picker()
		return vim.api.nvim_win_get_config(win.fzf_winid), vim.api.nvim_win_get_config(win.preview_winid)
	end
	local list, detail = layout()
	assert(detail.col > list.col, "Wide window must put preview beside results")
	vim.o.columns = 100
	vim.api.nvim_exec_autocmds("VimResized", {})
	wait_for(function()
		list, detail = layout()
		return detail.row > list.row and detail.col == list.col
	end, "Narrow window did not move preview below results")
	wait_for(function()
		return preview():find("branch change", 1, true) and preview():find("13 files changed", 1, true)
	end, "Narrow preview lost its commits or diff totals")
	local viewport = vim.api.nvim_win_call(picker().preview_winid, function()
		return { vim.fn.line("w0"), vim.fn.line("w$") }
	end)
	local visible = table.concat(
		vim.api.nvim_buf_get_lines(
			vim.api.nvim_win_get_buf(picker().preview_winid),
			viewport[1] - 1,
			viewport[2],
			false
		),
		"\n"
	)
	assert(visible:find("branch change", 1, true), "Recent commits are not visible below the limited status list")
	vim.o.columns = 240
	vim.api.nvim_exec_autocmds("VimResized", {})
	wait_for(function()
		list, detail = layout()
		return detail.col > list.col
	end, "Preview did not recover after widening")
	send("\21codex/session")
	wait_for(function()
		return preview():find("codex-worktrees", 1, true)
	end, "Filtering did not preview the selected detached worktree")
	send("\r")
	wait_for(function()
		return vim.uv.fs_realpath(vim.fn.getcwd()) == vim.uv.fs_realpath(codex)
	end, "Selection did not switch to the exact worktree path")
	assert(vim.g.this_obsession == codex_session, "Selection did not restore the destination session")
	assert(vim.api.nvim_buf_get_name(0) == codex .. "/sample file.txt", "Destination buffer was not restored")
	assert(#vim.api.nvim_tabpage_list_wins(0) == 1, "Previous worktree windows leaked into the destination")
	require("fzf-lua").resume()
	wait_for(function()
		local win = picker()
		local entry = win and win._previewer and win._previewer._last_entry
		return entry and entry:find("● detached@", 1, true)
	end, "Resumed picker did not open")
	send("\21")
	wait_for(function()
		local win = picker()
		local entry = win and win._previewer and win._previewer._last_entry
		return terminal():find("S13 M13 ?1", 1, true) and entry and entry:find("● detached@", 1, true)
	end, "Resuming lost the worktree list")
	send("\21feature/work")
	wait_for(function()
		return preview():find(linked, 1, true)
	end, "Filtering did not select the original worktree")
	send("\r")
	wait_for(function()
		return vim.g.this_obsession == linked_session
	end, "Returning did not restore the original session")
	assert(vim.fn.getcwd() == linked, "Returning restored the wrong working directory")
	assert(vim.api.nvim_buf_get_name(0) == linked .. "/committed.txt", "Original active buffer was not restored")
	assert(#vim.api.nvim_tabpage_list_wins(0) == 2, "Original split layout was not restored")
	vim.api.nvim_buf_set_lines(0, 0, -1, false, { "unsaved edit" })
	require("fzf-lua").resume()
	wait_for(function()
		return terminal():find("feature/work", 1, true)
	end, "Picker did not reopen with unsaved edits")
	send("\21codex/session")
	wait_for(function()
		return preview():find("codex-worktrees", 1, true)
	end, "Filtering did not select the other worktree with unsaved edits")
	send("\r")
	wait_for(function()
		return not picker()
	end, "Blocked selection did not close the picker")
	assert(vim.fn.getcwd() == linked and vim.g.this_obsession == linked_session, "Unsaved edit did not block switching")
	assert(vim.bo.modified and vim.api.nvim_get_current_line() == "unsaved edit", "Switching discarded unsaved edits")
	vim.bo.modified = false
	require("fzf-lua").resume()
	wait_for(function()
		return terminal():find("detached@", 1, true)
	end, "Picker did not reopen after blocked selection")
	send("\3")
	wait_for(function()
		return not picker()
	end, "Cancel did not close the picker")
	require("fzf-lua").resume()
	wait_for(function()
		return terminal():find("detached@", 1, true)
	end, "Picker did not reopen after cancel")
	send("\21")
	wait_for(function()
		return terminal():find("S13 M13 ?1", 1, true)
	end, "Cancel then resume left the picker empty")
	print("Worktree picker: previews, session switching, restored layouts and unsaved edit protection passed")
end

local ok, err = xpcall(workflow, debug.traceback)
require("fzf-lua").win.close()
vim.cmd("Obsession")
vim.cmd.cd(checkout)
vim.fn.delete(temporary, "rf")
if not ok then
	io.stderr:write(err .. "\n")
end
-- In -l mode fzf-lua's persistent RPC server keeps Neovim's loop alive.
-- The picker and fixture are already closed; exit this isolated test process.
os.exit(ok and 0 or 1)
