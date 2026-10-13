local M = {}

local function name(node, source)
	return vim.treesitter.get_node_text(node, source):gsub("`", ""):gsub("%s*%.%s*", ".")
end

local function location(node, path)
	local row, col, end_row, end_col = node:range()
	return {
		uri = vim.uri_from_fname(path),
		range = {
			start = { line = row, character = col },
			["end"] = { line = end_row, character = end_col },
		},
	}
end

local function cte_definition(node, target, source, path)
	local row, col = node:range()
	local scope = node:parent()
	while scope do
		if scope:type() == "query_expr" then
			for child in scope:iter_children() do
				if child:type() == "cte_clause" then
					local recursive = false
					for entry in child:iter_children() do
						recursive = recursive or entry:type() == "with_recursive_keyword"
					end
					for entry in child:iter_children() do
						if entry:type() == "cte" then
							-- Nonrecursive CTEs can see earlier siblings, never themselves or later siblings.
							if not recursive and vim.treesitter.is_in_node_range(entry, row, col) then
								break
							end
							local alias = entry:field("alias_name")[1]
							if alias and name(alias, source):lower() == target:lower() then
								return location(alias, path)
							end
						end
					end
				end
			end
		end
		scope = scope:parent()
	end
end

local function ddl_column_definition(node, source, path)
	local clause = node:parent()
	while clause and clause:type() ~= "table_cluster_clause" and clause:type() ~= "table_partition_clause" do
		clause = clause:parent()
	end
	local statement = clause and clause:parent()
	if
		not statement
		or (statement:type() ~= "create_table_statement" and statement:type() ~= "create_table_like_statement")
	then
		return
	end
	local target = name(node, source):lower()
	for _, column in ipairs(require("bigquery-ddl").columns(statement, source)) do
		if column.name:lower() == target then
			return location(column.node, path)
		end
	end
end

local function current(ctx)
	return vim.api.nvim_win_is_valid(ctx.win)
		and vim.api.nvim_get_current_win() == ctx.win
		and vim.api.nvim_win_get_buf(ctx.win) == ctx.buf
		and vim.api.nvim_buf_get_changedtick(ctx.buf) == ctx.tick
		and vim.deep_equal(vim.api.nvim_win_get_cursor(ctx.win), ctx.cursor)
end

local function jump(ctx, loc, encoding)
	if current(ctx) then
		vim.api.nvim_set_current_win(ctx.win)
		vim.lsp.util.show_document(loc, encoding or "utf-8", { focus = true })
	end
end

local function choose(ctx, locations, encoding)
	if #locations == 1 and not locations[1].candidate then
		jump(ctx, locations[1], encoding)
	elseif #locations > 0 and current(ctx) then
		vim.ui.select(locations, {
			prompt = "Choose SQL definition:",
			format_item = function(loc)
				local uri = loc.uri or loc.targetUri
				local range = loc.range or loc.targetSelectionRange
				local path = vim.fn.fnamemodify(vim.uri_to_fname(uri), ":~:.") .. ":" .. (range.start.line + 1)
				return loc.declared_name and (loc.declared_name .. " (" .. path .. ")") or path
			end,
		}, function(loc)
			if loc then
				jump(ctx, loc, encoding)
			end
		end)
	end
end

local function schema(ctx, client, params, target)
	client:request("textDocument/hover", params, function(err, result)
		if not current(ctx) then
			return
		end
		if err then
			vim.notify(err.message, vim.log.levels.WARN)
			return
		end
		local lines = result and result.contents and vim.lsp.util.convert_input_to_markdown_lines(result.contents) or {}
		if #lines == 0 then
			vim.notify("No definition found", vim.log.levels.INFO)
			return
		end
		lines = require("markdown-tables").align(lines)
		local buf = vim.api.nvim_create_buf(false, true)
		vim.api.nvim_buf_set_name(buf, "BigQuery schema: " .. target .. " [" .. buf .. "]")
		vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
		vim.bo[buf].bufhidden = "wipe"
		vim.bo[buf].filetype = "markdown"
		vim.bo[buf].modifiable = false
		vim.bo[buf].readonly = true
		vim.api.nvim_set_current_win(ctx.win)
		vim.cmd("normal! m'")
		vim.api.nvim_win_set_buf(ctx.win, buf)
	end, ctx.buf)
end

