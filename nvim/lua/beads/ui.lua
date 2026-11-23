local M = {}
local initialized = false
local document_windows = {}
local trees = {}
local namespace = vim.api.nvim_create_namespace("beads-sidebar")

M.states = {
	open = { icon = "", label = "Open", highlight = "BeadsOpen" },
	in_progress = { icon = "󰐊", label = "In progress", highlight = "BeadsProgress" },
	blocked = { icon = "", label = "Blocked", highlight = "BeadsBlocked" },
	deferred = { icon = "󰥔", label = "Deferred", highlight = "BeadsDeferred" },
	closed = { icon = "", label = "Closed", highlight = "BeadsClosed" },
}

function M.plain(text)
	return tostring(text):gsub("[%c]", " ")
end

local function highlights()
	local colors = require("dotfiles-theme").colors()
	local groups = {
		BeadsNormal = { link = "Normal" },
		BeadsHeader = { fg = colors["text.strong"], bold = true },
		BeadsRoot = { fg = colors.accent, bold = true },
		BeadsSummary = { fg = colors["text.muted"] },
		BeadsGuide = { fg = colors["text.muted"] },
		BeadsParent = { fg = colors["text.strong"], bold = true },
		BeadsTask = { fg = colors.text },
		BeadsOpen = { fg = colors["text.muted"], bold = true },
		BeadsProgress = { fg = colors["status.info"], bold = true },
		BeadsBlocked = { fg = colors["status.error"], bold = true },
		BeadsDeferred = { fg = colors["status.idle"], bold = true },
		BeadsClosed = { fg = colors["status.success"], bold = true },
		BeadsAttention = { fg = colors["status.attention"], bold = true },
		BeadsWarning = { fg = colors["status.warning"], bold = true },
		BeadsCursorLine = { bg = colors["selection.bg"] },
		BeadsSelected = { fg = colors["selection.fg"], bg = colors["selection.bg"], bold = true },
		BeadsFocus = { fg = colors.focus, bold = true },
		BeadsKey = { fg = colors.keyhint, bold = true },
		BeadsFooter = { fg = colors["text.muted"] },
		BeadsMetadata = { fg = colors["text.muted"] },
	}
	for name, style in pairs(groups) do
		vim.api.nvim_set_hl(0, name, style)
	end
end

function M.setup()
	if initialized then
		return
	end
	initialized = true
	highlights()
	vim.api.nvim_create_autocmd("ColorScheme", {
		group = vim.api.nvim_create_augroup("BeadsAppearance", { clear = true }),
		callback = highlights,
	})
	vim.api.nvim_create_autocmd("WinResized", {
		group = "BeadsAppearance",
		callback = function()
			for buf, project in pairs(trees) do
				if vim.api.nvim_buf_is_valid(buf) and project.widget then
					M.render(project)
					for _, win in ipairs(vim.fn.win_findbuf(buf)) do
						M.select(project, win)
					end
				else
					trees[buf] = nil
				end
			end
		end,
	})
end

local function append(line, text, highlight)
	line:append(text, { hl_group = highlight, hl_mode = "combine" })
end

local function truncate(text, width)
	if width <= 0 then
		return ""
	end
	if vim.fn.strdisplaywidth(text) <= width then
		return text
	end
	local low, high, count = 0, vim.fn.strchars(text), 0
	while low <= high do
		local middle = math.floor((low + high) / 2)
		if vim.fn.strdisplaywidth(vim.fn.strcharpart(text, 0, middle)) <= width - 1 then
			count, low = middle, middle + 1
		else
			high = middle - 1
		end
	end
	return vim.fn.strcharpart(text, 0, count) .. "…"
end

local function width(p)
	local wins = vim.fn.win_findbuf(p.tree_buf)
	return #wins > 0 and vim.api.nvim_win_get_width(wins[1]) or 42
end

