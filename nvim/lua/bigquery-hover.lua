local M = {}
local type_nodes = { column_type = true, type = true, type_identifier = true, array = true, struct = true }

local function type_contents()
	if vim.bo.filetype ~= "sql.bigquery" then
		return
	end
	local ok, parser = pcall(vim.treesitter.get_parser, 0, "sql_bigquery")
	if not ok or not pcall(parser.parse, parser) then
		return
	end
	local node = vim.treesitter.get_node({ ignore_injections = true })
	if not node or not type_nodes[node:type()] then
		return
	end
	local row, col = unpack(vim.api.nvim_win_get_cursor(0))
	row = row - 1
	local line = vim.api.nvim_buf_get_lines(0, row, row + 1, false)[1]
	if not line:sub(col + 1, col + 1):match("[%w_]") then
		return
	end
	local first, last = col, col + 1
	while first > 0 and line:sub(first, first):match("[%w_]") do
		first = first - 1
	end
	while line:sub(last + 1, last + 1):match("[%w_]") do
		last = last + 1
	end
	local word = line:sub(first + 1, last):upper()
	local info = require("bigquery-types").info(word)
	if not info then
		return
	end
	local sr, sc = node:range()
	local prefix = table.concat(vim.api.nvim_buf_get_text(0, sr, sc, row, first, {}), "\n")
	local text = vim.treesitter.get_node_text(node, 0)
	local comments = vim.treesitter.query.parse("sql_bigquery", "(comment) @comment")
	for _, comment in comments:iter_captures(node, 0) do
		local cr, cc = comment:range()
		local offset = #table.concat(vim.api.nvim_buf_get_text(0, sr, sc, cr, cc, {}), "\n")
		local content = vim.treesitter.get_node_text(comment, 0)
		text = text:sub(1, offset) .. content:gsub("[^\r\n]", " ") .. text:sub(offset + #content + 1)
	end
	local before = #prefix
	prefix = text:sub(1, before)
	local suffix = text:sub(before + last - first + 1)
	local _, backticks = prefix:gsub("\\.", ""):gsub("`", "")
	if backticks % 2 == 1 then
		return
	end
	-- CAST/constructor type nodes hide STRUCT field names; the first of two
	-- consecutive words following '<' or ',' is a field name, not its type.
	if prefix:match("[<,]%s*$") and suffix:match("^%s+[%a_`]") then
		return
	end
	local parameters = suffix:match("^%s*(%b())")
	local title = word .. (parameters and parameters:gsub("%s+", "") or "")
	return require("bigquery-types").contents(title)
end

function M.contents()
	local column = require("bigquery-ddl").column_at_cursor()
	local contents = column and require("bigquery-ddl").column_contents(column)
	contents = contents or require("bigquery-options").contents() or type_contents()
	if contents then
		return contents
	end
	if vim.bo.filetype ~= "sql.bigquery" then
		return
	end
	local ok, parser = pcall(vim.treesitter.get_parser, 0, "sql_bigquery")
	if not ok or not pcall(parser.parse, parser) then
		return
	end
	local node = vim.treesitter.get_node({ ignore_injections = true, include_anonymous = true })
	if not node then
		return
	end
	local data_dir = vim.fs.joinpath(vim.fs.dirname(debug.getinfo(1, "S").source:sub(2)), "../data")
	M.keywords = M.keywords
		or vim.json.decode(table.concat(vim.fn.readfile(data_dir .. "/bigquery-keywords.json"), "\n"))
	local info = M.keywords[node:type()]
	if not info then
		return
	end
	return {
		kind = "markdown",
		value = table.concat({
			"```sql",
			info.keyword,
			"```",
			"",
			info.summary,
			"",
			"```sql",
			info.syntax,
			"```",
			"",
			"[GoogleSQL reference](" .. info.url .. ")",
		}, "\n"),
	}
end

function M.hover()
	local contents = M.contents()
	if contents then
		require("noice.lsp.hover").on_hover(nil, { contents = contents }, { bufnr = vim.api.nvim_get_current_buf() })
	else
		vim.lsp.buf.hover()
	end
end

return M
