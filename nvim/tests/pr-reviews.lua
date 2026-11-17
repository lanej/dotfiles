-- One workflow through the full configuration, launcher, picker, ghlite and gh.
-- nvim --headless -u NONE -i NONE -n -l nvim/tests/pr-reviews.lua
local checkout = vim.fn.getcwd()
local temporary = vim.env.PR_REVIEW_FIXTURE or vim.fn.tempname()
if not vim.env.PR_REVIEW_TEST_CHILD then
	vim.fn.mkdir(temporary .. "/bin", "p")
	vim.fn.mkdir(temporary .. "/cache/nvim", "p")
	vim.fn.mkdir(temporary .. "/config", "p")
	vim.fn.writefile({ "[features]", "nvim_ghlite = true" }, temporary .. "/dotfiles.toml")
	assert(vim.uv.fs_symlink(checkout .. "/nvim", temporary .. "/config/nvim"))
	vim.fn.writefile(vim.fn.readfile(checkout .. "/nvim/lazy-lock.json"), temporary .. "/lazy-lock.json")
	vim.fn.writefile({ "normal" }, temporary .. "/mode")
	vim.fn.writefile({
		"#!/bin/sh",
		"exec " .. vim.fn.shellescape(vim.fn.exepath("uv")) .. " run --no-project " .. vim.fn.shellescape(
			checkout .. "/nvim/tests/fixtures/pr-review-gh.py"
		) .. ' "$@"',
	}, temporary .. "/bin/gh")
	vim.fn.setfperm(temporary .. "/bin/gh", "rwx------")
	vim.fn.writefile({ "#!/bin/sh", "exit 1" }, temporary .. "/bin/tmux")
	vim.fn.setfperm(temporary .. "/bin/tmux", "rwx------")
	for _, config in ipairs({ {}, { "[features]", "nvim_ghlite = false" } }) do
		vim.fn.writefile(config, temporary .. "/default.toml")
		local fallback = vim.system({
			vim.fn.exepath("nvim"),
			"--headless",
			"-u",
			checkout .. "/nvim/init.lua",
			"-i",
			"NONE",
			"-n",
			"--cmd",
			"let g:prosession_on_startup = 0",
			"-c",
			"lua dofile(" .. vim.inspect(checkout .. "/nvim/tests/pr-review-octo.lua") .. ")",
		}, {
			text = true,
			env = {
				PR_REVIEW_FIXTURE = temporary,
				PATH = temporary .. "/bin:" .. vim.env.PATH,
				XDG_STATE_HOME = temporary .. "/state",
				XDG_CACHE_HOME = temporary .. "/cache",
				XDG_CONFIG_HOME = temporary .. "/config",
				DOTFILES_CONFIG = temporary .. "/default.toml",
				DOTFILES_NVIM_BOOTSTRAP_LOCK = temporary .. "/lazy-lock.json",
				TMUX = "",
				TMUX_PANE = "",
			},
		}):wait(60000)
		io.stdout:write(fallback.stdout or "")
		io.stderr:write(fallback.stderr or "")
		if fallback.code ~= 0 then
			vim.fn.delete(temporary, "rf")
			vim.cmd("cquit 1")
			return
		end
	end
	for _, file in ipairs({ "attempts", "requests", "pending-review" }) do
		vim.fn.delete(temporary .. "/" .. file)
	end
	vim.fn.writefile(vim.fn.readfile(checkout .. "/nvim/lazy-lock.json"), temporary .. "/lazy-lock.json")
	local result = vim.system({
		checkout .. "/bin/nvim-gh-review",
		"--headless",
		"-u",
		checkout .. "/nvim/init.lua",
		"-i",
		"NONE",
		"-n",
		"--cmd",
		"lua vim.opt.rtp:remove(vim.fn.stdpath('config')); "
			.. "vim.opt.rtp:remove(vim.fn.stdpath('config') .. '/after'); "
			.. "vim.opt.rtp:prepend("
			.. vim.inspect(checkout .. "/nvim")
			.. ")",
		"--cmd",
		"lua vim.g.prosession_dir = vim.env.PR_REVIEW_FIXTURE .. '/sessions/'",
		"-c",
		"lua dofile(" .. vim.inspect(checkout .. "/nvim/tests/pr-reviews.lua") .. ")",
	}, {
		text = true,
		env = {
			PR_REVIEW_TEST_CHILD = "1",
			PR_REVIEW_FIXTURE = temporary,
			PATH = temporary .. "/bin:" .. vim.env.PATH,
			XDG_STATE_HOME = temporary .. "/state",
			XDG_CACHE_HOME = temporary .. "/cache",
			XDG_CONFIG_HOME = temporary .. "/config",
			DOTFILES_CONFIG = temporary .. "/dotfiles.toml",
			DOTFILES_NVIM_BOOTSTRAP_LOCK = temporary .. "/lazy-lock.json",
			TMUX = "",
			TMUX_PANE = "",
		},
	}):wait(120000)
	io.stdout:write(result.stdout or "")
	io.stderr:write(result.stderr or "")
	vim.fn.delete(temporary, "rf")
	vim.cmd(result.code == 0 and "qa!" or "cquit 1")
	return
