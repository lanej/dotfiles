local github = require("pr-review-github")
local cache = require("pr-review-cache")
local M = {}
local sessions = {}
local include_reviewed = false
local snapshot, login, refreshing, view, force_requested, revalidate
local discovery_errors = {}
local scope, scope_epoch, scope_request = "all", 0, 0
local snapshots = {}

local function notify(message, level)
	vim.notify(message, level or vim.log.levels.INFO, { title = "PR reviews" })
end

local function clean(text)
	return (text or ""):gsub("[%c]", " ")
end

local function label(pr)
	return pr.repository.nameWithOwner .. "#" .. pr.number
end

local function session_key(account, id)
	return tostring(account) .. ":" .. id
end

local function age(date)
	-- Interpret GitHub's UTC timestamp without changing the process timezone.
	local y, m, d, h, min, s = date:match("(%d+)%-(%d+)%-(%d+)T(%d+):(%d+):(%d+)")
	local local_time = os.time({ year = y, month = m, day = d, hour = h, min = min, sec = s })
	local utc = os.date("!*t", local_time)
	utc.isdst = nil
	local timestamp = local_time + os.difftime(local_time, os.time(utc))
	local days = math.max(0, math.floor((os.time() - timestamp) / 86400))
	return days == 0 and "<1d" or days .. "d"
end

