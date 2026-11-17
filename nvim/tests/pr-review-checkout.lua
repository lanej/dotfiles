-- One optional-checkout workflow using installed ghlite/fzf and a temporary Git remote.
-- nvim --headless -u NONE -i NONE -n -l nvim/tests/pr-review-checkout.lua
local checkout = vim.fn.getcwd()
local temporary = vim.fn.tempname()
local repo = temporary .. "/clone with spaces"
local remote
vim.fn.mkdir(temporary .. "/bin", "p")
vim.fn.mkdir(repo, "p")
vim.fn.writefile({ "[features]", "nvim_ghlite = true" }, temporary .. "/dotfiles.toml")
vim.env.DOTFILES_CONFIG = temporary .. "/dotfiles.toml"
temporary = assert(vim.uv.fs_realpath(temporary))
repo, remote = temporary .. "/clone with spaces", temporary .. "/remote.git"
local real_git = vim.fn.exepath("git")
local function git(path, ...)
	local result = vim.system(vim.list_extend({ real_git, "-C", path }, { ... }), {
		text = true,
		env = { GIT_CONFIG_GLOBAL = "/dev/null", GIT_CONFIG_NOSYSTEM = "1" },
	}):wait()
	assert(result.code == 0, result.stderr)
	return vim.trim(result.stdout)
end
git(repo, "init", "-b", "main")
git(repo, "config", "user.name", "Test")
git(repo, "config", "user.email", "test@example.invalid")
vim.fn.writefile({ ".worktrees/", "artifact.log" }, repo .. "/.gitignore")
vim.fn.writefile({ "baseline" }, repo .. "/sample.txt")
git(repo, "add", ".")
git(repo, "commit", "-m", "baseline")
local head = git(repo, "rev-parse", "HEAD")
vim.fn.writefile({ head }, temporary .. "/head")
vim.fn.mkdir(remote, "p")
git(remote, "init", "--bare")
git(repo, "push", remote, "HEAD:refs/pull/1/head")
git(repo, "remote", "add", "origin", "https://github.com/reviewer/fork.git")
git(repo, "remote", "add", "upstream", "git@github.com:example/repo.git")
vim.fn.writefile({ "original dirty content" }, repo .. "/sample.txt")
vim.fn.writefile({ "original untracked content" }, repo .. "/notes.txt")
local before = git(repo, "status", "--short", "--untracked-files=all")

vim.opt.rtp:prepend(checkout .. "/nvim")
local plugins = vim.fn.stdpath("data") .. "/lazy/"
for _, name in ipairs({ "fzf-lua", "nvim-web-devicons", "ghlite.nvim", "async.nvim" }) do
	local pinned = vim.env.PR_REVIEW_PLUGIN_ROOT
	vim.opt.rtp:append(
		pinned and (name == "fzf-lua" or name == "ghlite.nvim" or name == "async.nvim") and pinned .. "/" .. name
			or plugins .. name
	)
end
vim.env.PR_REVIEW_FIXTURE = temporary
vim.env.XDG_STATE_HOME = temporary .. "/state"
vim.env.XDG_CACHE_HOME = temporary .. "/cache"
vim.fn.mkdir(temporary .. "/cache/nvim", "p")
vim.fn.writefile({ "normal" }, temporary .. "/mode")
vim.fn.writefile({
	"#!/bin/sh",
	"exec " .. vim.fn.shellescape(vim.fn.exepath("uv")) .. " run --no-project " .. vim.fn.shellescape(
		checkout .. "/nvim/tests/fixtures/pr-review-gh.py"
	) .. ' "$@"',
}, temporary .. "/bin/gh")
-- Only fetching this controlled clone is redirected; all Git mechanics are real.
vim.fn.writefile({
	"#!/bin/sh",
	'if [ "$1" = "-C" ] && [ "$2" = ' .. vim.fn.shellescape(repo) .. ' ] && [ "$3" = "fetch" ]; then',
	"  exec "
		.. vim.fn.shellescape(real_git)
		.. " -C "
		.. vim.fn.shellescape(repo)
		.. " fetch --no-tags "
		.. vim.fn.shellescape(remote)
		.. " refs/pull/1/head",
	"fi",
	"exec " .. vim.fn.shellescape(real_git) .. ' "$@"',
}, temporary .. "/bin/git")
vim.fn.setfperm(temporary .. "/bin/gh", "rwx------")
vim.fn.setfperm(temporary .. "/bin/git", "rwx------")
-- The fixture lives under /tmp; inaccessible VM tracefs is unrelated to its file holders.
if vim.fn.has("linux") == 1 then
	local lsof = vim.fn.exepath("lsof")
	vim.fn.writefile(
		{ "#!/bin/sh", "exec " .. vim.fn.shellescape(lsof) .. ' -e /sys/kernel/debug/tracing "$@"' },
		temporary .. "/bin/lsof"
	)
	vim.fn.setfperm(temporary .. "/bin/lsof", "rwx------")