end
vim.fn.writefile({ "normal" }, temporary .. "/mode")
vim.g.mapleader = ","
vim.o.columns, vim.o.lines = 180, 50
local notifications = {}
require("ghlite")
local completed = {}
local github = require("pr-review-github")
local original_discover = github.discover
github.discover = function(include, callback, account, repository)
	original_discover(include, function(...)
		callback(...)
		local key = repository or "all"
		completed[key] = (completed[key] or 0) + 1
	end, account, repository)
end

local project, other_project = temporary .. "/project", temporary .. "/other-project"
local function make_project(path, name)
	vim.fn.mkdir(path, "p")
	vim.fn.writefile({ "new", "context", "context2" }, path .. "/sample.txt")
	for _, args in ipairs({
		{ "init", "-b", "main" },
		{ "remote", "add", "origin", "https://github.com/" .. name .. ".git" },
		{ "add", "sample.txt" },
		{ "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "fixture" },
	}) do
		local result = vim.system(vim.list_extend({ "git", "-C", path }, args), { text = true }):wait()
		assert(result.code == 0, result.stderr)
	end
end
make_project(project, "example/repo")
make_project(other_project, "another/project")

local function picker()
	local win = require("fzf-lua").utils.fzf_winobj()
	return win and not win:hidden() and vim.api.nvim_win_is_valid(win.fzf_winid) and win or nil
end
local function terminal()
	local win = picker()
	return win and table.concat(vim.api.nvim_buf_get_lines(win.fzf_bufnr, 0, -1, false), "\n") or ""
end
local function preview()
	local win = picker()
	return win
			and win:validate_preview()
			and table.concat(
				vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(win.preview_winid), 0, -1, false),
				"\n"
			)
		or ""
end
local function send(keys)
	vim.api.nvim_chan_send(vim.b[picker().fzf_bufnr].terminal_job_id, keys)
end
local function wait_for(predicate, message)
	if not vim.wait(20000, predicate, 20) then
		error(
			message
				.. "\nResults:\n"
				.. terminal()
				.. "\nPreview:\n"
				.. preview()
				.. "\nMessages:\n"
				.. table.concat(notifications, "\n")
				.. "\n"
				.. vim.fn.execute("messages")
		)
	end
end
local function attempts()
	return vim.fn.filereadable(temporary .. "/attempts") == 1 and #vim.fn.readfile(temporary .. "/attempts") or 0
end
local function requests()
	return vim.fn.filereadable(temporary .. "/requests") == 1 and vim.fn.readfile(temporary .. "/requests") or {}
end
local function searches()
	return select(2, table.concat(requests(), "\n"):gsub("query PRReviewSearch", ""))
end
local function menu_action(key, mode)
	local rendered
	vim.defer_fn(function()
		for _, win in ipairs(vim.api.nvim_list_wins()) do
			local buf = vim.api.nvim_win_get_buf(win)
			if vim.bo[buf].filetype == "wk" then
				rendered = table.concat(vim.api.nvim_buf_get_lines(buf, 0, -1, false), "\n")
			end
		end
		vim.api.nvim_input(key)
	end, 100)
	vim.fn.maparg(",o", mode or "n", false, true).callback()
	vim.api.nvim_feedkeys("", "x", false)
	assert(rendered and rendered:find("comment", 1, true), "PR review menu did not render review actions")