local function preview(pr)
	local lines = {
		label(pr) .. " — " .. pr.title,
		"Author: " .. (pr.author ~= vim.NIL and pr.author.login or "unknown") .. "   Age: " .. age(pr.createdAt),
		"Requested: " .. table.concat(pr.sources, ", "),
		"Checks: " .. pr.check_status .. "   Head: " .. pr.headRefOid,
		pr.reviewed and "Already reviewed at this head" or "",
		"",
	}
	vim.list_extend(lines, vim.split(pr.body or "", "\n", { plain = true }))
	lines[#lines + 1] = ""
	lines[#lines + 1] = "Individual checks (all reported results)"
	for _, check in ipairs(pr.checks) do
		local run = check.checkSuite and check.checkSuite ~= vim.NIL and check.checkSuite.workflowRun
		local workflow = run and run ~= vim.NIL and run.workflow
		local name = workflow and workflow ~= vim.NIL and workflow.name
		local exempt = check.name == "check-all-owners" and name == "Require All Owners Approval"
		lines[#lines + 1] = string.format(
			"%s: %s%s%s",
			check.name or check.context,
			check.state
				or (
					check.status .. (check.conclusion ~= vim.NIL and check.conclusion and "/" .. check.conclusion or "")
				),
			name and " [" .. name .. "]" or "",
			exempt and " (excluded from priority)" or ""
		)
		local url = check.detailsUrl or check.targetUrl
		if url and url ~= vim.NIL then
			lines[#lines + 1] = url
		end
	end
	return lines
end

function M.open(pr, source_scope)
	scope_request = scope_request + 1
	view = nil
	local key = session_key(login, pr.id)
	sessions[key] = sessions[key] or { login = login }
	local session = sessions[key]
	session.pr, session.loading = vim.deepcopy(pr), true
	session.scope = source_scope or scope
	if require("octo.reviews").get_current_review() or vim.bo.modified then
		vim.cmd.tabnew()
	end
	-- Octo owns description, discussion, diff navigation, comments and suggestions.
	-- Opening the description does not create a pending review.
	require("octo.utils").get_pull_request(pr.number, pr.repository.nameWithOwner)
	local buffer = require("octo.utils").get_current_buffer()
	if buffer and buffer.ready and buffer:isPullRequest() then
		buffer:update_metadata()
		-- Octo can mark rendered UI text modified. Its editable-region metadata
		-- identifies actual title, description and discussion edits.
		local dirty = buffer.titleMetadata.dirty or buffer.bodyMetadata.dirty
		for _, comment in ipairs(buffer.commentsMetadata) do
			dirty = dirty or comment.dirty
		end
		if dirty then
			session.loading = "blocked"
			notify(
				"Save the description's edits before reloading it; existing feedback is retained.",
				vim.log.levels.WARN
			)
		else
			buffer.ready = false
			require("octo").load_buffer({ bufnr = buffer.bufnr })
		end
	end
end

local function picker_data()
	local prs, errors = {}, snapshot and snapshot.errors or discovery_errors
	for _, pr in ipairs(snapshot and snapshot.prs or {}) do
		if include_reviewed or not pr.reviewed then
			prs[#prs + 1] = pr
		end
	end
	local rows, by_row = {}, {}
	for _, pr in ipairs(prs) do
		local source = pr.personal and (#pr.sources > 1 and "personal+team" or "personal")
			or table.concat(pr.sources, ",")
		local row = string.format(
			"%-7s %s  %s  @%s %s [%s]",
			pr.check_status,
			label(pr),
			clean(pr.title),
			pr.author ~= vim.NIL and pr.author.login or "unknown",
			age(pr.createdAt),
			source
		)
		rows[#rows + 1], by_row[row] = row, pr
	end
	for _, err in ipairs(errors) do
		rows[#rows + 1] = "! " .. clean(err)
	end
	if #prs == 0 then
		rows[#rows + 1] = not snapshot
				and (refreshing and "Refreshing review requests…" or "Review requests unavailable")
			or (#errors == 0 and "Review queue complete" or "No PRs discovered; results are incomplete")
	end
	local status = snapshot
			and string.format("Cached %ds ago · @%s", math.max(0, os.time() - snapshot.fetchedAt), login)
		or "Loading review requests"
	if refreshing then
		status = status .. " · refreshing"
	end
	status = (scope == "all" and "All repositories" or scope) .. " · " .. status
	return rows, by_row, status .. "\nEnter: open   Ctrl-R: refresh   Ctrl-A: toggle already reviewed"
end

local function write_rows(current)
	local rows, by_row, header = picker_data()
	current.by_row = by_row
	local function replace(name, lines)
		local filename = current.directory .. "/" .. name
		vim.fn.writefile(lines, filename .. ".tmp")
		assert(vim.uv.fs_rename(filename .. ".tmp", filename))
	end
	replace("rows", rows)
	replace("header", vim.split(header, "\n", { plain = true }))
	return header
end

local function active(current)
	local win = require("fzf-lua").utils.fzf_winobj()
	return current
		and current.active
		and current.bufnr
		and win
		and not win:hidden()
		and win.fzf_bufnr == current.bufnr
		and vim.api.nvim_buf_is_valid(current.bufnr)
end

local function redraw()
	-- Reload the owned fzf process rather than replacing its window. Native
	-- reload preserves the live query and cannot reopen a canceled picker.
	local current = view
	if active(current) then
		write_rows(current)
		vim.api.nvim_chan_send(vim.bo[current.bufnr].channel, "\29") -- Ctrl-]
	end
end

local function show_picker(current)
	current.directory = vim.fn.tempname()
	vim.fn.mkdir(current.directory, "p", 448)
	local header = write_rows(current)
	local contents = "cat " .. vim.fn.shellescape(current.directory .. "/rows")
	current.active = true
	require("fzf-lua").fzf_exec(contents, {
		no_hide = true,
		no_resume = true,
		query = current.query or "",
		prompt = include_reviewed and "PR Reviews (all)❯ " or "PR Reviews❯ ",
		header = header,
		fzf_opts = { ["--no-sort"] = true, ["--multi"] = false },
		keymap = {
			fzf = {
				["ctrl-]"] = "reload(" .. contents .. ")+transform-header(cat " .. vim.fn.shellescape(
					current.directory .. "/header"
				) .. ")+refresh-preview",
			},
		},
		winopts = {
			on_create = function(ev)
				-- fzf-lua can reuse these hooks for another picker. Native
				-- reload keeps our terminal ID, so ownership is immutable.
				current.bufnr = current.bufnr or ev.bufnr
			end,
			on_close = function()
				current.active = false
				vim.fn.delete(current.directory, "rf")
			end,
			preview = {
				layout = "flex",
				flip_columns = 140,
				horizontal = "right:50%",
				vertical = "down:55%",
				wrap = true,
			},
		},
		previewer = {
			_ctor = function()
				local renderer = require("fzf-lua.previewer.builtin").buffer_or_file:extend()
				function renderer:parse_entry(row)
					local pr = current.by_row[row]
					return { content = pr and preview(pr) or { row }, filetype = "markdown" }
				end
				return renderer
			end,
		},
		actions = {
			["default"] = function(selected)
				local pr = selected and current.by_row[selected[1]]
				if pr and view == current then
					M.open(pr, current.scope)
				end
			end,
			["ctrl-r"] = function(_, opts)
				vim.schedule(function()
					if view == current then
						M.pick({ scope = current.scope, bang = true, query = opts.last_query })
					end
				end)
			end,
			["ctrl-a"] = function(_, opts)
				if view ~= current then
					return
				end
				include_reviewed = not include_reviewed
				vim.schedule(function()
					if view == current then
						M.pick({ scope = current.scope, query = opts.last_query })
					end
				end)
			end,
		},
	})
end

local function persist()
	local err = cache.write(snapshot)
	if err then
		notify("Cannot save review cache: " .. err, vim.log.levels.WARN)
	end
end

local function refresh(force)
	if refreshing then
		force_requested, revalidate = force_requested or force, revalidate or force
		return
	end
	if not force and cache.fresh(snapshot, os.time()) then
		return
	end
	refreshing, force_requested, revalidate = true, force, false
	local epoch, requested_scope = scope_epoch, scope
	local function authenticate(callback)
		github.request({ "user" }, nil, function(user, err)
			if epoch ~= scope_epoch then
				return
			end
			if err or not user or type(user.login) ~= "string" then
				refreshing = false
				discovery_errors = { "Authentication: " .. (err or "GitHub returned no account") }
				notify(discovery_errors[1], vim.log.levels.ERROR)
				if snapshot then
					snapshot.errors = discovery_errors
				end
				redraw()
				return
			end
			local changed = login ~= user.login
			if changed then
				login = user.login
				snapshot = snapshots[session_key(login, requested_scope)] or cache.read(login, requested_scope)
			end
			discovery_errors = {}
			callback(changed)
		end)
	end
	local function discover()
		local account = login
		github.discover(true, function(prs, errors)
			-- Switching scopes retires the old UI flight. Its late callbacks
			-- cannot publish another repository's results into this queue.
			if epoch ~= scope_epoch then
				return
			end
			local function finish()
				refreshing = false
				if #prs == 0 and #errors > 0 and snapshot then
					-- A failed refresh is not evidence that the cached queue is empty.
					snapshot.errors = errors
				else
					snapshot = {
						version = 1,
						login = account,
						scope = requested_scope,
						fetchedAt = os.time(),
						prs = prs,
						errors = errors,
					}
				end
				for _, err in ipairs(errors) do
					notify(err, vim.log.levels.WARN)
				end
				if snapshot then
					snapshots[session_key(account, requested_scope)] = snapshot
					persist()
				end
				redraw()
			end
			if revalidate then
				revalidate = false
				authenticate(function(changed)
					if changed then
						redraw()
						discover()
					else
						finish()
					end
				end)
			else
				finish()
			end
		end, account, requested_scope ~= "all" and requested_scope or nil)
	end
	-- Verify the account before network discovery. A cached
	-- snapshot from another account must never become this account's queue.
	authenticate(function()
		if not force_requested and cache.fresh(snapshot, os.time()) then
			refreshing = false
			redraw()
			return
		end
		redraw()
		discover()
	end)
end

local function pick_scope(opts)
	if scope ~= opts.scope then
		if snapshot then
			snapshots[session_key(snapshot.login, scope)] = snapshot
		end
		scope, scope_epoch = opts.scope, scope_epoch + 1
		snapshot = login and (snapshots[session_key(login, scope)] or cache.read(login, scope)) or nil
		refreshing, force_requested, revalidate = false, false, false
		discovery_errors = {}
	end
	opts = opts or {}
	if view and view.waiting then
		view.scope, view.query = scope, opts.query
		refresh(opts.bang)
		return
	end
	if view and view.scope == scope and active(view) then
		refresh(opts.bang)
		redraw()
		return
	end
	local previous = require("fzf-lua").utils.fzf_winobj()
	view = { query = opts.query, scope = scope }
	local current = view
	refresh(opts.bang)
	if not previous then
		show_picker(current)
		return
	end
	local job = previous.fzf_bufnr
			and vim.api.nvim_buf_is_valid(previous.fzf_bufnr)
			and vim.bo[previous.fzf_bufnr].channel
		or 0
	current.waiting = true
	require("fzf-lua").win.close()
	local deadline = vim.uv.now() + 5000
	local function open_after_exit()
		if view ~= current then
			return
		end
		if require("fzf-lua").utils.fzf_winobj() then
			current.waiting = false
			return
		end
		if job > 0 and vim.fn.jobwait({ job }, 0)[1] == -1 then
			if vim.uv.now() < deadline then
				vim.defer_fn(open_after_exit, 10)
			else
				current.waiting = false
				notify("Previous picker did not close; reopen :PRReviews", vim.log.levels.WARN)
			end
			return
		end
		current.waiting = false
		show_picker(current)
	end
	vim.schedule(open_after_exit)
end

function M.pick(opts)
	opts = opts or {}
	scope_request = scope_request + 1
	local request = scope_request
	if opts.scope and opts.scope ~= "project" then
		pick_scope(opts)
	elseif not opts.scope and vim.g.pr_review_default_scope == "all" then
		pick_scope(vim.tbl_extend("force", opts, { scope = "all" }))
	else
		github.repository(vim.fn.getcwd(), function(repository, err)
			if request ~= scope_request then
				return
			end
			if not repository then
				notify(err, vim.log.levels.ERROR)
				return
			end
			pick_scope(vim.tbl_extend("force", opts, { scope = repository }))
		end)
	end
end

function M.all(opts)
	M.pick(vim.tbl_extend("force", opts or {}, { scope = "all" }))
end

local function context()
	local buffer = require("octo.utils").get_current_buffer()
	if buffer and buffer:isPullRequest() then
		return sessions[session_key(login, buffer.node.id)]
	end
	local review = require("octo.reviews").get_current_review()
	if review and sessions[session_key(login, review.pull_request.id)] then
		return sessions[session_key(login, review.pull_request.id)], review
	end
	local id = vim.t.pr_review_id
	return id and sessions[session_key(login, id)] or nil
end

local function pending_review(session, review)
	if review and review.id ~= -1 and review.pull_request.id == session.pr.id then
		return review
	end
	for _, candidate in pairs(require("octo.reviews").reviews) do
		if
			candidate.id ~= -1
			and candidate.pull_request.id == session.pr.id
			and candidate.layout
			and vim.api.nvim_tabpage_is_valid(candidate.layout.tabpage)
		then
			return candidate
		end
	end
end

-- These shortcuts only navigate to the pending review. Octo owns the
-- review UI, summary buffer, submission and failure handling.
local function review_command(command)
	local session, active_review = context()
	local review = session and pending_review(session, active_review)
	if review then
		vim.api.nvim_set_current_tabpage(review.layout.tabpage)
	end
	vim.cmd(command)
end

function M.start()
	local session, active = context()
	if not session then
		return
	end
	local review = pending_review(session, active)
	if review then
		vim.api.nvim_set_current_tabpage(review.layout.tabpage)
	else
		local current = require("octo.utils").get_current_buffer()
		if not current or not current:isPullRequest() or current.node.id ~= session.pr.id then
			local description
			for bufnr, buffer in pairs(octo_buffers) do
				if
					vim.api.nvim_buf_is_loaded(bufnr)
					and buffer:isPullRequest()
					and buffer.node.id == session.pr.id
					and buffer.ready
				then
					description = bufnr
					break
				end
			end
			if not description then
				M.open(session.pr, session.scope)
				notify("Start or resume from the loaded Octo description (,rs)")
				return
			end
			local window
			for _, win in ipairs(vim.api.nvim_list_wins()) do
				if vim.api.nvim_win_get_buf(win) == description then
					window = win
					break
				end
			end
			if window then
				vim.api.nvim_set_current_win(window)
			else
				vim.cmd.tabnew()
				vim.api.nvim_set_current_buf(description)
			end
		end
		local selected = require("octo.utils").get_current_buffer()
		if selected and selected.ready and session.loading == true then
			session.pr.headRefOid, session.loading = selected.node.headRefOid, false
		end
		if
			session.loading == "blocked"
			or not selected
			or not selected.ready
			or selected.node.headRefOid ~= session.pr.headRefOid
		then
			notify(
				"Wait for the selected PR revision to load, or save edits and refresh its description before starting",
				vim.log.levels.WARN
			)
			return
		end
		vim.cmd("Octo review")
	end
end

function M.checkout(opts)
	local session, review = context()
	if session then
		local pr = vim.deepcopy(session.pr)
		local buffer = require("octo.utils").get_current_buffer()
		pr.headRefOid = review and review.pull_request.right.commit
			or (buffer and buffer:isPullRequest() and buffer.node.headRefOid)
			or pr.headRefOid
		require("pr-review-checkout").checkout(pr, opts and opts.args ~= "" and opts.args or nil)
	end
end

M.octo_mappings = {
	pull_request = {
		review = { lhs = "<leader>or", desc = "Start/resume review" },
		add_comment = { lhs = "<leader>oc", desc = "Add comment" },
		list_changed_files = { lhs = "<leader>of", desc = "Changed files" },
		open_in_browser = { lhs = "<leader>ob", desc = "Open PR in browser" },
		resolve_thread = { lhs = "<leader>ot", desc = "Resolve thread" },
		unresolve_thread = { lhs = "<leader>oT", desc = "Reopen thread" },
	},
	review_thread = {
		add_reply = { lhs = "<leader>oc", desc = "Reply to thread" },
		add_suggestion = { lhs = "<leader>oS", desc = "Add suggestion" },
		resolve_thread = { lhs = "<leader>ot", desc = "Resolve thread" },
		unresolve_thread = { lhs = "<leader>oT", desc = "Reopen thread" },
	},
	review_diff = {
		submit_review = { lhs = "<leader>os", desc = "Submit review" },
		add_review_comment = { lhs = "<leader>oc", desc = "Add inline comment", mode = { "n", "x" } },
		add_review_suggestion = { lhs = "<leader>oS", desc = "Add suggestion", mode = { "n", "x" } },
		toggle_files = { lhs = "<leader>of", desc = "Toggle changed files" },
		toggle_viewed = { lhs = "<leader>ov", desc = "Toggle file viewed" },
	},
	file_panel = {
		submit_review = { lhs = "<leader>os", desc = "Submit review" },
		toggle_files = { lhs = "<leader>of", desc = "Toggle changed files" },
		toggle_viewed = { lhs = "<leader>ov", desc = "Toggle file viewed" },
	},
}

local function attach(bufnr)
	if bufnr ~= vim.api.nvim_get_current_buf() then
		return
	end
	local session = context()
	local comment = vim.fn.maparg("<leader>oc", "n", false, true)
	local submit = vim.fn.maparg("<leader>os", "n", false, true)
	local native = require("octo.mappings")
	local summary = vim.fn.maparg("<C-a>", "n", false, true).callback == native.approve_review
	local octo_context = comment.buffer == 1 or submit.buffer == 1 or summary
	if octo_context then
		-- Treesitter keeps <leader>o outside Octo's description/review buffers.
		local function show_actions()
			require("which-key").show({ keys = vim.g.mapleader .. "o" })
		end
		vim.keymap.set("n", "<leader>o", show_actions, { buffer = bufnr, desc = "Octo review actions" })
		if vim.fn.maparg("<leader>oc", "x", false, true).buffer == 1 then
			vim.keymap.set("x", "<leader>o", show_actions, { buffer = bufnr, desc = "Octo review actions" })
		end
	end
	local aliases = {
		["<leader>rs"] = "<leader>or",
		["<leader>rp"] = "<leader>op",
		["<leader>rv"] = "<leader>os",
		["<leader>rq"] = "<leader>oq",
		["<leader>rl"] = "<leader>ol",
	}
	for key, binding in
		pairs(session and {
			["<leader>rs"] = { M.start, "Start/resume PR review" },
			["<leader>rp"] = {
				function()
					review_command("Octo review comments")
				end,
				"Pending PR comments",
			},
			["<leader>rv"] = {
				function()
					review_command("Octo review submit")
				end,
				"Submit PR review",
			},
			["<leader>rq"] = {
				function()
					M.pick({ scope = session.scope or "all" })
				end,
				"Return to PR review queue",
			},
			["<leader>rl"] = { M.checkout, "Local PR worktree" },
		} or {})
	do
		vim.keymap.set("n", key, binding[1], { buffer = bufnr, desc = binding[2] })
		if octo_context then
			vim.keymap.set("n", aliases[key], binding[1], { buffer = bufnr, desc = binding[2] })
		end
	end
	if summary then
		vim.keymap.set("n", "<leader>oa", native.approve_review, { buffer = bufnr, desc = "Approve review" })
		vim.keymap.set("n", "<leader>oc", native.comment_review, { buffer = bufnr, desc = "Submit comment review" })
		vim.keymap.set("n", "<leader>or", native.request_changes, { buffer = bufnr, desc = "Request changes" })
	end
end

function M.setup()
	vim.api.nvim_create_user_command("PRReviews", M.pick, { bang = true })
	vim.api.nvim_create_user_command("PRReviewsAll", M.all, { bang = true })
	vim.api.nvim_create_user_command("PRReviewCheckout", M.checkout, { nargs = "?", complete = "dir" })
	vim.api.nvim_create_user_command("PRReviewCleanup", function()
		require("pr-review-checkout").cleanup()
	end, {})
	vim.keymap.set("n", "<leader>gR", M.pick, { desc = "PR review requests" })
	vim.api.nvim_create_autocmd({ "BufEnter", "FileType" }, {
		group = vim.api.nvim_create_augroup("PRReviewQueue", { clear = true }),
		callback = function(ev)
			vim.schedule(function()
				attach(ev.buf)
			end)
		end,
	})
end

return M
