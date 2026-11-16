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
	require("pr-review-ghlite").open(session, function()
		vim.t.pr_review_id = pr.id
		if
			require("pr-review-ghlite").checked_out()
			and vim.bo.buftype == ""
			and vim.api.nvim_buf_get_name(0) ~= ""
		then
			require("ghlite.comments").load_comments()
		else
			-- ghlite reuses description buffers by PR number across repositories.
			for _, bufnr in ipairs(vim.api.nvim_list_bufs()) do
				if vim.api.nvim_buf_get_name(bufnr):match("PR View: " .. pr.number .. "$") then
					vim.b[bufnr].pr_review_id = pr.id
				end
			end
			require("ghlite.pr_commands").load_pr_view()
		end
	end)
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
	local id = vim.b.pr_review_id or vim.t.pr_review_id
	return id and sessions[session_key(login, id)] or require("pr-review-ghlite").current()
end

function M.review_current()
	github.repository(vim.fn.getcwd(), function(repo, err)
		if not repo then
			notify(err, vim.log.levels.WARN)
			return
		end
		vim.system(
			{ "gh", "pr", "view", "--json", "id,number,headRefOid,url" },
			{ text = true, timeout = 15000, env = { GH_REPO = repo, GH_HOST = "github.com" } },
			vim.schedule_wrap(function(result)
				local ok, pr = pcall(vim.json.decode, result.stdout or "")
				if result.code ~= 0 or not ok or type(pr) ~= "table" or not pr.id then
					notify("Could not find this branch's PR: " .. vim.trim(result.stderr or ""), vim.log.levels.WARN)
					return
				end
				pr.repository = { nameWithOwner = repo }
				M.open(pr, repo)
			end)
		)
	end)
end

function M.start()
	local session = context()
	if session and require("pr-review-ghlite").select(session) and require("pr-review-ghlite").require_checkout() then
		require("ghlite.pr_commands").start_review("github")
	end
end

function M.checkout(opts)
	local session = context()
	if session then
		if session.loading then
			notify("Wait for the selected PR revision to load before checkout", vim.log.levels.WARN)
			return
		end
		require("pr-review-checkout").checkout(session.pr, opts and opts.args ~= "" and opts.args or nil)
	end
end

function M.local_files(pr, path)
	local session = sessions[session_key(login, pr.id)]
	if not session or not require("pr-review-ghlite").select(session) then
		return
	end
	session.root = path
	vim.cmd("tcd " .. vim.fn.fnameescape(path))
	vim.t.pr_review_id = pr.id
	require("ghlite.comments").load_comments()
	require("fzf-lua").files({ cwd = path })
end