local function lsp_definition(ctx, target)
	if not current(ctx) then
		return
	end
	local client = vim.lsp.get_clients({ name = "bqls", bufnr = ctx.buf })[1]
	if not client or not client.initialized then
		vim.notify("bqls is not ready for definition lookup", vim.log.levels.INFO)
		return
	end
	local params = vim.lsp.util.make_position_params(ctx.win, client.offset_encoding)
	if target then
		schema(ctx, client, params, target)
		return
	end
	client:request("textDocument/definition", params, function(err, result)
		if not current(ctx) then
			return
		end
		if err then
			vim.notify(err.message, vim.log.levels.WARN)
			return
		end
		local locations = result and (vim.islist(result) and result or { result }) or {}
		local files = {}
		for _, loc in ipairs(locations) do
			local uri = loc.uri or loc.targetUri
			if uri and not uri:match("^bqls://") then
				files[#files + 1] = loc
			end
		end
		if #files > 0 then
			choose(ctx, files, client.offset_encoding)
		else
			vim.notify("No definition found", vim.log.levels.INFO)
		end
	end, ctx.buf)
end

local function local_tables(ctx, target, done)
	local path = vim.api.nvim_buf_get_name(ctx.buf)
	local root = vim.fs.root(path, ".git") or vim.fs.dirname(path)
	vim.system({ "rg", "--files", "-0", "--iglob", "*.sql", "--iglob", "*.bqsql", root }, {}, function(result)
		vim.schedule(function()
			if not current(ctx) then
				return
			end
			if result.code ~= 0 and result.code ~= 1 then
				vim.notify("SQL definition search failed: " .. (result.stderr or ""), vim.log.levels.WARN)
				return
			end
			local paths = { [path] = true }
			for candidate in (result.stdout or ""):gmatch("[^%z]+") do
				paths[candidate] = true
			end
			for _, buf in ipairs(vim.api.nvim_list_bufs()) do
				local candidate = vim.api.nvim_buf_get_name(buf)
				if
					vim.api.nvim_buf_is_loaded(buf)
					and candidate:sub(1, #root + 1) == root .. "/"
					and (candidate:lower():match("%.sql$") or candidate:lower():match("%.bqsql$"))
				then
					paths[candidate] = true
				end
			end
			local query = vim.treesitter.query.parse(
				"sql_bigquery",
				"[(create_table_statement table_name: (identifier) @definition)"
					.. " (create_table_like_statement table_name: (identifier) @definition)]"
			)
			local exact, candidates = {}, {}
			for _, candidate in ipairs(vim.tbl_keys(paths)) do
				local buf = vim.fn.bufnr(candidate)
				local source
				if buf ~= -1 and vim.api.nvim_buf_is_loaded(buf) then
					source = table.concat(vim.api.nvim_buf_get_lines(buf, 0, -1, false), "\n")
				else
					local ok, lines = pcall(vim.fn.readfile, candidate)
					source = ok and table.concat(lines, "\n") or nil
				end
				if source then
					local parser = vim.treesitter.get_string_parser(source, "sql_bigquery")
					for _, definition in query:iter_captures(parser:parse()[1]:root(), source) do
						local declared = name(definition, source)
						if declared == target then
							exact[#exact + 1] = location(definition, candidate)
						elseif declared:sub(-#target - 1) == "." .. target then
							local loc = location(definition, candidate)
							loc.candidate = true
							loc.declared_name = declared
							candidates[#candidates + 1] = loc
						end
					end
				end
			end
			local locations = #exact > 0 and exact or candidates
			table.sort(locations, function(a, b)
				return a.uri < b.uri or (a.uri == b.uri and a.range.start.line < b.range.start.line)
			end)
			done(locations)
		end)
	end)
end

function M.goto_definition()
	local ctx = {
		buf = vim.api.nvim_get_current_buf(),
		win = vim.api.nvim_get_current_win(),
		cursor = vim.api.nvim_win_get_cursor(0),
		tick = vim.api.nvim_buf_get_changedtick(0),
	}
	local parser = vim.treesitter.get_parser(ctx.buf, "sql_bigquery")
	parser:parse()
	local node = vim.treesitter.get_node({ bufnr = ctx.buf, ignore_injections = true })
	while node and node:type() ~= "identifier" do
		node = node:parent()
	end
	local target
	if node then
		local column = ddl_column_definition(node, ctx.buf, vim.api.nvim_buf_get_name(ctx.buf))
		if column then
			jump(ctx, column)
			return
		end
		local parent = node:parent()
		for _, field in ipairs({ "table_name", "source_table_name", "referenced_table_name", "new_table_name" }) do
			local table_node = parent and parent:field(field)[1]
			if table_node and table_node:id() == node:id() then
				target = name(node, ctx.buf)
				break
			end
		end
	end
	if not target then
		lsp_definition(ctx)
		return
	end
	local cte = cte_definition(node, target, ctx.buf, vim.api.nvim_buf_get_name(ctx.buf))
	if cte then
		jump(ctx, cte)
		return
	end
	local_tables(ctx, target, function(locations)
		if #locations > 0 then
			choose(ctx, locations)
		else
			-- Scoped CTE lookup has already run; table hover fetches schema without
			-- the server's document-wide CTE matching or its table preview rows.
			lsp_definition(ctx, target)
		end
	end)
end

return M