end
vim.env.PATH = temporary .. "/bin:" .. vim.env.PATH
vim.g.mapleader = ","
vim.o.columns, vim.o.lines = 180, 50
local messages = {}
vim.notify = function(message)
	messages[#messages + 1] = message
end
require("fzf-lua").setup({ fzf_bin = "fzf" })
require("pr-review-ghlite").setup()
require("pr-reviews").setup()
local function wait_for(predicate, message)
	if not vim.wait(15000, predicate, 20) then
		local win = require("fzf-lua").utils.fzf_winobj()
		local text = win and table.concat(vim.api.nvim_buf_get_lines(win.fzf_bufnr, 0, -1, false), "\n") or ""
		error(
			message
				.. "\n"
				.. table.concat(messages, "\n")
				.. "\nBuffer: "
				.. vim.api.nvim_buf_get_name(0)
				.. "\n"
				.. text
		)
	end
end
local function picker()
	return require("fzf-lua").utils.fzf_winobj()
end
local destination = repo .. "/.worktrees/pr-review-1-" .. head:sub(1, 12)
local holder
local function cleanup()
	vim.ui.select = function(_, _, callback)
		callback(destination)
	end
	vim.cmd.PRReviewCleanup()
end
local function workflow()
	require("pr-reviews").open({
		id = "PR1",
		number = 1,
		headRefOid = head,
		repository = { nameWithOwner = "example/repo" },
	})
	wait_for(function()
		return vim.api.nvim_buf_get_name(0):find("PR View: 1", 1, true)
			and vim.fn.maparg(",ol", "n", false, true).callback
	end, "ghlite description did not open")
	local original_tabs = #vim.api.nvim_list_tabpages()
	vim.cmd("PRReviewCheckout " .. vim.fn.fnameescape(repo))
	wait_for(function()
		local win = picker()
		return win
			and vim.uv.fs_stat(destination)
			and table.concat(vim.api.nvim_buf_get_lines(win.fzf_bufnr, 0, -1, false), "\n"):find("sample.txt", 1, true)
	end, "Checkout did not open the detached worktree and files picker")
	assert(git(repo, "branch", "--show-current") == "main", "Original branch switched")
	assert(git(repo, "status", "--short", "--untracked-files=all") == before, "Original dirty files changed")
	assert(
		git(destination, "rev-parse", "HEAD") == head and git(destination, "branch", "--show-current") == "",
		"Worktree is not detached at selected head"
	)
	assert(vim.uv.fs_realpath(vim.fn.getcwd()) == destination, "Current tab did not receive the review cwd")
	vim.api.nvim_chan_send(vim.b[picker().fzf_bufnr].terminal_job_id, "sample")
	wait_for(function()
		local win = picker()
		local text = table.concat(vim.api.nvim_buf_get_lines(win.fzf_bufnr, 0, -1, false), "\n")
		return text:find("sample.txt", 1, true) and not text:find(".gitignore", 1, true)
	end, "Files picker did not finish filtering")
	vim.api.nvim_chan_send(vim.b[picker().fzf_bufnr].terminal_job_id, "\r")
	wait_for(function()
		return vim.api.nvim_buf_get_name(0) == destination .. "/sample.txt"
	end, "Files picker did not open the local file")
	require("fzf-lua").win.close()
	assert(
		vim.t.pr_review_id == "PR1" and vim.fn.maparg(",rq", "n", false, true).callback,
		"Local file selection lost review association"
	)
	cleanup()
	wait_for(function()
		return table.concat(messages, "\n"):find("active tab", 1, true)
	end, "Cleanup removed active local review")
	vim.fn.maparg(",rs", "n", false, true).callback()
	wait_for(function()
		return require("ghlite.state").pending_reviews[1]
	end, "Starting from detached local files did not start the selected pending review")
	assert(#vim.api.nvim_list_tabpages() == original_tabs, "Detached review opened an extra tab")
	assert(not vim.wo.diff, "Detached review enabled a diff layout")
	local local_buffer = vim.api.nvim_get_current_buf()
	vim.fn.maparg(",oc", "n", false, true).callback()
	wait_for(function()
		return vim.api.nvim_buf_get_name(0):find("PR comment", 1, true)
	end, "Fork checkout did not open the inline feedback editor")
	vim.api.nvim_buf_set_lines(0, 1, -1, false, { "Feedback from the upstream checkout" })
	vim.fn.maparg("<C-s>", "n", false, true).callback()
	wait_for(function()
		return vim.uv.fs_stat(temporary .. "/inline-saved") and vim.api.nvim_get_current_buf() == local_buffer
	end, "Inline feedback from the fork checkout was not saved")
	local saved = vim.json.decode(table.concat(vim.fn.readfile(temporary .. "/inline-saved"), "\n"))
	assert(saved.path == "sample.txt" and saved.reviewId == "REVIEW1", "Feedback lost its path or pending review")
	git(repo, "remote", "set-url", "upstream", "https://github.com/another/project.git")
	git(repo, "remote", "set-url", "--push", "upstream", "https://github.com/example/repo.git")
	assert(not require("pr-review-ghlite").checked_out(), "Matching only a push remote accepted another repository")
	git(repo, "remote", "set-url", "upstream", "git@github.com:example/repo.git")
	local session = require("pr-review-ghlite").current()
	session.head = string.rep("0", 40)
	assert(not require("pr-review-ghlite").checked_out(), "Matching upstream accepted a different PR revision")
	session.head = head
	assert(require("pr-review-ghlite").checked_out(), "Restoring the matching upstream and head did not restore review")
	vim.fn.writefile({ "valuable" }, destination .. "/artifact.log")
	vim.cmd.enew()
	vim.cmd("tcd " .. vim.fn.fnameescape(repo))
	vim.api.nvim_buf_delete(local_buffer, { force = false })
	cleanup()
	wait_for(function()
		return table.concat(messages, "\n"):find("ignored artifacts", 1, true)
	end, "Ignored artifacts were not retained")
	assert(vim.uv.fs_stat(destination .. "/artifact.log"), "Valuable artifact was deleted")
	vim.fn.delete(destination .. "/artifact.log")
	vim.fn.writefile({ "reviewer change" }, destination .. "/sample.txt")
	cleanup()
	wait_for(function()
		return table.concat(messages, "\n"):find("uncommitted work", 1, true)
	end, "Dirty worktree was not retained")
	git(destination, "restore", "sample.txt")
	holder = vim.system({
		vim.fn.exepath("uv"),
		"run",
		"--no-project",
		"python",
		"-c",
		"import pathlib, sys\nwith open(sys.argv[1]) as held:\n"
			.. "    pathlib.Path(sys.argv[2]).write_text('ready')\n    sys.stdin.read()\n",
		destination .. "/sample.txt",
		temporary .. "/holder-ready",
	}, { cwd = temporary, stdin = true, text = true })
	wait_for(function()
		return vim.uv.fs_stat(temporary .. "/holder-ready")
	end, "Reader did not hold a worktree file open")
	cleanup()
	wait_for(function()
		return table.concat(messages, "\n"):find("active process or incomplete process inspection", 1, true)
	end, "Cleanup did not retain a worktree file held open from another directory")
	assert(vim.uv.fs_stat(destination), "In-use worktree was removed")
	holder:write(nil)
	assert(holder:wait().code == 0, "Reader did not exit")
	holder = nil
	cleanup()
	wait_for(function()
		return not vim.uv.fs_stat(destination)
	end, "Safe cleanup did not remove owned worktree")
	assert(
		git(repo, "rev-parse", "refs/heads/review/pr-1-" .. head:sub(1, 12)) == head,
		"Cleanup lost the detached commit"
	)
	assert(
		git(repo, "branch", "--show-current") == "main"
			and git(repo, "status", "--short", "--untracked-files=all") == before,
		"Cleanup changed original work"
	)
	assert(not git(repo, "worktree", "list", "--porcelain"):find(destination, 1, true), "Cleanup left a registration")
	print(
		"PR checkout workflow passed: fork origin with matching upstream, inline feedback, exact revision, original dirty files and safe cleanup"
	)
end
local ok, err = xpcall(workflow, debug.traceback)
if holder then
	holder:write(nil)
	holder:wait()
end
require("fzf-lua").win.close()
vim.cmd.cd(checkout)
if vim.uv.fs_stat(destination) then
	git(destination, "restore", "sample.txt")
	vim.fn.delete(destination .. "/artifact.log")
	git(repo, "worktree", "remove", destination)
end
vim.fn.delete(temporary, "rf")
if not ok then
	io.stderr:write(err .. "\n")
	vim.cmd("cquit 1")
end
vim.cmd("qa!")