local function attach(bufnr)
	if bufnr ~= vim.api.nvim_get_current_buf() then
		return
	end
	local session = context()
	if not session or session.loading then
		return
	end
	if not require("pr-review-ghlite").select(session) then
		return
	end
	local name = vim.api.nvim_buf_get_name(bufnr)
	local source = vim.bo[bufnr].buftype == ""
		and name ~= ""
		and require("pr-review-ghlite").checked_out()
		and session.root
		and name:sub(1, #session.root + 1) == session.root .. "/"
	local review_buffer = vim.bo[bufnr].buftype == "nofile"
		and (name:find("PR View:", 1, true) or name:find("PR comment", 1, true) or name:find("PR reply", 1, true))
	if not source and not review_buffer then
		return
	end
	vim.b[bufnr].pr_review_id = session.pr.id
	local function command(cmd)
		return function()
			if require("pr-review-ghlite").select(session) then
				vim.cmd(cmd)
			end
		end
	end
	local function comment(opts)
		if not require("pr-review-ghlite").select(session) or not require("pr-review-ghlite").require_checkout() then
			return
		end
		local comments = require("ghlite.comments")
		local task = require("ghlite.pr_commands").start_review("github")
		task:on_complete(function(err)
			vim.schedule(function()
				if not err and require("ghlite.state").pending_reviews[session.pr.number] then
					comments.comment_on_line(opts)
				end
			end)
		end)
	end
	local bindings = {
		["<leader>or"] = { M.start, "Start/resume review" },
		["<leader>oc"] = { source and comment or command("GHLitePRAddPRComment"), "Add comment or reply" },
		["<leader>of"] = {
			function()
				if require("pr-review-ghlite").require_checkout() then
					require("fzf-lua").files()
				end
			end,
			"PR files",
		},
		["<leader>ov"] = { command("GHLitePRToggleFileViewed"), "Toggle file viewed" },
		["<leader>op"] = {
			function()
				if require("pr-review-ghlite").require_checkout() then
					vim.cmd("GHLitePRLoadComments")
					vim.cmd("copen")
				end
			end,
			"Review comments (including pending)",
		},
		["<leader>os"] = { command("GHLitePRSubmitReview github"), "Submit review" },
		["<leader>oa"] = { command("GHLitePRApprove"), "Approve review" },
		["<leader>ox"] = { command("GHLitePRRequestChanges"), "Request changes" },
		["<leader>oq"] = {
			function()
				M.pick({ scope = session.scope or "all" })
			end,
			"Return to review queue",
		},
		["<leader>ol"] = { M.checkout, "Local PR worktree" },
		["<leader>ob"] = {
			function()
				vim.ui.open(
					session.pr.url
						or (
							"https://github.com/"
							.. session.pr.repository.nameWithOwner
							.. "/pull/"
							.. session.pr.number
						)
				)
			end,
			"Open PR in browser",
		},
		["<leader>ot"] = { command("GHLitePRResolveComment"), "Resolve thread" },
		["<leader>oT"] = { command("GHLitePRUnresolveComment"), "Reopen thread" },
		["<leader>oh"] = {
			function()
				vim.diagnostic.open_float({ scope = "line", source = true })
			end,
			"Read review thread",
		},
	}
	for key, binding in pairs(bindings) do
		vim.keymap.set("n", key, binding[1], { buffer = bufnr, desc = binding[2] })
	end
	for alias, key in pairs({ rs = "or", rp = "op", rv = "os", rq = "oq", rl = "ol" }) do
		local binding = bindings["<leader>" .. key]
		vim.keymap.set("n", "<leader>" .. alias, binding[1], { buffer = bufnr, desc = binding[2] })
	end
	local function menu()
		require("which-key").show({ keys = vim.g.mapleader .. "o" })
	end
	vim.keymap.set("n", "<leader>o", menu, { buffer = bufnr, desc = "PR review actions" })
	if source then
		vim.keymap.set("x", "<leader>oc", function()
			local first, last = vim.fn.line("v"), vim.fn.line(".")
			vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "nx", false)
			comment({ line1 = math.min(first, last), line2 = math.max(first, last) })
		end, { buffer = bufnr, desc = "Comment on selected lines" })
		vim.keymap.set("x", "<leader>o", menu, { buffer = bufnr, desc = "PR review actions" })
	end
end

function M.setup()
	vim.api.nvim_create_user_command("PRReviews", M.pick, { bang = true })
	vim.api.nvim_create_user_command("PRReviewsAll", M.all, { bang = true })
	vim.api.nvim_create_user_command("PRReviewCurrent", M.review_current, {})
	vim.api.nvim_create_user_command("PRReviewCheckout", M.checkout, { nargs = "?", complete = "dir" })
	vim.api.nvim_create_user_command("PRReviewCleanup", function()
		require("pr-review-checkout").cleanup()
	end, {})
	vim.keymap.set("n", "<leader>gR", M.pick, { desc = "PR review requests" })
	vim.keymap.set("n", "<leader>gP", M.review_current, { desc = "Review current PR inline" })
	vim.api.nvim_create_autocmd({ "BufEnter", "FileType" }, {
		group = vim.api.nvim_create_augroup("PRReviewQueue", { clear = true }),
		callback = function(ev)
			vim.schedule(function()
				attach(ev.buf)
			end)
		end,
	})
	vim.api.nvim_create_autocmd("User", {
		pattern = "PRReviewUpdated",
		group = vim.api.nvim_create_augroup("PRReviewUpdates", { clear = true }),
		callback = function()
			attach(vim.api.nvim_get_current_buf())
		end,
	})
end

return M
