local M = {}
local data_dir = vim.fs.joinpath(vim.fs.dirname(debug.getinfo(1, "S").source:sub(2)), "../data")
local catalog

function M.catalog()
	if not catalog then
		catalog = vim.json.decode(table.concat(vim.fn.readfile(data_dir .. "/bigquery-options.json"), "\n"))
	end
	return catalog
end

-- Byte offsets remain stable even with unfinished quoted values and comments.
-- Tree-sitter alone cannot identify strings in every partially typed statement.
function M.tokens(text)
	local tokens, i = {}, 1
	while i <= #text do
		local first, c = i, text:sub(i, i)
		local pair = text:sub(i, i + 1)
		local literal_prefix = text:sub(i, i + 2):match("^([rRbB][rRbB]?)['\"]")
		if literal_prefix and (literal_prefix:lower() == "rr" or literal_prefix:lower() == "bb") then
			literal_prefix = nil
		end
		if c:match("%s") then
			i = i + 1
		elseif pair == "--" or c == "#" then
			i = (text:find("\n", i, true) or (#text + 1))
			tokens[#tokens + 1] = { kind = "comment", first = first - 1, last = i - 1, closed = false }
		elseif pair == "/*" then
			local ending = text:find("*/", i + 2, true)
			i = (ending or (#text - 1)) + 2
			tokens[#tokens + 1] = { kind = "comment", first = first - 1, last = i - 1, closed = ending ~= nil }
		elseif c == "'" or c == '"' or c == "`" or literal_prefix then
			i = i + #(literal_prefix or "")
			c = text:sub(i, i)
			local quote = c
			if c ~= "`" and text:sub(i, i + 2) == c:rep(3) then
				quote = c:rep(3)
			end
			i = i + #quote
			local closed = false
			while i <= #text do
				if text:sub(i, i) == "\\" then
					i = i + 2
				elseif text:sub(i, i + #quote - 1) == quote then
					i = i + #quote
					closed = true
					break
				else
					i = i + 1
				end
			end
			tokens[#tokens + 1] = {
				kind = c == "`" and "quoted"
					or (literal_prefix and literal_prefix:lower():find("b") and "bytes" or "literal"),
				value = text:sub(first + #(literal_prefix or "") + #quote, i - #quote - 1),
				first = first - 1,
				last = math.min(i - 1, #text),
				closed = closed,
				raw = literal_prefix and literal_prefix:lower():find("r") ~= nil or false,
			}
		elseif c:match("[%w_]") then
			i = i + 1
			while text:sub(i, i):match("[%w_]") do
				i = i + 1
			end
			tokens[#tokens + 1] = {
				kind = "word",
				value = text:sub(first, i - 1):upper(),
				first = first - 1,
				last = i - 1,
			}
		else
			i = i + 1
			tokens[#tokens + 1] = { kind = c, value = c, first = first - 1, last = i - 1 }
		end
	end
	return tokens
end

local function scope(text, clause, tokens)
	-- Repair only the current clause and close enclosing delimiters. This also
	-- recovers ALTER statements whose unfinished OPTIONS currently parse as ERROR.
	local prefix = text:sub(clause.statement + 1, clause.keyword.first)
	local repaired = prefix .. clause.keyword.value .. "(description = 'x')"
	for i = #clause.parents, 1, -1 do
		repaired = repaired .. (clause.parents[i] == "(" and ")" or "]")
	end
	local ok, parser = pcall(vim.treesitter.get_string_parser, repaired .. ";", "sql_bigquery")
	if not ok then
		return
	end
	local parsed, trees = pcall(parser.parse, parser)
	if not parsed then
		return
	end
	local offset = #prefix
	local before = repaired:sub(1, offset)
	local _, row = before:gsub("\n", "")
	local col = #before - (before:match(".*()\n") or 0)
	local node = trees[1]:root():named_descendant_for_range(row, col, row, col + 7)
	local parents, owner_start = {}, clause.statement
	while node do
		parents[node:type()] = true
		if node:type():match("_statement$") then
			local sr, sc = node:start()
			local repaired_lines = vim.split(repaired, "\n", { plain = true })
			local start = sc
			for i = 1, sr do
				start = start + #repaired_lines[i] + 1
			end
			owner_start = clause.statement + start
			break
		end
		node = node:parent()
	end
	local words, head = {}, {}
	for _, token in ipairs(tokens) do
		if token.first >= owner_start and token.first < clause.keyword.first then
			head[#head + 1] = token
			if token.kind == "word" then
				words[#words + 1] = token.value
			end
		end
	end
	local statement = " " .. table.concat(words, " ") .. " "
	local index = 2
	if head[index] and head[index].value == "OR" then
		index = index + 2
	end
	if head[index] and (head[index].value == "TEMP" or head[index].value == "TEMPORARY") then
		index = index + 1
	end
	local object = head[index] and head[index].value
	local materialized = object == "MATERIALIZED" and head[index + 1] and head[index + 1].value == "VIEW"
	local view = object == "VIEW" or materialized
	local table_function = object == "TABLE" and head[index + 1] and head[index + 1].value == "FUNCTION"
	local spark = words[1] == "CREATE" and object == "PROCEDURE" and statement:find(" WITH CONNECTION ", 1, true)
	if not parents.option_clause and not parents.from_files_clause then
		-- The pinned grammar lacks Spark's WITH CONNECTION procedure branch.
		-- Recognize its declaration header without accepting OPTIONS calls in SQL bodies.
		if spark and not statement:find(" BEGIN ", 1, true) and not statement:find(" AS ", 1, true) then
			return "create_spark_procedure"
		end
		return
	end
	if clause.keyword.value == "FILES" and statement:match("^ LOAD DATA ") then
		return "load_data_files"
	elseif parents.column_definition then
		return view and "create_view_column" or (parents.load_data_statement and "load_data_column" or "create_column")
	elseif parents.set_option and statement:find(" ALTER COLUMN ", 1, true) then
		return view and "alter_view_column" or "alter_column"
	elseif parents.create_table_statement or parents.create_table_like_statement then
		if materialized then
			return "create_materialized_view"
		elseif view then
			return "create_view"
		end
		return parents.create_table_like_statement and "create_table_like" or "create_table"
	elseif parents.alter_table_statement then
		return materialized and "alter_materialized_view" or (view and "alter_view" or "alter_table")
	elseif parents.create_function_statement and not table_function then
		return statement:find(" LANGUAGE JS ", 1, true) and "create_javascript_function"
			or (statement:find(" LANGUAGE PYTHON ", 1, true) and "create_python_function" or "create_sql_function")
	elseif parents.create_procedure_statement then
		return spark and "create_spark_procedure" or "create_sql_procedure"
	elseif parents.export_data_statement or statement:match("^ EXPORT DATA ") then
		local format
		for i, token in ipairs(tokens) do
			if
				token.first > clause.open.first
				and token.first < clause.last
				and token.value == "FORMAT"
				and tokens[i + 1]
				and tokens[i + 1].kind == "="
				and tokens[i + 2]
			then
				format = tokens[i + 2].value:upper()
			end
		end
		local backends =
			{ BIGTABLE = "bigtable", CLOUD_PUBSUB = "pubsub", CLOUD_SPANNER = "spanner", CLOUD_ALLOYDB = "alloydb" }
		return "export_" .. (backends[format] or "files")
	elseif parents.create_model_statement then
		return "create_model"
	end
	for parent, context in pairs(M.catalog().grammar_parent_types) do
		if parents[parent] and type(context) == "string" then
			return context
		end
	end
	-- Some grammar branches require a body after OPTIONS before creating a
	-- statement node. Recover the kind from lexed words, never quoted SQL text.
	if words[1] == "CREATE" and object == "MODEL" then
		return "create_model"
	elseif words[1] == "CREATE" and object == "PROCEDURE" then
		return spark and "create_spark_procedure" or "create_sql_procedure"
	elseif words[1] == "CREATE" and table_function then
		return "create_table_function"
	elseif words[1] == "CREATE" and object == "FUNCTION" then
		if statement:find(" REMOTE WITH CONNECTION ", 1, true) then
			return "create_remote_function"
		end
		return statement:find(" LANGUAGE JS ", 1, true) and "create_javascript_function"
			or (statement:find(" LANGUAGE PYTHON ", 1, true) and "create_python_function" or "create_sql_function")
	elseif statement:match("^ LOAD DATA ") then
		return clause.keyword.value == "FILES" and "load_data_files" or "load_data_table"
	end
end

function M.context(buf, cursor)
	buf = buf or vim.api.nvim_get_current_buf()
	if vim.bo[buf].filetype ~= "sql.bigquery" then
		return
	end
	cursor = cursor or vim.api.nvim_win_get_cursor(0)
	local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
	local text = table.concat(lines, "\n")
	local position = cursor[2]
	for i = 1, cursor[1] - 1 do
		position = position + #lines[i] + 1
	end
	local tokens = M.tokens(text)
	local stack, clauses, previous, statement = {}, {}, nil, 0
	local selected, blocked
	for _, token in ipairs(tokens) do
		if
			token.first <= position and (position < token.last or (position == token.last and token.closed == false))
		then
			selected = token
			blocked = token.kind == "literal"
				or token.kind == "bytes"
				or token.kind == "quoted"
				or token.kind == "comment"
		end
		if token.kind ~= "comment" then
			if token.kind == "(" or token.kind == "[" then
				local clause
				if
					token.kind == "("
					and previous
					and previous.kind == "word"
					and (previous.value == "OPTIONS" or previous.value == "FILES")
				then
					clause = {
						keyword = previous,
						open = token,
						last = #text + 1,
						statement = statement,
						parents = vim.tbl_map(function(entry)
							return entry.kind
						end, stack),
					}
					clauses[#clauses + 1] = clause
				end
				stack[#stack + 1] = { kind = token.kind, clause = clause }
			elseif token.kind == ")" or token.kind == "]" then
				local entry = table.remove(stack)
				if entry and entry.clause then
					entry.clause.last = token.first
				end
			elseif token.kind == ";" then
				for _, entry in ipairs(stack) do
					if entry.clause then
						entry.clause.last = token.first
					end
				end
				stack, statement = {}, token.last
			end
			previous = token
		end
	end
	local clause
	for _, candidate in ipairs(clauses) do
		if position >= candidate.keyword.first and position <= candidate.last then
			clause = candidate
		end
	end
	if not clause or blocked then
		return
	end
	tokens = vim.tbl_filter(function(token)
		return token.kind ~= "comment"
	end, tokens)
	local context = scope(text, clause, tokens)
	local info = context and M.catalog().contexts[context]
	if not info then
		return
	end
	if context == "create_model" then
		local model_type
		for i, token in ipairs(tokens) do
			if
				token.first > clause.open.first
				and token.first < clause.last
				and token.value == "MODEL_TYPE"
				and tokens[i + 1]
				and tokens[i + 1].kind == "="
				and tokens[i + 2]
				and tokens[i + 2].kind == "literal"
				and tokens[i + 2].closed
			then
				model_type = tokens[i + 2].value:upper()
			end
		end
		for _, family in pairs(M.catalog().model_families or {}) do
			if vim.tbl_contains(family.model_types, model_type) then
				info = vim.deepcopy(family)
				info.options = vim.tbl_filter(function(option)
					return not option.applies_to_model_types
						or vim.tbl_contains(option.applies_to_model_types, model_type)
				end, info.options)
				break
			end
		end
	end
	local depth, segment, used, assignments = 0, {}, {}, {}
	local current
	for _, token in ipairs(tokens) do
		if token.first > clause.open.first and token.first < clause.last and token.kind ~= "comment" then
			if depth == 0 and token.kind == "," then
				segment = {}
			elseif depth == 0 then
				segment[#segment + 1] = token
				if token.kind == "=" and segment[1] and segment[1].kind == "word" then
					used[segment[1].value:lower()] = true
					assignments[segment[1].first] = true
				end
			end
			if token.first <= position then
				current = { segment = vim.deepcopy(segment), depth = depth }
			end
			if token.kind == "(" or token.kind == "[" then
				depth = depth + 1
			elseif token.kind == ")" or token.kind == "]" then
				depth = depth - 1
			end
		end
	end
	current = current or { segment = {}, depth = 0 }
	return {
		info = info,
		name = context,
		selected = selected,
		keyword = clause.keyword,
		segment = current.segment,
		has_equals = current.segment[1] and assignments[current.segment[1].first] or false,
		depth = current.depth,
		used = used,
		position = position,
	}
end

function M.option_contents(option)
	local lines = {
		"```sql",
		option.name .. " = " .. option.type,
		"```",
		"",
		option.summary,
	}
	if option.values then
		lines[#lines + 1] = ""
		lines[#lines + 1] = "Supported values: " .. table.concat(option.values, ", ") .. "."
	end
	lines[#lines + 1] = ""
	lines[#lines + 1] = "[GoogleSQL option reference](" .. option.url .. ")"
	return { kind = "markdown", value = table.concat(lines, "\n") }
end

function M.contents()
	local context = M.context()
	if not context then
		return
	end
	local token = context.selected
	if token and token == context.keyword then
		local lines = { "```sql", "OPTIONS(name = value, ...)", "```", "", context.info.title, "" }
		for _, option in ipairs(context.info.options) do
			lines[#lines + 1] = "- `" .. option.name .. "` · `" .. option.type .. "` — " .. option.summary
		end
		lines[#lines + 1] = ""
		lines[#lines + 1] = "[GoogleSQL option reference](" .. context.info.url .. ")"
		return { kind = "markdown", value = table.concat(lines, "\n") }
	elseif token and context.segment[1] and token.first == context.segment[1].first and token.kind == "word" then
		for _, option in ipairs(context.info.options) do
			if option.name:upper() == token.value then
				return M.option_contents(option)
			end
		end
	end
end

return M
