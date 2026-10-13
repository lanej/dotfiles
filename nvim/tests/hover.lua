-- Run through the installed configuration after Noice's VimEnter setup:
-- nvim --headless -i NONE '+lua dofile("nvim/tests/hover.lua")'
local function workflow()
	vim.o.columns = 150
	vim.o.lines = 40
	local source = { "SELECT address FROM shipments;" }
	vim.api.nvim_buf_set_lines(0, 0, -1, false, source)
	local contents = {
		kind = "markdown",
		value = table.concat({
			"Table: demo-project.dataset.shipments",
			"Destination addresses.",
			"",
			"| Name | Type | Mode | Description |",
			"| --- | --- | --- | --- |",
			"| `address` | RECORD | NULLABLE | destination |",
			"| &nbsp;&nbsp;city | STRING | REQUIRED | 東京 \\| city |",
			"",
			"```sql",
			"| code | untouched |",
			"| --- | --- |",
			"| x | y |",
			"```",
		}, "\n"),
	}
	local original = vim.deepcopy(contents)
	local request = vim.lsp.buf_request
	local sent = false
	vim.lsp.buf_request = function(_, method, _, callback)
		assert(method == "textDocument/hover", "Expected the hover request")
		sent = true
		callback(nil, { contents = contents }, { bufnr = vim.api.nvim_get_current_buf() })
	end
	vim.lsp.buf.hover()
	vim.lsp.buf_request = request
	assert(sent, "Hover bypassed the LSP entrypoint")
	local docs = require("noice.lsp.docs")
	assert(
		vim.wait(2000, function()
			return docs._messages.hover and docs._messages.hover:win() ~= nil
		end, 10),
		"Hover popup did not open"
	)
	local win = docs._messages.hover:win()
	local lines = vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(win), 0, -1, false)
	assert(lines[1] == "Table: demo-project.dataset.shipments", "Table title gained Markdown markers")
	local title_highlight = false
	for _, mark in ipairs(vim.api.nvim_buf_get_extmarks(vim.api.nvim_win_get_buf(win), -1, 0, -1, { details = true })) do
		if mark[2] == 0 and mark[3] == 0 and mark[4].hl_group == "@module" then
			title_highlight = true
		end
	end
	assert(title_highlight, "Table name is missing its semantic highlight")
	local boundaries
	for r = 4, 7 do
		local positions = {}
		for c in lines[r]:gmatch("()|") do
			if lines[r]:sub(c - 1, c - 1) ~= "\\" then
				positions[#positions + 1] = vim.fn.strdisplaywidth(lines[r]:sub(1, c - 1))
			end
		end
		assert(#positions == 5, "Schema row lost a cell")
		boundaries = boundaries or positions
		assert(vim.deep_equal(boundaries, positions), "Rendered table boundaries are misaligned")
	end
	assert(lines[7]:find("|   city", 1, true), "Nested field indentation was lost")
	assert(vim.tbl_contains(lines, "| code | untouched |"), "Fenced code was reformatted")
	assert(vim.wo[win].conceallevel == 0 and not vim.wo[win].wrap, "Popup options break column alignment")
	assert(vim.deep_equal(contents, original), "Hover modified the server response")
	assert(vim.deep_equal(source, vim.api.nvim_buf_get_lines(0, 0, -1, false)), "Hover modified the source")
	docs.on_close()
	assert(
		vim.wait(2000, function()
			return docs._messages.hover:win() == nil
		end, 10),
		"Table hover did not close"
	)

	local path = vim.fn.tempname() .. ".bqsql"
	vim.fn.writefile({}, path)
	vim.cmd.edit(path)
	assert(
		vim.wait(20000, function()
			local client = vim.lsp.get_clients({ name = "bqls", bufnr = 0 })[1]
			return client and client.initialized
		end, 100),
		"bqls did not attach for hover"
	)
	local declaration = {
		"CREATE TABLE types (",
		"  STRING STRING(36) OPTIONS(description = 'Journey\\'s identifier\\nUnicode: \\u6771'),",
		"  count INT64,",
		"  note ARRAY<STRUCT<`postal  code` STRING OPTIONS(description = 'Nested field documentation')>> OPTIONS(description = 'STRING outer notes')",
		");",
		"SELECT CAST(NULL AS STRUCT<STRING /* field name */ INT64>);",
	}
	vim.api.nvim_buf_set_lines(0, 0, -1, false, declaration)
	vim.bo.filetype = "sql.bigquery"
	vim.api.nvim_win_set_cursor(0, { 2, 9 })
	local hover = vim.lsp.buf.hover
	local forwarded = false
	vim.lsp.buf.hover = function()
		forwarded = true
		hover()
	end
	vim.cmd.normal("K")
	assert(forwarded, "Type hover did not request the language server")
	assert(
		vim.wait(2000, function()
			local popup = docs._messages.hover:win()
			if not popup then
				return false
			end
			local text = table.concat(vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(popup), 0, -1, false), "\n")
			return text:find("STRING(36)", 1, true)
				and text:find("Declared maximum: 36 Unicode characters.", 1, true)
				and text:find("Journey's identifier", 1, true)
				and text:find("Unicode: 東", 1, true)
		end, 10),
		"K did not show the parameterized STRING documentation"
	)
	assert(not docs._messages.hover.opts.markdown_table, "Type documentation retained schema-table rendering")
	assert(vim.deep_equal(declaration, vim.api.nvim_buf_get_lines(0, 0, -1, false)), "Type hover changed the SQL")
	docs.on_close()
	assert(
		vim.wait(2000, function()
			return docs._messages.hover:win() == nil
		end, 10),
		"STRING hover did not close"
	)
	vim.api.nvim_win_set_cursor(0, { 3, 11 })
	vim.cmd.normal("K")
	assert(forwarded, "Hovering a digit within INT64 missed the type")
	assert(
		vim.wait(2000, function()
			local popup = docs._messages.hover:win()
			return popup
				and table
					.concat(vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(popup), 0, -1, false), "\n")
					:find("Signed 64-bit integer.", 1, true)
		end, 10),
		"INT64 hover did not render"
	)
	docs.on_close()
	vim.api.nvim_win_set_cursor(0, { 2, 2 })
	vim.cmd.normal("K")
	assert(forwarded, "A local column name did not request the language server")
	assert(
		vim.wait(2000, function()
			local popup = docs._messages.hover:win()
			return popup
				and table
					.concat(vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(popup), 0, -1, false), "\n")
					:find("Journey's identifier", 1, true)
		end, 10),
		"Column name hover omitted its declared description"
	)
	docs.on_close()
	forwarded = false
	local literal = declaration[4]:find("'STRING outer notes'", 1, true)
	vim.api.nvim_win_set_cursor(0, { 4, literal })
	vim.cmd.normal("K")
	assert(forwarded, "A string literal was mistaken for a type")
	forwarded = false
	vim.api.nvim_win_set_cursor(0, { 4, 2 })
	vim.cmd.normal("K")
	assert(
		vim.wait(2000, function()
			local popup = docs._messages.hover:win()
			if not popup then
				return false
			end
			local text = table.concat(vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(popup), 0, -1, false), "\n")
			return text:find("`postal  code`", 1, true)
				and text:find("STRING outer notes", 1, true)
				and not text:find("Nested field documentation", 1, true)
		end, 10),
		"STRUCT hover changed a quoted name or used a nested description"
	)
	assert(forwarded, "STRUCT column hover did not reach bqls")
	docs.on_close()
	local field = declaration[6]:find("STRING", 1, true) - 1
	vim.api.nvim_win_set_cursor(0, { 6, field })
	vim.cmd.normal("K")
	assert(forwarded, "A commented STRUCT field name was mistaken for a type")
	forwarded = false
	local ddl = {
		"CREATE TABLE deliveries (",
		"  carrier STRING NOT NULL OPTIONS(description = 'Delivery carrier')",
		")",
		"PARTITION BY DATE_TRUNC(created_at, MONTH)",
		"CLUSTER BY carrier",
		"OPTIONS(description = 'Deliveries', require_partition_filter = TRUE);",
	}
	vim.api.nvim_buf_set_lines(0, 0, -1, false, ddl)
	vim.api.nvim_win_set_cursor(0, { 2, assert(ddl[2]:find("NOT NULL", 1, true)) - 1 })
	vim.cmd.normal("K")
	assert(forwarded, "Keyword hover did not reach bqls")
	assert(
		vim.wait(2000, function()
			local popup = docs._messages.hover:win()
			return popup
				and table
					.concat(vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(popup), 0, -1, false), "\n")
					:find("Makes a column required", 1, true)
		end, 10),
		"NOT NULL keyword documentation did not render"
	)
	docs.on_close()
	vim.api.nvim_win_set_cursor(0, { 6, 0 })
	vim.cmd.normal("K")
	assert(
		vim.wait(2000, function()
			local popup = docs._messages.hover:win()
			return popup
				and table
					.concat(vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(popup), 0, -1, false), "\n")
					:find("require_partition_filter", 1, true)
		end, 10),
		"Table OPTIONS did not show supported parameters"
	)
	docs.on_close()
	vim.api.nvim_win_set_cursor(0, { 2, assert(ddl[2]:find("OPTIONS", 1, true)) - 1 })
	vim.cmd.normal("K")
	assert(
		vim.wait(2000, function()
			local popup = docs._messages.hover:win()
			if not popup then
				return false
			end
			local text = table.concat(vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(popup), 0, -1, false), "\n")
			return text:find("rounding_mode", 1, true) and not text:find("require_partition_filter", 1, true)
		end, 10),
		"Column OPTIONS did not use the column parameter list"
	)
	docs.on_close()
	vim.api.nvim_win_set_cursor(0, { 6, assert(ddl[6]:find("require_partition_filter", 1, true)) - 1 })
	vim.cmd.normal("K")
	assert(
		vim.wait(2000, function()
			local popup = docs._messages.hover:win()
			return popup
				and table
					.concat(vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(popup), 0, -1, false), "\n")
					:find("Supported values: TRUE, FALSE.", 1, true)
		end, 10),
		"Individual OPTIONS parameter documentation did not render"
	)
	assert(forwarded, "OPTIONS help did not reach bqls")
	docs.on_close()
	vim.api.nvim_win_set_cursor(0, { 5, 11 })
	vim.cmd.normal("K")
	assert(
		vim.wait(2000, function()
			local popup = docs._messages.hover:win()
			return popup
				and table
					.concat(vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(popup), 0, -1, false), "\n")
					:find("Delivery carrier", 1, true)
		end, 10),
		"Clustering reference hover omitted the column's description"
	)
	assert(forwarded, "Clustering column hover did not reach bqls")
	docs.on_close()
	vim.lsp.buf.hover = hover
	vim.fn.delete(path)
end

vim.api.nvim_create_autocmd("VimEnter", {
	once = true,
	callback = function()
		vim.schedule(function()
			local ok, err = xpcall(workflow, debug.traceback)
			if not ok then
				io.stderr:write(err .. "\n")
				vim.cmd.cquit(1)
			else
				io.stdout:write("Hover workflow: schema, type, keyword and OPTIONS documentation passed\n")
				vim.cmd("qa!")
			end
		end)
	end,
})
