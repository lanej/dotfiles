local M = {}
local active

local function begin()
	if active then
		active.cancel()
	end
	local ctx = {
		buf = vim.api.nvim_get_current_buf(),
		win = vim.api.nvim_get_current_win(),
		cursor = vim.api.nvim_win_get_cursor(0),
		tick = vim.api.nvim_buf_get_changedtick(0),
		word = vim.fn.expand("<cword>"),
		pending = {},
	}
	ctx.root = vim.fs.root(ctx.buf, { ".git" })
	ctx.cwd = ctx.root or vim.fs.dirname(vim.api.nvim_buf_get_name(ctx.buf)) or vim.fn.getcwd()
	function ctx.cancel()
		ctx.cancelled = true
		for cancel in pairs(ctx.pending) do
			cancel()
		end
		ctx.pending = {}
	end
	function ctx.current(focus)
		return not ctx.cancelled
			and vim.api.nvim_win_is_valid(ctx.win)
			and vim.api.nvim_win_get_buf(ctx.win) == ctx.buf
			and vim.api.nvim_buf_get_changedtick(ctx.buf) == ctx.tick
			and vim.deep_equal(vim.api.nvim_win_get_cursor(ctx.win), ctx.cursor)
			and (not focus or vim.api.nvim_get_current_win() == ctx.win)
	end
	active = ctx
	return ctx
end

-- One request per supporting client. The deadline closes this request group;
-- cancellation and late replies cannot start a second fallback or jump.
local function request(ctx, method, params, done)
	local clients = vim.tbl_filter(function(client)
		return client.initialized and not client:is_stopped() and client:supports_method(method, ctx.buf)
	end, vim.lsp.get_clients({ bufnr = ctx.buf }))
	local remaining, finished, results = #clients, false, {}
	local cancels = {}
	local cancel
	local function finish()
		if finished then
			return
		end
		finished = true
		ctx.pending[cancel] = nil
		for _, cancel in ipairs(cancels) do
			cancel()
		end
		if ctx.current(false) then
			done(results)
		end
	end
	cancel = function()
		finished = true
		ctx.pending[cancel] = nil
		for _, stop in ipairs(cancels) do
			stop()
		end
	end
	ctx.pending[cancel] = true
	if remaining == 0 then
		finish()
		return cancel
	end
	vim.defer_fn(finish, 1500)
	for _, client in ipairs(clients) do
		local accepted, id = client:request(method, params(client), function(err, result)
			if finished or ctx.cancelled then
				return
			end
			if err then
				vim.notify(client.name .. ": " .. (err.message or tostring(err)), vim.log.levels.WARN)
			elseif result then
				local list = vim.islist(result) and result or { result }
				for _, item in ipairs(list) do
					table.insert(results, { value = item, encoding = client.offset_encoding })
				end
			end
			remaining = remaining - 1
			if remaining == 0 then
				finish()
			end
		end, ctx.buf)
		if accepted then
			table.insert(cancels, function()
				client:cancel_request(id)
			end)
		else
			remaining = remaining - 1
		end
	end
	if remaining == 0 then
		finish()
	end
	return cancel
end

local function locations(results)
	local items, seen = {}, {}
	for _, result in ipairs(results) do
		local loc = result.value
		local uri, range = loc.uri or loc.targetUri, loc.targetSelectionRange or loc.range
		if uri and range then
			local position = vim.lsp.util.locations_to_items({ loc }, result.encoding)[1]
			local key = position.filename .. ":" .. position.lnum .. ":" .. position.col
			if not seen[key] then
				seen[key] = true
				table.insert(items, { label = key, location = loc, encoding = result.encoding })
			end
		end
	end
	return items
end

