local api = require("beads.api")
local document = require("beads.document")
local ui = require("beads.ui")
local M = {}
local projects, active, documents = {}, nil, {}
local discovering = false
local open_requests = {}
local context_namespace = vim.api.nvim_create_namespace("beads-context")

local function notify(message, level)
	vim.notify("Beads: " .. message, level or vim.log.levels.INFO)
end

local function project(name)
	if not name or name == "" then
		local current = documents[vim.api.nvim_get_current_buf()]
		if current then
			return current.project
		end
		for _, candidate in pairs(projects) do
			if candidate.tree_buf == vim.api.nvim_get_current_buf() then
				return candidate
			end
		end
	end
	name = name and name ~= "" and name or active
	assert(projects[name], "Select a configured project with :Beads <project>")
	return projects[name]
end

local function prefix_candidates(values, lead)
	local result = {}
	for _, value in ipairs(values) do
		if value:sub(1, #lead) == lead then
			result[#result + 1] = value
		end
	end
	table.sort(result)
	return result
end

function M.projects()
	local names = prefix_candidates(vim.tbl_keys(projects), "")
	if #names == 0 then
		notify("No projects loaded. Run :Beads to discover the local service.")
		return
	end
	local ok, current = pcall(project)
	local lines = { "Projects (* current):" }
	for _, name in ipairs(names) do
		lines[#lines + 1] = (ok and current.name == name and "* " or "  ") .. name
	end
	notify(table.concat(lines, "\n"))
end

-- Completion is deliberately cache-only: never verify authority or load a graph.
local function complete_ids(lead)
	local ok, p = pcall(project)
	if not ok then
		return {}
	end
	local ids = {}
	for _, task in ipairs(p.graph.items) do
		ids[#ids + 1] = task.id
	end
	return prefix_candidates(ids, lead)
end

local function async(fn, done)
	api.run(fn, function(err, result)
		if done then
			done(err, result)
		elseif err then
			notify(api.message(err), vim.log.levels.ERROR)
		end
	end)
end

local function selected(p)
	if p.tree_buf and vim.api.nvim_get_current_buf() == p.tree_buf then
		local node = p.widget and p.widget:get_node(vim.api.nvim_win_get_cursor(0)[1])
		return node and node.task and node.id
	end
	local doc = documents[vim.api.nvim_get_current_buf()]
	return doc and doc.project == p and doc.base and doc.base.id or p.selection
end

local function render(p)
	if not p.tree_buf or not vim.api.nvim_buf_is_valid(p.tree_buf) then
		return
	end
	ui.render(p)
	for _, win in ipairs(vim.fn.win_findbuf(p.tree_buf)) do
		ui.select(p, win)
	end
end

function M.refresh(name)
	local p = project(name)
	p.selection = selected(p) or p.selection
	p.generation = p.generation + 1
	local generation = p.generation
	p.loading, p.error = true, nil
	render(p)
	async(function()
		return p.store:list()
	end, function(err, graph)
		if generation ~= p.generation then
			return
		end
		p.loading = false
		if err then
			p.error = api.message(err)
			render(p)
			notify(p.error, vim.log.levels.ERROR)
			return
		end
		p.loaded = true
		-- Read selection when applying the response: navigation during HTTP wins.
		p.selection = selected(p) or p.selection
		p.graph = graph
		render(p)
	end)
end

local function editing_window(p)
	local current = vim.api.nvim_get_current_win()
	if vim.api.nvim_get_current_buf() ~= p.tree_buf then
		p.edit_win = current
		return current
	end
	if
		p.edit_win
		and vim.api.nvim_win_is_valid(p.edit_win)
		and vim.api.nvim_win_get_tabpage(p.edit_win) == vim.api.nvim_get_current_tabpage()
		and vim.api.nvim_win_get_buf(p.edit_win) ~= p.tree_buf
	then
		return p.edit_win
	end
	for _, win in ipairs(vim.api.nvim_tabpage_list_wins(0)) do
		if vim.api.nvim_win_get_buf(win) ~= p.tree_buf then
			p.edit_win = win
			return win
		end
	end
	vim.cmd("rightbelow vnew")
	p.edit_win = vim.api.nvim_get_current_win()
	return p.edit_win
end

local function display(p, buf)
	local win = editing_window(p)
	open_requests[win] = (open_requests[win] or 0) + 1
	vim.api.nvim_win_set_buf(win, buf)
	vim.api.nvim_set_current_win(win)
end

local function find_doc(p, id)
	for buf, doc in pairs(documents) do
		if
			vim.api.nvim_buf_is_valid(buf)
			and doc.project.store.scope == p.store.scope
			and (doc.base and doc.base.id == id or doc.pending and doc.pending.target == id)
		then
			return buf, doc
		end
	end
end

local function bind(doc)
	ui.setup()
	local identity = doc.base and doc.base.id or "unsaved draft"
	local status = doc.base and (doc.base.status or "unknown") or "local"
	local parent = doc.parent and " · parent " .. doc.parent or ""
	local phase = doc.saving and "Saving…"
		or doc.pending and "Pending creation"
		or vim.b[doc.buf].beads_error and "Save failed"
		or vim.bo[doc.buf].modified and "Unsaved"
		or "Saved"
	local phase_style = doc.pending and "BeadsAttention"
		or vim.b[doc.buf].beads_error and "BeadsBlocked"
		or vim.bo[doc.buf].modified and "BeadsWarning"
		or "BeadsClosed"
	vim.api.nvim_buf_clear_namespace(doc.buf, context_namespace, 0, -1)
	vim.api.nvim_buf_set_extmark(doc.buf, context_namespace, 0, 0, {
		virt_lines = {
			{
				{ "  " .. phase, phase_style },
				{
					"  ·  " .. status:gsub("_", " ") .. "  ·  " .. doc.project.name .. " / " .. identity .. parent,
					"BeadsMetadata",
				},
			},
		},
		virt_lines_above = false,
		right_gravity = false,
	})

	-- Only the persistence boundary is managed here; Markview owns Markdown rendering.
	for index, line in ipairs(vim.api.nvim_buf_get_lines(doc.buf, 0, -1, false)) do
		if line == doc.marker then
			vim.api.nvim_buf_set_extmark(doc.buf, context_namespace, index - 1, 0, { end_col = #line, conceal = "" })
		end
	end
	if not doc.base then
		return
	end
	vim.b[doc.buf].beads_id = doc.base.id
	vim.b[doc.buf].beads_revision = doc.base.revision
	local name = "beads://" .. doc.project.name .. "/" .. doc.base.id .. ".md"
	if vim.api.nvim_buf_get_name(doc.buf) ~= name then
		vim.api.nvim_buf_set_name(doc.buf, name)
	end
end

local function make_doc(p, fields, options)
	options = options or {}
	local buf = vim.api.nvim_create_buf(true, false)
	local doc = {
		buf = buf,
		project = p,
		base = options.base,
		parent = options.parent,
		marker = options.marker or "<!-- beads:acceptance:v2:" .. document.token() .. " -->",
		pending = options.pending,
		receipt_path = options.receipt_path,
		pending_fields = options.pending and options.pending.fields,
	}
	documents[buf] = doc
	vim.api.nvim_buf_set_name(buf, "beads://" .. p.name .. "/draft-" .. document.token() .. ".md")
	vim.bo[buf].buftype = "acwrite"
	vim.bo[buf].bufhidden = "hide"
	vim.bo[buf].swapfile = false
	vim.bo[buf].modeline = false
	vim.b[buf].focus_disable = true
	vim.api.nvim_buf_set_lines(buf, 0, -1, false, options.lines or document.render(fields, doc.marker))
	vim.bo[buf].modified = not options.base
	vim.b[buf].beads_project = p.name
	vim.b[buf].beads_parent = doc.parent
	bind(doc)
	vim.bo[buf].filetype = "markdown"
	vim.api.nvim_create_autocmd({ "TextChanged", "TextChangedI" }, {
		buffer = buf,
		callback = function()
			bind(doc)
		end,
	})
	vim.api.nvim_create_autocmd("BufWinEnter", {
		buffer = buf,
		callback = function()
			ui.enter_document(buf)
		end,
	})
	vim.api.nvim_create_autocmd("BufWinLeave", {
		buffer = buf,
		callback = function()
			ui.leave_document(buf)
		end,
	})
	vim.api.nvim_create_autocmd("BufWriteCmd", {
		buffer = buf,
		callback = function(event)
			if event.match ~= vim.api.nvim_buf_get_name(buf) then
				notify("Use :write to save this task; export text with :write! <file>", vim.log.levels.ERROR)
				return
			end
			if doc.saving then
				notify("A save is already running; local edits are retained", vim.log.levels.WARN)
				return
			end
			local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
			local ok, parsed = pcall(document.parse, lines, doc.marker)
			if not ok then
				notify(tostring(parsed), vim.log.levels.ERROR)
				vim.b[buf].beads_error = tostring(parsed)
				return
			end
			local tick = vim.api.nvim_buf_get_changedtick(buf)
			doc.saving = true
			vim.b[buf].beads_saving = true
			vim.b[buf].beads_error = nil
			bind(doc)
			async(function()
				local _, submitted = p.store:save(doc, parsed, lines)
				return submitted
			end, function(err, submitted)
				doc.saving = false
				if not vim.api.nvim_buf_is_valid(buf) then
					return
				end
				vim.b[buf].beads_saving = false
				vim.b[buf].beads_pending = doc.pending ~= nil
				bind(doc)
				if err then
					vim.b[buf].beads_error = api.message(err)
					bind(doc)
					notify(
						api.message(err) .. (doc.pending and "; creation retained for :BeadsRecover" or ""),
						vim.log.levels.ERROR
					)
					return
				end
				bind(doc)
				if vim.api.nvim_buf_get_changedtick(buf) == tick and vim.deep_equal(parsed, submitted) then
					vim.bo[buf].modified = false
				end
				notify("Saved " .. doc.base.id)
				M.refresh(p.name)
			end)
		end,
	})
	vim.api.nvim_create_autocmd("BufWipeout", {
		buffer = buf,
		once = true,
		callback = function()
			documents[buf] = nil
		end,
	})
	return buf, doc
end

function M.open(id, name)
	local p = project(name)
	id = id and id ~= "" and id or assert(selected(p), "Select a task")
	local existing = find_doc(p, id)
	if existing then
		display(p, existing)
		return
	end
	local win = editing_window(p)
	local original = vim.api.nvim_win_get_buf(win)
	local tick = vim.api.nvim_buf_get_changedtick(original)
	open_requests[win] = (open_requests[win] or 0) + 1
	local generation = open_requests[win]
	local source_win = vim.api.nvim_get_current_win()
	async(function()
		p.store.client:verify()
		return p.store:get(id)
	end, function(err, task)
		if err then
			notify(api.message(err), vim.log.levels.ERROR)
			return
		end
		local buf = find_doc(p, id) or make_doc(p, document.fields(task), { base = task })
		-- An arriving response cannot replace a window the operator has repurposed.
		if
			vim.api.nvim_win_is_valid(win)
			and open_requests[win] == generation
			and vim.api.nvim_win_get_buf(win) == original
			and vim.api.nvim_buf_get_changedtick(original) == tick
		then
			vim.api.nvim_win_set_buf(win, buf)
			if vim.api.nvim_get_current_win() == source_win then
				vim.api.nvim_set_current_win(win)
			end
		end
	end)
end

function M.new(parent, name)
	local p = project(name)
	local buf = make_doc(p, {
		title = "New task",
		description = "\n## Problem\n\n## Outcome\n\n## Scope\n\n## Constraints\n\n## Source links\n",
		acceptance_criteria = "\n- [ ] ",
	}, { parent = parent })
	display(p, buf)
	return buf
end

function M.relationships(name)
	local p = project(name)
	local id = assert(selected(p), "Select a task")
	async(function()
		p.store.client:verify()
		local all = p.store:list()
		local result = {}
		for _, edge in ipairs(all.edges) do
			if edge.issue_id == id or edge.depends_on_id == id then
				result[#result + 1] = {
					id = edge.issue_id == id and edge.depends_on_id or edge.issue_id,
					label = edge.issue_id == id and (edge.type .. " → " .. edge.depends_on_id)
						or (edge.type .. " ← " .. edge.issue_id),
				}
			end
		end
		return result
	end, function(err, edges)
		if err then
			notify(api.message(err), vim.log.levels.ERROR)
			return
		end
		vim.ui.select(edges, {
			prompt = "Relationships of " .. id,
			format_item = function(edge)
				return edge.label
			end,
		}, function(edge)
			if edge then
				M.open(edge.id, p.name)
			end
		end)
	end)
end

function M.status(status, name)
	local p = project(name)
	local id = assert(selected(p), "Select a task")
	local buf, doc = find_doc(p, id)
	assert(
		not doc or not doc.saving and not vim.bo[buf].modified,
		"Save or resolve the task document before changing status"
	)
	async(function()
		p.store.client:verify()
		local before = doc and doc.base or p.store:get(id)
		local body = { actor = p.settings.actor or "nvim", expected_version = before.revision }
		local result
		if status == "closed" then
			body.force = false
			result = p.store.client:call("closeIssue", { path = { id = id }, body = body })
		elseif status == "open" then
			result = p.store.client:call("reopenIssue", { path = { id = id }, body = body })
			if result.already_open and before.status ~= "open" then
				body.expected_version = result.revision
				body.expected_status, body.expected_assignee, body.patch =
					before.status, before.assignee or "", { status = status }
				result = p.store.client:call("updateIssue", { path = { id = id }, body = body })
			end
		else
			body.expected_status, body.expected_assignee, body.patch =
				before.status, before.assignee or "", { status = status }
			result = p.store.client:call("updateIssue", { path = { id = id }, body = body })
		end
		if doc then
			doc.base = vim.tbl_extend(
				"force",
				before,
				{ revision = result.revision, status = result.issue and result.issue.status or status }
			)
		end
	end, function(err)
		if err then
			notify(api.message(err), vim.log.levels.ERROR)
			return
		end
		if doc and vim.api.nvim_buf_is_valid(buf) then
			bind(doc)
		end
		M.refresh(p.name)
	end)
end

function M.recover(name)
	local p = project(name)
	local pending = p.store:pending()
	if #pending == 0 then
		notify("No pending creations")
		return
	end
	vim.ui.select(pending, {
		prompt = "Pending creations (opens retained draft)",
		format_item = function(item)
			return item.receipt.fields.title .. " · " .. item.receipt.target
		end,
	}, function(item)
		if not item then
			return
		end
		local buf = find_doc(p, item.receipt.target)
		if not buf then
			buf = make_doc(p, item.receipt.fields, {
				parent = item.receipt.parent,
				marker = item.receipt.marker,
				lines = item.receipt.lines,
				pending = item.receipt,
				receipt_path = item.path,
			})
		end
		display(p, buf)
		notify("Retained draft opened; :write reconciles without another create request")
	end)
end

function M.explorer(name)
	local p = project(name)
	active = p.name
	p.edit_win = vim.api.nvim_get_current_win()
	ui.setup()
	if not p.tree_buf or not vim.api.nvim_buf_is_valid(p.tree_buf) then
		p.tree_buf = vim.api.nvim_create_buf(false, true)
		vim.api.nvim_buf_set_name(p.tree_buf, "beads-tree://" .. p.name)
		vim.bo[p.tree_buf].filetype = "beads"
		vim.bo[p.tree_buf].bufhidden = "hide"
		vim.b[p.tree_buf].focus_disable = true
		local function map(key, callback)
			vim.keymap.set("n", key, function()
				local ok, err = pcall(callback)
				if not ok then
					notify(api.message(err), vim.log.levels.ERROR)
				end
			end, { buffer = p.tree_buf, silent = true })
		end
		map("<CR>", function()
			M.open(nil, p.name)
		end)
		map("o", function()
			M.open(nil, p.name)
		end)
		local function expand(value)
			local id = selected(p)
			if id then
				p.selection = id
				p.expanded[id] = value == nil and not p.expanded[id] or value
				render(p)
			end
		end
		map("l", function()
			expand(true)
		end)
		map("h", function()
			local id = selected(p)
			if id and p.expanded[id] then
				expand(false)
			elseif id then
				p.selection = p.parents[id]
				render(p)
			end
		end)
		map("<Tab>", function()
			expand(nil)
		end)
		map("a", function()
			M.new(assert(selected(p), "Select a parent"), p.name)
		end)
		map("A", function()
			M.new(nil, p.name)
		end)
		map("r", function()
			M.refresh(p.name)
		end)
		map("gr", function()
			M.relationships(p.name)
		end)
		map("s", function()
			vim.ui.input({ prompt = "Beads status: " }, function(value)
				if value and value ~= "" then
					M.status(value, p.name)
				end
			end)
		end)
		map("?", function()
			notify(
				"j/k move · l/h expand/collapse · <CR> open · a child · A root · s status · gr relationships · r refresh · q close"
			)
		end)
		vim.api.nvim_create_autocmd("CursorMoved", {
			buffer = p.tree_buf,
			callback = function()
				ui.select(p, vim.api.nvim_get_current_win())
			end,
		})
		vim.api.nvim_create_autocmd("BufWipeout", {
			buffer = p.tree_buf,
			once = true,
			callback = function()
				p.widget = nil
			end,
		})
		map("q", function()
			vim.api.nvim_win_close(0, false)
		end)
	end
	local wins = vim.fn.win_findbuf(p.tree_buf)
	local win
	for _, candidate in ipairs(wins) do
		if vim.api.nvim_win_get_tabpage(candidate) == vim.api.nvim_get_current_tabpage() then
			win = candidate
			break
		end
	end
	local sidebar_width = math.min(52, math.max(26, math.floor(vim.o.columns * 0.38)))
	if not win then
		-- A fixed sidebar must also fit when the user's normal-window minimum is wide.
		local minimum, focus_disabled = vim.o.winminwidth, vim.g.focus_disable
		vim.g.focus_disable = true
		vim.o.winminwidth = 1
		local ok, result = pcall(vim.api.nvim_open_win, p.tree_buf, true, { split = "left", win = 0 })
		vim.g.focus_disable = focus_disabled
		vim.o.winminwidth = math.min(minimum, vim.o.winwidth, sidebar_width)
		assert(ok, result)
		win = result
	end
	vim.api.nvim_set_current_win(win)
	vim.api.nvim_win_set_width(win, sidebar_width)
	ui.window(win)
	render(p)
	M.refresh(p.name)
end

-- Explicit reload is the escape from a stale base; refresh never adopts one silently.
function M.reload(force)
	local doc = assert(documents[vim.api.nvim_get_current_buf()], "Open a task document")
	assert(doc.base and not doc.pending and not doc.saving, "Resolve pending saves before reloading")
	assert(
		force or not vim.bo[doc.buf].modified,
		"Export/copy your edits first, then use :BeadsReload! to replace them"
	)
	local tick = vim.api.nvim_buf_get_changedtick(doc.buf)
	async(function()
		doc.project.store.client:verify()
		return doc.project.store:get(doc.base.id)
	end, function(err, task)
		if err then
			notify(api.message(err), vim.log.levels.ERROR)
			return
		end
		if
			not vim.api.nvim_buf_is_valid(doc.buf)
			or doc.saving
			or vim.api.nvim_buf_get_changedtick(doc.buf) ~= tick
		then
			notify("Document changed while reloading; edits retained", vim.log.levels.WARN)
			return
		end
		doc.base = task
		vim.api.nvim_buf_set_lines(doc.buf, 0, -1, false, document.render(document.fields(task), doc.marker))
		vim.bo[doc.buf].modified = false
		vim.b[doc.buf].beads_error = nil
		bind(doc)
	end)
end

local function add_project(name, settings)
	if projects[name] then
		assert(
			vim.deep_equal(projects[name].settings, settings),
			"Cannot reconfigure an active Beads project; restart Neovim"
		)
	else
		projects[name] = {
			name = name,
			settings = settings,
			store = require("beads.store").new(settings),
			graph = { items = {}, edges = {} },
			rows = {},
			expanded = {},
			generation = 0,
		}
	end
end

local function invoke(callback, ...)
	local ok, err = pcall(callback, ...)
	if not ok then
		notify(api.message(err), vim.log.levels.ERROR)
	end
end

local function with_project(callback, args)
	if active or next(projects) then
		invoke(callback, args)
		return
	end
	if discovering then
		notify("Local service discovery is in progress.", vim.log.levels.WARN)
		return
	end
	local win, buf = vim.api.nvim_get_current_win(), vim.api.nvim_get_current_buf()
	discovering = true
	async(require("beads.discovery").local_project, function(err, found)
		discovering = false
		if err then
			notify(api.message(err), vim.log.levels.ERROR)
			return
		end
		invoke(function()
			if not active and not next(projects) then
				add_project(found.name, found.settings)
				active = found.name
			end
			if vim.api.nvim_get_current_win() ~= win or vim.api.nvim_get_current_buf() ~= buf then
				notify("Local project discovered. Run the Beads command again in its intended window.")
				return
			end
			callback(args)
		end)
	end)
end

function M.setup(options)
	options = options or {}
	for name, settings in pairs(options.projects or {}) do
		add_project(name, settings)
	end
	active = options.default_project or active
	if not active then
		local names = vim.tbl_keys(projects)
		table.sort(names)
		active = names[1]
	end
	local function command(name, callback, opts)
		vim.api.nvim_create_user_command(name, function(args)
			if name == "BeadsProjects" then
				invoke(callback)
			else
				with_project(callback, args.args)
			end
		end, vim.tbl_extend("force", { force = true }, opts or {}))
	end
	command("Beads", M.explorer, {
		nargs = "?",
		complete = function(lead)
			return prefix_candidates(vim.tbl_keys(projects), lead)
		end,
	})
	command("BeadsProjects", M.projects)
	command("BeadsOpen", M.open, { nargs = "?", complete = complete_ids })
	command("BeadsNew", function(parent)
		M.new(parent ~= "" and parent or nil)
	end, { nargs = "?", complete = complete_ids })
	command("BeadsRefresh", function()
		M.refresh()
	end)
	command("BeadsStatus", M.status, { nargs = 1 })
	command("BeadsRelationships", function()
		M.relationships()
	end)
	command("BeadsRecover", function()
		M.recover()
	end)
	vim.api.nvim_create_user_command("BeadsReload", function(args)
		invoke(M.reload, args.bang)
	end, { bang = true, force = true })
end

return M
