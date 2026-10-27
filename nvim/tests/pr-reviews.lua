-- One workflow through the full configuration, launcher, picker, Octo and gh.
-- nvim --headless -u NONE -i NONE -n -l nvim/tests/pr-reviews.lua
local checkout = vim.fn.getcwd()
local temporary = vim.env.PR_REVIEW_FIXTURE or vim.fn.tempname()
if not vim.env.PR_REVIEW_TEST_CHILD then
	vim.fn.mkdir(temporary .. "/bin", "p")
	vim.fn.mkdir(temporary .. "/cache/nvim", "p")
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
vim.g.octo_viewer = "reviewer"
vim.o.columns, vim.o.lines = 180, 50
local notifications = {}
require("octo").setup({
	picker = "fzf-lua",
	mappings = require("pr-reviews").octo_mappings,
	gh_env = { PR_REVIEW_FIXTURE = temporary },
	use_local_fs = false,
	reviews = { auto_show_threads = false },
	default_to_projects_v2 = false,
	enable_builtin = true,
})
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
	for _, args in ipairs({
		{ "init", "-b", "main" },
		{ "remote", "add", "origin", "https://github.com/" .. name .. ".git" },
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
local function summary_action(key)
	local map = vim.fn.maparg(key, "n", false, true)
	assert(type(map.callback) == "function", "Native summary action missing: " .. key)
	map.callback()
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
	assert(rendered and rendered:find("comment", 1, true), "Octo menu did not render review actions")
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
	-- The cached queue is now older than the selected PR. Octo must fetch the
	-- current revision without requiring another discovery of the whole list.
	vim.fn.writefile({ string.rep("e", 40) }, temporary .. "/head")
	send("\r")
	wait_for(function()
		local buffer = require("octo.utils").get_current_buffer()
		return buffer and buffer.ready and buffer.number == 1 and vim.fn.maparg(",or", "n", false, true).callback
	end, "Selecting a PR did not open its installed Octo description")
	assert(attempts() == 0 and not require("octo.reviews").get_current_review(), "Opening created a review")
	local description = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
	assert(description:find("Description of first request", 1, true), description)
	assert(
		vim.fn.maparg(",o", "x", false, true).buffer == 0,
		"Description replaced visual Treesitter selection with an empty menu"
	)
	menu_action("r")
	wait_for(function()
		local review = require("octo.reviews").get_current_review()
		return review
			and review.layout.files[1]
			and review.layout.files[1].right_bufid
			and vim.fn.maparg(",os", "n", false, true).callback
	end, "Octo remote review did not start")
	local review = require("octo.reviews").get_current_review()
	assert(review.pull_request.right.commit == string.rep("e", 40), "Cached queue started review of stale code")
	local file = review.layout.files[1]
	assert(file.right_lines[1] == "new" and file.left_lines[1] == "old", "Remote diff content missing")
	vim.api.nvim_set_current_win(review.layout.right_winid)
	local code = vim.api.nvim_create_buf(false, true)
	vim.bo[code].filetype = "lua"
	vim.api.nvim_win_set_buf(review.layout.right_winid, code)
	wait_for(function()
		return vim.fn.maparg(",rs", "n", false, true).buffer == 1
	end, "Review context did not attach to a local code buffer")
	assert(
		vim.fn.maparg(",o", "n", false, true).buffer == 0 and vim.fn.maparg(",o", "x", false, true).buffer == 0,
		"Review context replaced ordinary code's Treesitter selection"
	)
	vim.api.nvim_win_set_buf(review.layout.right_winid, file.right_bufid)
	wait_for(function()
		return vim.fn.maparg(",o", "x", false, true).buffer == 1
	end, "Visual inline-feedback menu did not attach")
	vim.api.nvim_win_set_cursor(0, { 1, 0 })
	vim.cmd("normal! V")
	menu_action("c", "x")
	wait_for(function()
		local buffer = require("octo.utils").get_current_buffer()
		return buffer and buffer.kind == "reviewthread" and buffer.commentsMetadata[1]
	end, "Octo did not create a pending inline comment buffer")
	vim.cmd.stopinsert()
	local buffer = require("octo.utils").get_current_buffer()
	local mark = vim.api.nvim_buf_get_extmark_by_id(
		0,
		require("octo.constants").OCTO_COMMENT_NS,
		buffer.commentsMetadata[1].extmark,
		{ details = true }
	)
	vim.api.nvim_buf_set_lines(0, mark[1] + 1, mark[3].end_row - 1, false, { "Inline feedback" })
	local thread_buf = vim.api.nvim_get_current_buf()
	vim.cmd.write()
	wait_for(function()
		return buffer.commentsMetadata[1].savedBody == "Inline feedback"
	end, "Octo inline feedback was not saved to the pending review")
	vim.api.nvim_set_current_win(review.layout.right_winid)
	vim.fn.maparg(",op", "n", false, true).callback()
	wait_for(function()
		return terminal():find("sample.txt:1:1", 1, true) and preview():find("Inline feedback", 1, true)
	end, "Native Octo pending-comment picker did not open")
	send("\3")
	wait_for(function()
		return not picker()
	end, "Pending-comment picker did not close")
	-- Returning to the cached queue keeps Octo's pending review and scope.
	vim.g.pr_review_default_scope = nil
	vim.cmd("cd " .. vim.fn.fnameescape(other_project))
	local before_return = searches()
	vim.fn.maparg(",oq", "n", false, true).callback()
	wait_for(function()
		return terminal():find("All repositories", 1, true)
	end, "Return mapping changed to the current directory's project")
	assert(searches() == before_return, "Returning to a warm queue repeated discovery")
	send("\21newer personal")
	wait_for(function()
		return preview():find("example/repo#10", 1, true)
	end, "Queue did not filter to another PR")
	send("\r")
	wait_for(function()
		local visible = require("octo.utils").get_current_buffer()
		return visible and visible.ready and visible.number == 10 and vim.fn.maparg(",os", "n", false, true).callback
	end, "Second description did not open")
	assert(not require("octo.reviews").get_current_review(), "Second PR inherited the first review")
	assert(
		vim.api.nvim_tabpage_is_valid(review.layout.tabpage) and vim.api.nvim_buf_is_valid(file.right_bufid),
		"Queue selection damaged the pending review"
	)
	local second_description = vim.api.nvim_get_current_buf()
	vim.fn.maparg(",os", "n", false, true).callback()
	assert(vim.api.nvim_get_current_buf() == second_description, "Second PR opened the first PR's summary")
	vim.api.nvim_set_current_tabpage(review.layout.tabpage)
	vim.fn.maparg(",os", "n", false, true).callback()
	local summary = vim.api.nvim_get_current_buf()
	assert(vim.api.nvim_win_get_config(0).relative == "editor", "Native Octo summary did not open")
	wait_for(function()
		return vim.fn.maparg(",oa", "n", false, true).buffer == 1
	end, "Summary review actions did not attach")
	vim.api.nvim_buf_set_lines(summary, 0, -1, false, { "Summary feedback" })
	vim.fn.writefile({ "submit-rejected" }, temporary .. "/mode")
	summary_action(",oc")
	wait_for(function()
		return table.concat(notifications, "\n"):find("Review submission rejected", 1, true)
	end, "Octo did not report the submission failure")
	assert(attempts() == 1 and vim.fn.filereadable(temporary .. "/submitted") == 0, "Rejected review was submitted")
	assert(
		vim.api.nvim_get_current_buf() == summary
			and review.id == "REVIEW1"
			and vim.api.nvim_tabpage_is_valid(review.layout.tabpage),
		"Native failure discarded the pending review or summary"
	)
	vim.fn.writefile({ "normal" }, temporary .. "/mode")
	summary_action(",oc")
	wait_for(function()
		return not vim.api.nvim_tabpage_is_valid(review.layout.tabpage)
	end, "Native submission did not close the completed review")
	assert(attempts() == 2, "Native retry did not submit the pending review")
	local submitted = vim.json.decode(vim.fn.readfile(temporary .. "/attempts")[2])
	assert(
		submitted.review == "REVIEW1" and submitted.event == "COMMENT" and submitted.body == "Summary feedback",
		"Native submission lost the review ID or summary"
	)
	assert(vim.fn.filereadable(temporary .. "/inline-saved") == 1, "Submission lost inline comments")
	assert(
		not picker() and not require("octo.reviews").get_current_review(),
		"Submission automatically opened a queue or review"
	)
	local returned = require("octo.utils").get_current_buffer()
	assert(
		returned and (returned.number == 1 or returned.number == 10),
		"Native submission did not return to an existing PR"
	)
	vim.fn.maparg(",oq", "n", false, true).callback()
	wait_for(function()
		return terminal():find("All repositories", 1, true)
	end, "Native submission lost the originating queue")
	send("\18")
	wait_for(function()
		return terminal():find("newer personal", 1, true)
			and not terminal():find("first request", 1, true)
			and not terminal():find("refreshing", 1, true)
	end, "Refreshing did not omit the natively submitted review at this head")
	vim.cmd("cd " .. vim.fn.fnameescape(project))
	vim.cmd("PRReviews!")
	wait_for(function()
		return terminal():find("example/repo ·", 1, true)
			and terminal():find("newer personal", 1, true)
			and not terminal():find("first request", 1, true)
			and not terminal():find("refreshing", 1, true)
	end, "Project refresh did not update native review history")
	vim.cmd.PRReviewsAll()
	wait_for(function()
		return terminal():find("All repositories", 1, true)
	end, "Global queue did not reopen")
	send("\3")
	wait_for(function()
		return not picker()
	end, "Picker cancel failed")
	vim.fn.writefile({ "repeat-review" }, temporary .. "/mode")
	vim.cmd("PRReviewsAll!")
	wait_for(function()
		return preview():find(string.rep("d", 40), 1, true)
	end, "New head did not reappear in the queue")
	send("\r")
	wait_for(function()
		local visible = require("octo.utils").get_current_buffer()
		return visible
			and visible.ready
			and visible.node.headRefOid == string.rep("d", 40)
			and vim.fn.maparg(",or", "n", false, true).callback
	end, "Cached Octo description did not reload the new revision")
	vim.fn.maparg(",or", "n", false, true).callback()
	wait_for(function()
		local next_review = require("octo.reviews").get_current_review()
		return next_review
			and next_review.id == "REVIEW2"
			and next_review.layout.files[1]
			and vim.fn.maparg(",os", "n", false, true).callback
	end, "Same PR could not start another pending review")
	local next_review = require("octo.reviews").get_current_review()
	assert(next_review.pull_request.right.commit == string.rep("d", 40), "Repeat review showed stale code")
	vim.fn.maparg(",os", "n", false, true).callback()
	assert(vim.api.nvim_get_current_buf() ~= summary, "New review reused the previous native summary")
	assert(vim.api.nvim_win_get_config(0).relative == "editor", "Shortcut did not open native submission window")
	assert(type(vim.fn.maparg("<C-a>", "n", false, true).callback) == "function", "Native approval action missing")
	assert(
		type(vim.fn.maparg("<C-r>", "n", false, true).callback) == "function",
		"Native request-changes action missing"
	)
	vim.cmd.close()
	next_review.layout:close()
	assert(vim.api.nvim_buf_is_valid(thread_buf) or vim.fn.filereadable(temporary .. "/inline-saved") == 1)
	io.stdout:write(
		"PR review workflow passed: full startup, scoped cached discovery, ranking, native Octo feedback and submission, failure retry and manual picker return\n"
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