local function open(item, ctx)
	if not item or not ctx.current(true) then
		return
	end
	if item.location then
		vim.lsp.util.show_document(item.location, item.encoding, { focus = true })
		return
	end
	vim.cmd("normal! m'")
	if vim.api.nvim_buf_get_name(0) ~= item.filename then
		vim.cmd.edit(vim.fn.fnameescape(item.filename))
	end
	if item.row then
		vim.api.nvim_win_set_cursor(0, { item.row, item.col or 0 })
	elseif tonumber(item.cmd) then
		vim.api.nvim_win_set_cursor(0, { tonumber(item.cmd), 0 })
	else
		-- Ctags search addresses are patterns, never Ex commands to execute.
		local delimiter = item.cmd:sub(1, 1)
		if delimiter == "/" or delimiter == "?" then
			local pattern = "\\M" .. item.cmd:sub(2, -2):gsub("\\" .. delimiter, delimiter)
			vim.api.nvim_win_set_cursor(0, { 1, 0 })
			vim.fn.search(pattern, "cw")
		end
	end
end

local function pick(ctx, items, title, jump)
	if not ctx.current(true) then
		return
	end
	if #items == 0 then
		vim.notify("No " .. title:lower() .. " found", vim.log.levels.INFO)
		return
	end
	if jump and #items == 1 then
		open(items[1], ctx)
		return
	end
	require("fzf-lua").register_ui_select(nil, true)
	vim.ui.select(items, {
		prompt = title,
		format_item = function(item)
			return item.label
		end,
	}, function(item)
		open(item, ctx)
	end)
end

