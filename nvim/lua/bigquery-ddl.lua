local M = {}

local cluster_types = {
	BIGNUMERIC = true,
	BOOL = true,
	DATE = true,
	DATETIME = true,
	GEOGRAPHY = true,
	INT64 = true,
	NUMERIC = true,
	RANGE = true,
	STRING = true,
	TIMESTAMP = true,
}
local aliases = {
	BOOLEAN = "BOOL",
	INT = "INT64",
	INTEGER = "INT64",
	SMALLINT = "INT64",
	BIGINT = "INT64",
	TINYINT = "INT64",
	BYTEINT = "INT64",
	DECIMAL = "NUMERIC",
	BIGDECIMAL = "BIGNUMERIC",
}

local escapes = {
	a = "\a",
	b = "\b",
	f = "\f",
	n = "\n",
	r = "\r",
	t = "\t",
	v = "\v",
	["\\"] = "\\",
	["?"] = "?",
	["'"] = "'",
	['"'] = '"',
	["`"] = "`",
}

local function decode(token)
	if token.raw then
		return token.value
	end
	local result, i = {}, 1
	while i <= #token.value do
		local c = token.value:sub(i, i)
		local code = token.value:sub(i + 1, i + 1)
		if c ~= "\\" then
			result[#result + 1], i = c, i + 1
		elseif escapes[code] then
			result[#result + 1], i = escapes[code], i + 2
		else
			local length = ({ x = 2, X = 2, u = 4, U = 8 })[code]
			local digits = length and token.value:sub(i + 2, i + 1 + length)
			local number = digits and #digits == length and digits:match("^%x+$") and tonumber(digits, 16)
			if not length and code:match("[0-7]") then
				digits = token.value:sub(i + 1, i + 3)
				if #digits == 3 and digits:match("^[0-7]+$") then
					number, length = tonumber(digits, 8), 2
				end
			end
			if
				number
				and number > 0
				and number <= 0x10FFFF
				and not (number >= 0xD800 and number <= 0xDFFF)
				and not (code:match("[0-7]") and number > 255)
			then
				result[#result + 1] = vim.fn.nr2char(number)
				i = i + length + 2
			else
				result[#result + 1], i = c, i + 1
			end
		end
	end
	return table.concat(result)
end

local function collation(node, source)
	if node then
		for _, token in ipairs(require("bigquery-options").tokens(vim.treesitter.get_node_text(node, source))) do
			if token.kind == "literal" then
				return token.value
			end
		end
	end
end

local function description(column, source)
	-- Only this declaration's OPTIONS; nested STRUCT descriptions belong to
	-- their own fields and must never replace the outer column's description.
	for child in column:iter_children() do
		local clause
		if child:type() == "option_clause" then
			clause = child
		elseif child:type() == "option" then
			for entry in child:iter_children() do
				if entry:type() == "option_clause" then
					clause = entry
				end
			end
		end
		if clause then
			-- The pinned parser truncates some escaped/chunked literals. Recover
			-- the full literal value within this clause rather than its value node.
			local tokens = vim.tbl_filter(function(token)
				return token.kind ~= "comment"
			end, require("bigquery-options").tokens(vim.treesitter.get_node_text(clause, source)))
			local depth = 0
			for i, token in ipairs(tokens) do
				if
					depth == 1
					and token.kind == "word"
					and token.value == "DESCRIPTION"
					and tokens[i - 1]
					and (tokens[i - 1].kind == "(" or tokens[i - 1].kind == ",")
					and tokens[i + 1]
					and tokens[i + 1].kind == "="
				then
					local parts, j = {}, i + 2
					while tokens[j] and tokens[j].kind == "literal" and tokens[j].closed do
						parts[#parts + 1] = decode(tokens[j])
						j = j + 1
					end
					if #parts > 0 and tokens[j] and (tokens[j].kind == "," or tokens[j].kind == ")") then
						return table.concat(parts)
					end
					return
				end
				if token.kind == "(" or token.kind == "[" then
					depth = depth + 1
				elseif token.kind == ")" or token.kind == "]" then
					depth = depth - 1
				end
			end
		end
	end
end

local function declared_type(node, source)
	if not node then
		return ""
	end
	local text = vim.treesitter.get_node_text(node, source)
	local sr, sc = node:start()
	local removals = {}
	local function visit(child)
		if child:type() == "option_clause" or child:type() == "comment" then
			local cr, cc = child:start()
			local first
			if type(source) == "number" then
				first = #table.concat(vim.api.nvim_buf_get_text(source, sr, sc, cr, cc, {}), "\n")
			else
				local rows = vim.split(text, "\n", { plain = true })
				first = cr == sr and cc - sc or cc
				for i = 1, cr - sr do
					first = first + #rows[i] + 1
				end
			end
			removals[#removals + 1] = { first, #vim.treesitter.get_node_text(child, source) }
		else
			for entry in child:iter_children() do
				visit(entry)
			end
		end
	end
	visit(node)
	table.sort(removals, function(a, b)
		return a[1] > b[1]
	end)
	for _, removal in ipairs(removals) do
		text = text:sub(1, removal[1]) .. " " .. text:sub(removal[1] + removal[2] + 1)
	end
	local pieces, last, previous = {}, 0, nil
	for _, token in ipairs(require("bigquery-options").tokens(text)) do
		local gap = text:sub(last + 1, token.first)
		if
			gap ~= ""
			and #pieces > 0
			and token.kind ~= ">"
			and token.kind ~= ","
			and (not previous or previous.kind ~= "<")
		then
			pieces[#pieces + 1] = " "
		end
		pieces[#pieces + 1] = text:sub(token.first + 1, token.last)
		last, previous = token.last, token
	end
	return table.concat(pieces)
end

local function column_info(column, source, default_collation)
	local declaration = column:field("column_name")[1]
	if not declaration then
		return
	end
	local typ = declared_type(column:field("column_type")[1], source)
	local base = typ:match("^%s*([%w_]+)")
	base = base and base:upper()
	local column_collation = collation(column:field("collate_clause")[1], source)
	if column_collation == nil then
		column_collation = default_collation
	end
	local required = false
	for child in column:iter_children() do
		required = required or child:type() == "NOT_NULL"
	end
	return {
		name = vim.treesitter.get_node_text(declaration, source):gsub("^`(.*)`$", "%1"),
		quoted = vim.treesitter.get_node_text(declaration, source):sub(1, 1) == "`",
		node = declaration,
		type = typ,
		description = description(column, source),
		required = required,
		clusterable = cluster_types[aliases[base] or base] == true
			and not (base == "STRING" and column_collation and column_collation ~= ""),
	}
end

function M.columns(statement, source)
	local columns = {}
	local default_collation
	for child in statement:iter_children() do
		if child:type() == "default_collate_clause" then
			default_collation = collation(child, source)
		end
	end
	for parameters in statement:iter_children() do
		if parameters:type() == "create_table_parameters" then
			for column in parameters:iter_children() do
				local declaration = column:type() == "column_definition" and column:field("column_name")[1]
				if declaration then
					columns[#columns + 1] = column_info(column, source, default_collation)
				end
			end
		end
	end
	return columns
end

function M.column_contents(column)
	local name = column.quoted and ("`" .. column.name .. "`") or column.name
	local lines = { "```sql", name .. " " .. column.type .. (column.required and " NOT NULL" or ""), "```" }
	if column.description and column.description ~= "" then
		lines[#lines + 1], lines[#lines + 2] = "", column.description
	end
	local explanation = require("bigquery-types").explanation(column.type)
	if explanation then
		lines[#lines + 1], lines[#lines + 2] = "", explanation
	end
	return { kind = "markdown", value = table.concat(lines, "\n") }
end

function M.column_at_cursor()
	if vim.bo.filetype ~= "sql.bigquery" then
		return
	end
	local ok, parser = pcall(vim.treesitter.get_parser, 0, "sql_bigquery")
	if not ok or not pcall(parser.parse, parser) then
		return
	end
	local origin = vim.treesitter.get_node({ ignore_injections = true, include_anonymous = true })
	if not origin or origin:type() == "comment" or origin:type() == "string" then
		return
	end
	local cursor = vim.api.nvim_win_get_cursor(0)
	local node, column, clause = origin
	while node do
		if not column and node:type() == "column_definition" then
			column = node
		end
		if node:type() == "table_cluster_clause" or node:type() == "table_partition_clause" then
			clause = node
		end
		if node:type():match("_statement$") then
			break
		end
		node = node:parent()
	end
	if column then
		local name_node, type_node = column:field("column_name")[1], column:field("column_type")[1]
		if
			origin == name_node or (type_node and vim.treesitter.is_in_node_range(type_node, cursor[1] - 1, cursor[2]))
		then
			local info = column_info(column, 0)
			if info and info.type ~= "" then
				return info
			end
		end
	elseif clause and node and origin:type() == "identifier" then
		local parent = origin:parent()
		if parent and parent:type() == "function_call" and parent:field("function")[1] == origin then
			return
		end
		local target = vim.treesitter.get_node_text(origin, 0):gsub("^`(.*)`$", "%1"):lower()
		for _, info in ipairs(M.columns(node, 0)) do
			if info.name:lower() == target then
				return info
			end
		end
	end
end

local function position(text, offset)
	local prefix = text:sub(1, offset)
	local _, row = prefix:gsub("\n", "")
	return { line = row, character = #prefix - (prefix:match(".*()\n") or 0) }
end

function M.cluster_context(buf, cursor)
	if vim.bo[buf].filetype ~= "sql.bigquery" then
		return
	end
	local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
	local text = table.concat(lines, "\n")
	local offset = cursor[2]
	for i = 1, cursor[1] - 1 do
		offset = offset + #lines[i] + 1
	end
	local tokens = require("bigquery-options").tokens(text)
	local significant, selected, blocked = {}, nil, false
	for _, token in ipairs(tokens) do
		if token.first <= offset and (offset < token.last or (offset == token.last and token.closed == false)) then
			selected = token
			blocked = token.kind == "literal" or token.kind == "bytes" or token.kind == "comment"
		end
		if token.kind ~= "comment" then
			significant[#significant + 1] = token
		end
	end
	if blocked then
		return
	end
	local statement_start, clause
	for i, token in ipairs(significant) do
		if token.first >= offset then
			break
		end
		if token.kind == ";" then
			statement_start, clause = token.last, nil
		elseif
			token.kind == "word"
			and token.value == "CLUSTER"
			and significant[i + 1]
			and significant[i + 1].value == "BY"
			and significant[i + 1].last <= offset
		then
			clause = { first = token.first, last = significant[i + 1].last, index = i + 2 }
		end
	end
	if not clause then
		return
	end
	local finish, finish_kind, used, segment = #text + 1, nil, {}, {}
	for i = clause.index, #significant do
		local token = significant[i]
		local option_clause = token.kind == "word"
			and token.value == "OPTIONS"
			and significant[i + 1]
			and significant[i + 1].kind == "("
		if token.kind == ";" or option_clause or (token.kind == "word" and token.value == "AS") then
			finish = token.first
			finish_kind = token.kind
			break
		end
		if token.kind == "word" or token.kind == "quoted" then
			local key = token.value:lower()
			used[key] = (used[key] or 0) + 1
		end
		if token.first < offset then
			if token.kind == "," then
				segment = {}
			else
				segment[#segment + 1] = token
			end
		end
	end
	if
		(offset > finish or (offset == finish and finish_kind ~= ";"))
		or #segment > 1
		or (segment[1] and segment[1].kind ~= "word" and segment[1].kind ~= "quoted")
	then
		return
	end
	-- A placeholder gives even an empty/partially typed CLUSTER BY a clause node.
	local prefix = text:sub((statement_start or 0) + 1, clause.last)
	local repaired = prefix .. " __bigquery_column__;"
	local ok, parser = pcall(vim.treesitter.get_string_parser, repaired, "sql_bigquery")
	if not ok then
		return
	end
	local parsed, trees = pcall(parser.parse, parser)
	if not parsed then
		return
	end
	local pos = position(repaired, #prefix + 1)
	local node = trees[1]:root():named_descendant_for_range(pos.line, pos.character, pos.line, pos.character + 1)
	local cluster
	while node do
		if node:type() == "table_cluster_clause" then
			cluster = node
		end
		if node:type():match("_statement$") then
			break
		end
		node = node:parent()
	end
	if not cluster or not node or node:type() ~= "create_table_statement" then
		return
	end
	-- The grammar shares this node with views; their output types/provenance
	-- need separate analysis before they can supply clustering candidates.
	local table_statement = false
	for child in node:iter_children() do
		if child:type() == "TABLE" then
			table_statement = true
		end
	end
	if not table_statement then
		return
	end
	local editing = selected and (selected.kind == "word" or selected.kind == "quoted") and selected
	if not editing and segment[1] then
		if segment[1].last ~= offset then
			return
		end
		editing = segment[1]
	end
	if editing then
		local key = editing.value:lower()
		used[key] = (used[key] or 1) - 1
		if used[key] == 0 then
			used[key] = nil
		end
	end
	local slots = 0
	for _, count in pairs(used) do
		slots = slots + count
	end
	if slots >= 4 then
		return
	end
	return {
		columns = M.columns(node, repaired),
		used = used,
		range = {
			start = position(text, editing and editing.first or offset),
			["end"] = position(text, editing and editing.last or offset),
		},
		quoted = editing and editing.kind == "quoted",
		separator = offset == clause.last and " " or "",
	}
end

return M
