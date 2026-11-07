-- One optional-checkout workflow using installed Octo/fzf and a temporary Git remote.
-- nvim --headless -u NONE -i NONE -n -l nvim/tests/pr-review-checkout.lua
local checkout = vim.fn.getcwd()
local temporary = vim.fn.tempname()
local repo, remote = temporary .. "/clone with spaces", temporary .. "/remote.git"
vim.fn.mkdir(temporary .. "/bin", "p")
vim.fn.mkdir(repo, "p")
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
git(repo, "remote", "add", "origin", "https://github.com/example/repo.git")
vim.fn.writefile({ "original dirty content" }, repo .. "/sample.txt")
vim.fn.writefile({ "original untracked content" }, repo .. "/notes.txt")
local before = git(repo, "status", "--short", "--untracked-files=all")

vim.opt.rtp:prepend(checkout .. "/nvim")
local plugins = vim.fn.stdpath("data") .. "/lazy/"
for _, name in ipairs({ "fzf-lua", "nvim-web-devicons", "plenary.nvim", "octo.nvim" }) do
	local pinned = vim.env.PR_REVIEW_PLUGIN_ROOT
	vim.opt.rtp:append(
		pinned and (name == "fzf-lua" or name == "octo.nvim") and pinned .. "/" .. name or plugins .. name
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
vim.env.PATH = temporary .. "/bin:" .. vim.env.PATH
vim.g.mapleader, vim.g.octo_viewer = ",", "reviewer"
vim.o.columns, vim.o.lines = 180, 50
local messages = {}
vim.notify = function(message)
	messages[#messages + 1] = message
end
require("fzf-lua").setup({ fzf_bin = "fzf" })
require("octo").setup({ picker = "fzf-lua", default_to_projects_v2 = false, gh_env = { PR_REVIEW_FIXTURE = temporary } })
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
		local buffer = require("octo.utils").get_current_buffer()
		return buffer and buffer.ready
	end, "Octo description did not open")
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
	assert(vim.uv.fs_realpath(vim.fn.getcwd()) == destination, "Local tab did not receive its own cwd")
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
		"Local file selection lost remote review association"
	)
	cleanup()
	wait_for(function()
		return table.concat(messages, "\n"):find("active tab", 1, true)
	end, "Cleanup removed active local review")
	local local_tab = vim.api.nvim_get_current_tabpage()
	vim.fn.maparg(",rs", "n", false, true).callback()
	wait_for(function()
		local review = require("octo.reviews").get_current_review()
		return review and review.id == "REVIEW1" and review.layout.files[1]
	end, "Starting from detached local files did not open the selected remote review")
	local review = require("octo.reviews").get_current_review()
	assert(review.pull_request.id == "PR1", "Local files started another PR's review")
	review.layout:close()
	vim.api.nvim_set_current_tabpage(local_tab)
	vim.fn.writefile({ "valuable" }, destination .. "/artifact.log")
	local local_buffer = vim.api.nvim_get_current_buf()
	vim.cmd("tabclose")
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
		"PR checkout workflow passed: detached revision, local tab association, original dirty files and safe retention/cleanup"
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