local function tags(ctx, word, buffer_only)
	if not ctx.root then
		return {}
	end
	local pattern = word and ("\\C^" .. vim.fn.escape(word, [[\.^$~[]*]]) .. "$") or ".*"
	local ok, matches = pcall(vim.api.nvim_buf_call, ctx.buf, function()
		-- taglist otherwise invokes vim.lsp.tagfunc, issuing a second LSP
		-- request at precisely the point where we are falling back from LSP.
		local tagfunc = vim.bo.tagfunc
		vim.bo.tagfunc = ""
		local success, result = pcall(vim.fn.taglist, pattern)
		vim.bo.tagfunc = tagfunc
		if not success then
			error(result)
		end
		return result
	end)
	if not ok then
		vim.notify("Tags: " .. tostring(matches), vim.log.levels.WARN)
		return {}
	end
	local items, seen = {}, {}
	local current = vim.fs.normalize(vim.api.nvim_buf_get_name(ctx.buf))
	for _, tag in ipairs(matches) do
		local filename = vim.fs.normalize(vim.fn.fnamemodify(tag.filename, ":p"))
		if filename:sub(1, #ctx.root + 1) == ctx.root .. "/" and (not buffer_only or filename == current) then
			local key = filename .. ":" .. tag.cmd .. ":" .. tag.name
			if not seen[key] then
				seen[key] = true
				table.insert(items, {
					filename = filename,
					cmd = tag.cmd,
					label = tag.name .. " · " .. vim.fs.relpath(ctx.root, filename),
				})
			end
		end
	end
	return items
end

local function text_search(ctx, title)
	if ctx.word == "" or not ctx.current(true) then
		return
	end
	require("fzf-lua").grep({
		cwd = ctx.cwd,
		search = ctx.word,
		rg_opts = "--column --line-number --no-heading --color=always --smart-case --hidden --glob=!.git --fixed-strings --word-regexp",
		prompt = title .. " · Text matches❯ ",
	})
end

local function lookup(method, title, use_tags)
	local ctx = begin()
	request(ctx, method, function(client)
		local params = vim.lsp.util.make_position_params(ctx.win, client.offset_encoding)
		if method == "textDocument/references" then
			params.context = { includeDeclaration = false }
		end
		return params
	end, function(results)
		local items = locations(results)
		if #items > 0 then
			pick(ctx, items, title .. " · LSP", true)
			return
		end
		if use_tags and ctx.word ~= "" then
			items = tags(ctx, ctx.word)
			if #items > 0 then
				pick(ctx, items, title .. " · Tags", true)
				return
			end
		end
		text_search(ctx, title)
	end)
end

function M.goto_definition()
	lookup("textDocument/definition", "Definitions", true)
end
function M.references()
	lookup("textDocument/references", "References", false)
end
function M.implementations()
	lookup("textDocument/implementation", "Implementations", false)
end

local function document_symbols(results, uri)
	local flattened = {}
	local function visit(symbol, encoding)
		if symbol.location then
			table.insert(flattened, { value = symbol.location, encoding = encoding })
			flattened[#flattened].name = symbol.name
		elseif symbol.selectionRange or symbol.range then
			table.insert(flattened, {
				value = { uri = uri, range = symbol.selectionRange or symbol.range },
				encoding = encoding,
				name = symbol.name,
			})
		end
		for _, child in ipairs(symbol.children or {}) do
			visit(child, encoding)
		end
	end
	for _, result in ipairs(results) do
		visit(result.value, result.encoding)
	end
	local items = locations(flattened)
	for _, item in ipairs(items) do
		for _, result in ipairs(flattened) do
			if result.value == item.location then
				item.label = (result.name or "") .. " · " .. item.label
				break
			end
		end
	end
	return items
end

local function treesitter(ctx)
	local items, seen = {}, {}
	local ok = pcall(function()
		local parser = vim.treesitter.get_parser(ctx.buf)
		local lang = parser:lang()
		local query = vim.treesitter.query.get(lang, "locals")
		if not query then
			return
		end
		for _, tree in ipairs(parser:parse()) do
			for id, node in query:iter_captures(tree:root(), ctx.buf) do
				if query.captures[id]:match("^local%.definition") then
					local row, col = node:range()
					local key = row .. ":" .. col
					if not seen[key] then
						seen[key] = true
						table.insert(items, {
							filename = vim.api.nvim_buf_get_name(ctx.buf),
							row = row + 1,
							col = col,
							label = vim.treesitter.get_node_text(node, ctx.buf) .. " · " .. (row + 1),
						})
					end
				end
			end
		end
	end)
	return ok and items or {}
end

function M.buffer_symbols()
	local ctx = begin()
	request(ctx, "textDocument/documentSymbol", function()
		return { textDocument = { uri = vim.uri_from_bufnr(ctx.buf) } }
	end, function(results)
		local items = document_symbols(results, vim.uri_from_bufnr(ctx.buf))
		if #items > 0 then
			pick(ctx, items, "Buffer symbols · LSP")
			return
		end
		items = treesitter(ctx)
		if #items > 0 then
			pick(ctx, items, "Buffer symbols · Tree-sitter")
			return
		end
		pick(ctx, tags(ctx, nil, true), "Buffer symbols · Tags (saved)")
	end)
end

function M.workspace_symbols()
	local ctx = begin()
	local generation, cancel, entries = 0, nil, {}
	require("fzf-lua").fzf_live(function(args)
		generation = generation + 1
		local current = generation
		if cancel then
			cancel()
		end
		return function(cb)
			vim.defer_fn(function()
				if current ~= generation or not ctx.current(false) then
					cb(nil)
					return
				end
				cancel = request(ctx, "workspace/symbol", function()
					return { query = args[1] or "" }
				end, function(results)
					if current ~= generation then
						cb(nil)
						return
					end
					local items = document_symbols(results)
					local source = "LSP"
					if #items == 0 then
						items, source = tags(ctx), "Tags"
						local query = args[1] or ""
						if query ~= "" then
							items = vim.fn.matchfuzzy(items, query, { key = "label" })
						end
					end
					for _, item in ipairs(items) do
						local id = tostring(#entries + 1)
						entries[#entries + 1] = item
						cb(id .. "\t[" .. source .. "] " .. item.label)
					end
					cb(nil)
				end)
			end, 200)
		end
	end, {
		prompt = "Workspace symbols❯ ",
		previewer = false,
		fzf_opts = { ["--delimiter"] = "\t", ["--with-nth"] = "2..", ["--no-multi"] = true },
		winopts = {
			on_close = function()
				generation = generation + 1
				if cancel then
					cancel()
				end
			end,
		},
		actions = {
			["default"] = function(selected)
				local id = selected[1] and tonumber(selected[1]:match("^(%d+)\t"))
				if id then
					open(entries[id], ctx)
				end
			end,
		},
	})
end

return M