local function prepare(p, node)
	local Line = require("nui.line")
	local line = Line()
	if node.kind == "project" then
		append(line, "  󰉋  " .. M.plain(p.name), "BeadsRoot")
		local summary = Line()
		local blocked = 0
		for _, task in ipairs(p.graph.items) do
			if task.status == "blocked" then
				blocked = blocked + 1
			end
		end
		append(summary, "  " .. #p.graph.items .. " tasks", "BeadsSummary")
		if blocked > 0 then
			append(summary, "  ·  " .. blocked .. " blocked", "BeadsBlocked")
		end
		if p.loading then
			append(summary, "  ·  refreshing", "BeadsOpen")
		end
		if p.error then
			append(summary, "  ·  stale", "BeadsWarning")
		end
		return { line, summary, Line() }
	end
	if node.kind == "empty" then
		append(
			line,
			p.error and "  Unable to load tasks" or p.loading and "  Loading tasks…" or "  No tasks yet",
			p.error and "BeadsWarning" or "BeadsSummary"
		)
		local hint = Line()
		append(hint, p.error and "  r  Retry refresh" or p.loading and "" or "  A  Create a task", "BeadsKey")
		return { line, hint }
	end
	local guides = node.guides
	if node.depth > 8 then
		guides = "… " .. guides:sub(-18)
	end
	append(line, "  " .. guides .. (node.branch or ""), "BeadsGuide")
	append(line, node:has_children() and (node:is_expanded() and " " or " ") or "  ", "BeadsGuide")
	local state = M.states[node.task.status]
		or { icon = "", highlight = "BeadsDeferred", label = M.plain(node.task.status or "Unknown") }
	append(line, state.icon .. "  ", state.highlight)
	if not M.states[node.task.status] then
		append(line, "[" .. state.label .. "] ", state.highlight)
	end
	local attention = p.settings.attention and p.settings.attention(node.task) or nil
	local badge = attention and "   " .. M.plain(attention) or node.warning and "   " .. node.warning or ""
	if width(p) < 40 and badge ~= "" then
		badge = "  "
	end
	local available = math.max(1, width(p) - line:width() - math.min(vim.fn.strdisplaywidth(badge), 18) - 1)
	local style = node:has_children() and "BeadsParent" or "BeadsTask"
	node.title_col = #line:content()
	append(line, truncate(M.plain(node.task.title), available), style)
	node.title_end = #line:content()
	if badge ~= "" then
		append(
			line,
			truncate(badge, math.max(0, width(p) - line:width() - 1)),
			attention and "BeadsAttention" or "BeadsWarning"
		)
	end
	return line
end

function M.render(p)
	M.setup()
	trees[p.tree_buf] = p
	local Tree = require("nui.tree")
	local forest, parents = require("beads.tree").forest(p.graph)
	p.parents = parents
	local roots, all = {}, {}
	local stack = {}
	for index = #forest, 1, -1 do
		stack[#stack + 1] = { value = forest[index], into = roots }
	end
	while #stack > 0 do
		local entry = table.remove(stack)
		local data = entry.value
		local children = {}
		local node = Tree.Node({
			id = data.id,
			task = data.task,
			guides = data.guides,
			branch = data.branch,
			depth = data.depth,
			warning = data.warning,
		}, children)
		entry.into[#entry.into + 1] = node
		all[#all + 1] = node
		for index = #data.children, 1, -1 do
			stack[#stack + 1] = { value = data.children[index], into = children }
		end
	end
	for _, node in ipairs(all) do
		if p.expanded[node.id] then
			node:expand()
		end
	end
	if #roots == 0 then
		roots = { Tree.Node({ id = "@empty", kind = "empty" }) }
	end
	local root = Tree.Node({ id = "@project", kind = "project" }, roots)
	root:expand()
	if not p.widget then
		p.widget = Tree({
			bufnr = p.tree_buf,
			ns_id = namespace,
			get_node_id = function(node)
				return node.kind and "ui:" .. node.kind or "task:" .. node.id
			end,
			prepare_node = function(node)
				return prepare(p, node)
			end,
		})
	end
	p.widget:set_nodes({ root })
	p.widget:render()
	if not p.selection and roots[1].task then
		p.selection = roots[1].id
	end
	for _, win in ipairs(vim.fn.win_findbuf(p.tree_buf)) do
		local _, row = p.widget:get_node("task:" .. (p.selection or ""))
		if row then
			vim.api.nvim_win_set_cursor(win, { row, 0 })
		end
	end
end

function M.select(p, win)
	local node = p.widget and p.widget:get_node(vim.api.nvim_win_get_cursor(win)[1])
	if node and node.task then
		p.selection = node.id
		vim.b[p.tree_buf].beads_selection = node.id
		-- Nui owns node highlights; a separate namespace tracks the moving selection.
		local ns = vim.api.nvim_create_namespace("beads-selection")
		vim.api.nvim_buf_clear_namespace(p.tree_buf, ns, 0, -1)
		vim.api.nvim_buf_set_extmark(
			p.tree_buf,
			ns,
			vim.api.nvim_win_get_cursor(win)[1] - 1,
			0,
			{ line_hl_group = "BeadsCursorLine", priority = 90 }
		)
		vim.api.nvim_buf_set_extmark(p.tree_buf, ns, vim.api.nvim_win_get_cursor(win)[1] - 1, 0, {
			virt_text = { { "▎", "BeadsFocus" } },
			virt_text_pos = "overlay",
			priority = 220,
		})
		vim.api.nvim_buf_set_extmark(p.tree_buf, ns, vim.api.nvim_win_get_cursor(win)[1] - 1, node.title_col, {
			end_col = node.title_end,
			hl_group = "BeadsSelected",
			hl_mode = "combine",
			priority = 200,
		})
	end
end

function M.window(win)
	vim.wo[win].number, vim.wo[win].relativenumber, vim.wo[win].wrap = false, false, false
	vim.wo[win].signcolumn = "no"
	vim.wo[win].foldcolumn = "0"
	vim.wo[win].list = false
	vim.wo[win].winfixwidth = true
	vim.wo[win].cursorline = true
	vim.wo[win].cursorlineopt = "line"
	vim.wo[win].fillchars = "eob: "
	vim.wo[win].winhighlight =
		"Normal:BeadsNormal,NormalNC:BeadsNormal,CursorLine:BeadsCursorLine,EndOfBuffer:BeadsNormal,WinBar:BeadsHeader,WinBarNC:BeadsHeader,StatusLine:BeadsFooter,StatusLineNC:BeadsFooter"
	vim.wo[win].winbar = "%#BeadsRoot#  󰠮  %#BeadsHeader#TASKS"
	vim.wo[win].statusline =
		"%#BeadsKey#  <CR>%#BeadsFooter# open   %#BeadsKey#a%#BeadsFooter# child   %#BeadsKey#?%#BeadsFooter# help"
end

function M.leave_document(buf)
	local win = vim.api.nvim_get_current_win()
	local previous = document_windows[win]
	if previous and previous.buf == buf then
		for key, value in pairs(previous.options) do
			vim.wo[win][key] = value
		end
		document_windows[win] = nil
	end
end

function M.enter_document(buf)
	local win = vim.api.nvim_get_current_win()
	if document_windows[win] then
		M.leave_document(document_windows[win].buf)
	end
	local options = {}
	for _, key in ipairs({ "conceallevel", "concealcursor", "linebreak", "breakindent" }) do
		options[key] = vim.wo[win][key]
	end
	document_windows[win] = { buf = buf, options = options }
	vim.wo[win].conceallevel, vim.wo[win].concealcursor = 2, "nc"
	vim.wo[win].linebreak, vim.wo[win].breakindent = true, true
end

return M
