local backend = require(
	require("dotfiles-config").enabled("features.nvim_ghlite") and "pr-review-ghlite-actions" or "pr-review-octo"
)
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
	backend.open(session, notify)
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

backend.install(M, function(id)
	return sessions[session_key(login, id)]
end, notify)

return M
