-- Keep ghlite's GitHub state bound to the selected repository, including detached review worktrees.
local M = {}
local remotes = require("pr-review-remote")
local selected, busy = nil, 0
local contexts = {}

local function notify(message)
	vim.notify(message, vim.log.levels.WARN, { title = "PR reviews" })
end

local function git(args)
	local result = vim.system(vim.list_extend({ "git" }, args), { text = true, timeout = 10000 }):wait()
	return result.code == 0 and vim.trim(result.stdout) or nil
end

function M.current()
	return selected
end

function M.checked_out()
	if not selected or not selected.head then
		return false
	end
	local matches = remotes.matching(git({ "remote", "-v" }) or "", selected.pr.repository.nameWithOwner) ~= nil
		and git({ "rev-parse", "HEAD" }) == selected.head
	if matches then
		selected.root = git({ "rev-parse", "--show-toplevel" })
	end
	return matches
end

function M.select(session)
	if selected == session then
		return true
	end
	if busy > 0 then
		notify("Wait for the current GitHub request to finish before changing PRs.")
		return false
	end
	for _, bufnr in ipairs(vim.api.nvim_list_bufs()) do
		if vim.b[bufnr].pr_review_editor and vim.bo[bufnr].modified then
			notify("Save or close the comment editor before changing PRs.")
			return false
		end
	end
	local state = require("ghlite.state")
	if selected then
		contexts[selected] = vim.tbl_extend("force", {}, state)
	end
	for key in pairs(state) do
		state[key] = nil
	end
	for key, value in
		pairs(contexts[session] or {
			comments_list = {},
			pending_reviews = {},
			pending_reviews_checked = {},
			filename_line_to_diff_line = {},
			diff_line_to_filename_line = {},
		})
	do
		state[key] = value
	end
	selected = session
	vim.diagnostic.reset(vim.api.nvim_create_namespace("GHLiteNamespace"))
	vim.diagnostic.reset(vim.api.nvim_create_namespace("GHLiteDiffNamespace"))
	return true
end

function M.open(session, callback)
	if not M.select(session) then
		return
	end
	session.loading = true
	local repo = session.pr.repository.nameWithOwner
	busy = busy + 1
	vim.system(
		{
			"gh",
			"pr",
			"view",
			tostring(session.pr.number),
			"--repo",
			repo,
			"--json",
			"number,headRefName,headRefOid,baseRefName,baseRefOid",
		},
		{ text = true, timeout = 15000, env = { GH_HOST = "github.com", GH_REPO = repo } },
		vim.schedule_wrap(function(result)
			busy = busy - 1
			local ok, pr = pcall(vim.json.decode, result.stdout or "")
			if result.code ~= 0 or not ok or type(pr) ~= "table" or not pr.headRefOid then
				session.loading = "blocked"
				notify("Could not load the selected PR: " .. vim.trim(result.stderr or ""))
				return
			end
			session.head, session.loading = pr.headRefOid, false
			session.pr.headRefOid = pr.headRefOid
			local state = require("ghlite.state")
			state.selected_PR = pr
			state.pending_reviews, state.pending_reviews_checked = {}, {}
			callback()
		end)
	)
end

function M.require_checkout()
	if M.checked_out() then
		if vim.bo.buftype == "" and vim.api.nvim_buf_get_name(0) ~= "" then
			local root = git({ "rev-parse", "--show-toplevel" })
			local filename = vim.api.nvim_buf_get_name(0)
			if not root or filename:sub(1, #root + 1) ~= root .. "/" then
				notify("Open a source file in the selected PR checkout before commenting.")
				return false
			end
			if vim.bo.modified or git({ "diff", "--exit-code", "HEAD", "--", filename }) ~= "" then
				notify("Restore this file to the PR revision before leaving inline feedback.")
				return false
			end
		end
		return true
	end
	notify("Open the PR revision with ,ol or :PRReviewCheckout before leaving inline feedback.")
	return false
end

function M.setup()
	-- gh infers repository identity from GH_REPO for PR and GraphQL requests.
	-- Set it per subprocess rather than changing the user's environment.
	local async = require("async")
	local system = require("ghlite.system")
	system.run_result = function(cmd, opts)
		local env = selected and {
			GH_HOST = "github.com",
			GH_REPO = selected.pr.repository.nameWithOwner,
		} or {}
		opts = vim.tbl_extend("force", { text = true }, opts or {})
		opts.env = vim.tbl_extend("force", opts.env or {}, env)
		return async.await(3, vim.system, cmd, opts)
	end
	system.run = function(cmd)
		return system.run_result(cmd).stdout
	end
	system.run_str = function(cmd, silent)
		local result = system.run_result(vim.split(cmd, " "))
		if result.stderr ~= "" and not silent then
			vim.notify(result.stderr, vim.log.levels.ERROR)
		end
		return result.stdout, result.stderr
	end
	local task = require("ghlite.task")
	local run = task.run
	task.run = function(fn)
		busy = busy + 1
		local result = run(fn)
		result:on_complete(function()
			busy = busy - 1
			vim.schedule(function()
				vim.api.nvim_exec_autocmds("User", { pattern = "PRReviewUpdated" })
			end)
		end)
		return result
	end
	local utils = require("ghlite.pr_utils")
	local is_checked_out, get_checked_out = utils.is_pr_checked_out, utils.get_checked_out_pr
	utils.is_pr_checked_out = function()
		if selected then
			return M.checked_out()
		end
		return is_checked_out()
	end
	utils.get_checked_out_pr = function()
		if not selected then
			return get_checked_out()
		end
		if M.require_checkout() then
			return require("ghlite.state").selected_PR
		end
		return nil, "declined"
	end
	local comments = require("ghlite.comments")
	local load_buffer = comments.load_comments_on_buffer
	comments.load_comments_on_buffer = function(bufnr)
		if selected and vim.bo[bufnr].buftype == "" and not M.checked_out() then
			vim.diagnostic.reset(vim.api.nvim_create_namespace("GHLiteNamespace"), bufnr)
			return
		end
		return load_buffer(bufnr)
	end
	local editor = require("ghlite.utils")
	local get_comment = editor.get_comment
	editor.get_comment = function(...)
		get_comment(...)
		if selected then
			vim.b.pr_review_id = selected.pr.id
			vim.b.pr_review_editor = true
		end
	end
	require("ghlite").setup({
		view_split = "",
		diff_split = "",
		comment_split = "",
		comments_quickfix = "fill",
		pr_commands = {},
		open_command = vim.fn.has("mac") == 1 and "open" or "xdg-open",
		keymaps = {
			comment = { send_comment = "<C-s>" },
			pr = { checkout = "", merge = "", diffview = "" },
		},
	})
end

return M