end
local function workflow()
	wait_for(function()
		return terminal():find("another/project#11", 1, true) and terminal():find("All repositories", 1, true)
	end, "nvim-gh-review did not launch the cross-project queue")
	-- Observe messages after the real UI plugins have initialized their routes.
	vim.notify = function(message)
		notifications[#notifications + 1] = message
	end
	assert(vim.g.pr_review_default_scope == "all", "Dedicated launcher did not select global review mode")
	assert(
		not vim.g.this_obsession or vim.g.this_obsession == "",
		"Dedicated launcher started saving a project session"
	)
	send("\3")
	wait_for(function()
		return not picker()
	end, "Startup queue did not close")
	require("fzf-lua").fzf_exec({ "Previous picker" }, { no_hide = true, no_resume = true })
	wait_for(function()
		return terminal():find("Previous picker", 1, true)
	end, "Previous picker did not open")
	vim.fn.maparg(",gR", "n", false, true).callback()
	vim.cmd.PRReviews() -- Repeated invocation joins the pending foreign-picker close.
	wait_for(function()
		return terminal():find("unknown checks", 1, true) and preview():find("external-ci", 1, true)
	end, "Discovery did not render all sources and paginated checks")
	local text = terminal()
	assert(not text:find("own request", 1, true) and not text:find("draft request", 1, true), text)
	assert(not text:find("example/repo#9", 1, true), text)
	assert(text:find("first request", 1, true) < text:find("newer personal", 1, true), text)
	assert(text:find("newer personal", 1, true) < text:find("team passing", 1, true), text)
	assert(text:find("team passing", 1, true) < text:find("pending request", 1, true), text)
	assert(text:find("pending request", 1, true) < text:find("failed request", 1, true), text)
	assert(text:find("failed request", 1, true) < text:find("missing checks", 1, true), text)
	assert(text:find("missing checks", 1, true) < text:find("unknown checks", 1, true), text)
	assert(select(2, text:gsub("first request", "")) == 1, "Personal/team duplicate")
	assert(preview():find("personal, team", 1, true) and preview():find("excluded from priority", 1, true), preview())
	assert(text:find("Checks unavailable", 1, true), "Partial failure was hidden")
	local fetched = #requests()
	local batch = false
	for _, line in ipairs(requests()) do
		local request = vim.json.decode(line)
		batch = batch or request.query:find("PRReviewBatch", 1, true)
		assert(
			not request.query:find("PRReviewChecks", 1, true)
				or request.variables.id == "PR8"
				or request.variables.cursor,
			"Healthy PR metadata was fetched individually"
		)
	end
	assert(batch, "Discovery did not batch metadata")
	send("\1") -- Ctrl-A includes current-head reviewed PRs.
	wait_for(function()
		return terminal():find("example/repo#9", 1, true)
	end, "Include-reviewed action did not filter cached results")
	send("\1")
	wait_for(function()
		return terminal():find("first request", 1, true) and not terminal():find("example/repo#9", 1, true)
	end, "Include-reviewed toggle did not restore default")
	assert(#requests() == fetched, "Toggling reviewed PRs repeated discovery")
	send("\3")
	wait_for(function()
		return not picker()
	end, "Cached picker cancel failed")
	-- Simulate a new editor module: authenticate, then restore this account's
	-- persistent snapshot without fetching the whole queue again.
	package.loaded["pr-reviews"] = nil
	require("pr-reviews").setup()
	vim.cmd.PRReviews()
	wait_for(function()
		return terminal():find("first request", 1, true) and not terminal():find("Loading review requests", 1, true)
	end, "Persistent queue cache did not reopen")
	assert(#requests() == fetched, "Fresh persistent cache repeated discovery")
	vim.g.pr_review_default_scope = nil
	vim.cmd("cd " .. vim.fn.fnameescape(project))
	local changed_origin = vim.system(
		{ "git", "-C", project, "remote", "set-url", "origin", "https://github.com:443/example/repo.git" },
		{ text = true }
	):wait()
	assert(changed_origin.code == 0, changed_origin.stderr)
	local original_gh_repo = vim.env.GH_REPO
	vim.env.GH_REPO = "another/project"
	local scoped_start = #requests()
	local retired_actions = picker()._o.actions
	vim.cmd.PRReviews()
	wait_for(function()
		return terminal():find("example/repo ·", 1, true)
			and terminal():find("first request", 1, true)
			and not terminal():find("refreshing", 1, true)
	end, "Normal Neovim did not discover current-project review requests")
	vim.env.GH_REPO = original_gh_repo
	assert(not terminal():find("another/project#11", 1, true), "Project picker included another repository")
	-- Deliver actions belonging to the replaced picker after the scope switch.
	-- They must not reopen that queue or change the reviewed filter.
	local before_retired = searches()
	retired_actions["ctrl-r"]({}, { last_query = "" })
	retired_actions["ctrl-a"]({}, { last_query = "" })
	local drained = false
	vim.schedule(function()
		drained = true
	end)
	wait_for(function()
		return drained
	end, "Retired actions did not drain")
	assert(terminal():find("example/repo ·", 1, true), "Retired picker action reopened another scope")
	assert(searches() == before_retired, "Retired picker action started discovery")
	for i = scoped_start + 1, #requests() do
		local request = vim.json.decode(requests()[i])
		if request.query:find("PRReviewSearch", 1, true) then
			assert(
				request.variables.query:find("repo:example/repo ", 1, true),
				"Project discovery fetched an unscoped list"
			)
		end
	end
	local cache = require("pr-review-cache")
	assert(cache.read("reviewer", "example/repo").scope == "example/repo", "Project snapshot was not cached separately")
	assert(
		#cache.read("reviewer", "all").prs > #cache.read("reviewer", "example/repo").prs,
		"Project cache replaced global cache"
	)
	vim.cmd("cd " .. vim.fn.fnameescape(other_project))
	vim.cmd.PRReviews()
	wait_for(function()
		return terminal():find("another/project ·", 1, true)
			and terminal():find("another/project#11", 1, true)
			and not terminal():find("refreshing", 1, true)
	end, "Changing projects reused another repository's queue")
	assert(not terminal():find("PR Reviews (all)", 1, true), "Retired picker action toggled the reviewed filter")
	assert(not terminal():find("example/repo#1", 1, true), "Project caches were mixed")
	vim.fn.writefile({ "yes" }, temporary .. "/slow-discovery")
	local previous_global = completed.all
	local before_switch = searches()
	vim.cmd("PRReviewsAll!")
	wait_for(function()
		return searches() > before_switch
	end, "Cross-project background refresh did not start")
	vim.cmd.PRReviews()
	wait_for(function()
		return completed.all > previous_global
	end, "Retired discovery did not finish")
	assert(
		terminal():find("another/project ·", 1, true) and not terminal():find("example/repo#1", 1, true),
		"Late cross-project results replaced the active project queue"
	)
	vim.fn.delete(temporary .. "/slow-discovery")
	vim.cmd.PRReviewsAll()
	wait_for(function()
		return terminal():find("All repositories", 1, true)
	end, "Global cache did not reopen")
	vim.cmd("cd " .. vim.fn.fnameescape(temporary))
	vim.cmd.PRReviews()
	wait_for(function()
		return table.concat(notifications, "\n"):find("Current directory needs a GitHub checkout", 1, true)
	end, "Project command outside a repository did not explain the failure")
	vim.g.pr_review_default_scope = "all"
	vim.cmd("cd " .. vim.fn.fnameescape(checkout))
	vim.fn.writefile({ "yes" }, temporary .. "/slow-discovery")
	local before_refresh = searches()
	send("\18") -- Ctrl-R refreshes while leaving cached rows usable.
	wait_for(function()
		return terminal():find("refreshing", 1, true) and searches() > before_refresh
	end, "Explicit refresh did not keep cached results visible")
	send("\21'example/repo#2")
	wait_for(function()
		return preview():find("example/repo#2", 1, true)
	end, "Refresh lost usable cached rows")
	send("\1")
	wait_for(function()
		return terminal():find("PR Reviews (all)", 1, true)
	end, "Toggle during refresh failed")
	send("\1")
	wait_for(function()
		return not terminal():find("refreshing", 1, true) and preview():find("example/repo#2", 1, true)
	end, "Background refresh lost the typed filter")
	assert(searches() == before_refresh + 3, "Overlapping picker actions duplicated discovery")
	send("\21") -- Restore the full list.
	wait_for(function()
		return preview():find("example/repo#1", 1, true)
	end, "Clearing cached filter failed")
	before_refresh = searches()
	local cache_path = vim.fn.stdpath("cache") .. "/pr-reviews/reviewer.json"
	local cached_at = vim.json.decode(table.concat(vim.fn.readfile(cache_path), "\n")).fetchedAt
	send("\18")
	wait_for(function()
		return searches() > before_refresh
	end, "Second explicit refresh did not start")
	-- A forced refresh during a flight must revalidate a changed account,
	-- discard the old flight's result and keep the two disk snapshots apart.
	vim.fn.writefile({ "alternate" }, temporary .. "/account")
	vim.cmd("PRReviews!")
	send("\3")
	wait_for(function()
		return not picker()
	end, "Cancel during background refresh failed")
	wait_for(function()
		return searches() == before_refresh + 6
	end, "Canceled picker stopped cache refresh")
	-- The last search's process is delayed; wait for the durable cache update.
	local alternate_cache = vim.fn.stdpath("cache") .. "/pr-reviews/alternate.json"
	wait_for(function()
		return vim.fn.filereadable(alternate_cache) == 1
	end, "Canceled refresh did not finish metadata reads")
	assert(not picker(), "Background results reopened a canceled picker")
	assert(
		vim.json.decode(table.concat(vim.fn.readfile(cache_path), "\n")).fetchedAt == cached_at,
		"Account switch wrote another account's results into the original snapshot"
	)
	assert(
		vim.json.decode(table.concat(vim.fn.readfile(alternate_cache), "\n")).login == "alternate",
		"New account's discovery was not cached separately"
	)
	vim.fn.delete(temporary .. "/account")
	vim.fn.delete(temporary .. "/slow-discovery")
	vim.cmd("PRReviews!")
	wait_for(function()
		return preview():find("example/repo#1", 1, true) and not terminal():find("refreshing", 1, true)
	end, "Warm picker did not reopen")
	-- Selecting a cached PR loads the current revision without another queue search.
	local project_head =
		vim.trim(vim.system({ "git", "-C", project, "rev-parse", "HEAD" }, { text = true }):wait().stdout)
	vim.fn.writefile({ project_head }, temporary .. "/head")
	send("\r")
	wait_for(function()
		return vim.api.nvim_buf_get_name(0):find("PR View: 1", 1, true)
			and vim.fn.maparg(",ol", "n", false, true).callback
	end, "Selecting a PR did not open its installed ghlite description")
	assert(attempts() == 0 and not vim.uv.fs_stat(temporary .. "/pending-review"), "Opening created a review")
	assert(require("ghlite.state").selected_PR.headRefOid == project_head, "Cached queue loaded stale PR revision")
	local description = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
	assert(description:find("Description of first request", 1, true), description)
	local tab, tabs = vim.api.nvim_get_current_tabpage(), #vim.api.nvim_list_tabpages()
	vim.cmd("tcd " .. vim.fn.fnameescape(project))
	vim.cmd("edit " .. vim.fn.fnameescape(project .. "/sample.txt"))
	wait_for(function()
		return vim.fn.maparg(",oc", "n", false, true).callback
	end, "Source buffer did not receive review actions")
	local source = vim.api.nvim_get_current_buf()
	menu_action("r")
	wait_for(function()
		return require("ghlite.state").pending_reviews[1]
	end, "Pending review did not start")
	assert(
		vim.api.nvim_get_current_buf() == source and #vim.api.nvim_list_tabpages() == tabs,
		"Starting review changed the source buffer or tabs"
	)
	assert(not vim.wo.diff, "Starting review enabled diff mode")
	-- A selected line range becomes a pending GitHub thread via native ghlite.
	vim.api.nvim_win_set_cursor(0, { 1, 0 })
	vim.cmd("normal! Vj")
	vim.fn.maparg(",oc", "x", false, true).callback()
	wait_for(function()
		return vim.api.nvim_buf_get_name(0):find("PR comment", 1, true)
	end, "Inline comment editor did not open")
	assert(
		vim.api.nvim_get_current_tabpage() == tab and #vim.api.nvim_list_tabpages() == tabs,
		"Commenting created a review tab"
	)
	vim.api.nvim_buf_set_lines(0, 1, -1, false, { "Inline feedback" })
	vim.fn.maparg("<C-s>", "n", false, true).callback()
	wait_for(function()
		return vim.uv.fs_stat(temporary .. "/inline-saved")
	end, "Pending inline feedback was not saved")
	local saved = vim.json.decode(table.concat(vim.fn.readfile(temporary .. "/inline-saved"), "\n"))
	assert(
		saved.path == "sample.txt" and saved.startLine == "1" and saved.line == "2" and saved.reviewId == "REVIEW1",
		"Selection lost its path, range or pending review"
	)
	vim.api.nvim_set_current_buf(source)
	vim.cmd.GHLitePRLoadComments()
	wait_for(function()
		return #vim.diagnostic.get(source) > 0
	end, "Review feedback did not appear in the ordinary source buffer")
	assert(vim.diagnostic.get(source)[1].message:find("Inline feedback", 1, true), "Inline thread text missing")
	assert(not vim.wo.diff and #vim.api.nvim_list_tabpages() == tabs, "Loading comments opened a diff or tab")
	-- Refuse shifted source lines rather than attaching feedback to the wrong revision.
	vim.api.nvim_buf_set_lines(source, 0, 0, false, { "local edit" })
	vim.fn.maparg(",oc", "n", false, true).callback()
	assert(vim.api.nvim_get_current_buf() == source, "Modified source opened a misleading comment editor")
	vim.cmd.undo()
	vim.bo.modified = false
	-- Native submission failure retains the review for a retry.
	vim.ui.select = function(items, _, callback)
		callback(items[1])
	end
	local function save_summary()
		wait_for(function()
			return vim.api.nvim_buf_get_name(0):find("PR Review Submit:", 1, true)
		end, "Native submission summary did not open")
		vim.api.nvim_buf_set_lines(0, 1, -1, false, { "Review summary" })
		vim.fn.maparg("<C-s>", "n", false, true).callback()
	end
	vim.fn.writefile({ "submit-rejected" }, temporary .. "/mode")
	vim.fn.maparg(",os", "n", false, true).callback()
	save_summary()
	wait_for(function()
		return attempts() == 1
	end, "Submission failure was not exercised")
	wait_for(function()
		return table.concat(notifications, "\n"):find("Failed to submit", 1, true)
	end, "Submission failure was not reported")
	assert(require("ghlite.state").pending_reviews[1], "Rejected submission discarded pending review")
	vim.fn.writefile({ "normal" }, temporary .. "/mode")
	vim.fn.maparg(",os", "n", false, true).callback()
	save_summary()
	wait_for(function()
		return attempts() == 2
			and not require("ghlite.state").pending_reviews[1]
			and table.concat(notifications, "\n"):find("Review submitted.", 1, true)
	end, "Pending review could not be retried")
	assert(
		vim.api.nvim_get_current_buf() == source and vim.api.nvim_get_current_tabpage() == tab,
		"Submission left the source buffer"
	)
	vim.fn.maparg(",oq", "n", false, true).callback()
	wait_for(function()
		return picker() and terminal():find("example/repo#1", 1, true)
	end, "Manual return lost the cached queue")
	send("\18")
	wait_for(function()
		return not terminal():find("refreshing", 1, true) and not terminal():find("example/repo#1", 1, true)
	end, "Refresh did not hide the PR reviewed at this head")
	require("fzf-lua").win.close()
	-- Description buffers are reused by number; another repository's PR #1 must
	-- not inherit this repository's review context.
	require("pr-reviews").open({
		id = "OTHER_PR1",
		number = 1,
		headRefOid = project_head,
		repository = { nameWithOwner = "another/project" },
	}, "another/project")
	wait_for(function()
		return table
			.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
			:find("URL: https://github.com/another/project/pull/1", 1, true) and vim.b.pr_review_id == "OTHER_PR1"
	end, "Same-number PR in another repository reused the original context")
	assert(
		require("pr-review-ghlite").current().pr.repository.nameWithOwner == "another/project",
		"Description retained another repository's backend"
	)
	vim.api.nvim_set_current_buf(source)
	vim.fn.maparg(",gP", "n", false, true).callback()
	wait_for(function()
		local session = require("pr-review-ghlite").current()
		return session
			and session.pr.repository.nameWithOwner == "example/repo"
			and session.loading == false
			and require("ghlite.state").pending_reviews_checked[1]
			and #vim.diagnostic.get(source) > 0
	end, "Current-PR shortcut did not restore threads in the existing source buffer")
	assert(
		vim.api.nvim_get_current_buf() == source and #vim.api.nvim_list_tabpages() == tabs and not vim.wo.diff,
		"Current-PR shortcut changed buffers, tabs or layout"
	)
	assert(not require("ghlite.state").pending_reviews[1], "Loading current PR created a review")
	io.stdout:write(
		"PR review workflow passed: full startup, scoped cached discovery, ranking, source-buffer threads, selected-line pending feedback and submission retry without review tabs\n"
	)
end

vim.api.nvim_create_autocmd("VimEnter", {
	once = true,
	callback = function()
		vim.schedule(function()
			local ok, err = xpcall(workflow, debug.traceback)
			require("fzf-lua").win.close()
			vim.cmd("cd " .. vim.fn.fnameescape(checkout))
			vim.fn.delete(temporary, "rf")
			-- Noice's headless UI teardown can leave a hit-enter prompt at exit.
			vim.api.nvim_input("\r")
			if not ok then
				io.stderr:write(err .. "\n")
				vim.cmd("cquit 1")
			end
			vim.cmd("qa!")
		end)
	end,
})
