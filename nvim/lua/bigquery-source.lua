local Source = {}
Source.__index = Source

function Source.new()
	return setmetatable({}, Source)
end

function Source:enabled()
	return vim.bo.filetype == "sql.bigquery"
end

function Source:get_trigger_characters()
	return { "(", ",", " " }
end

function Source:get_completions(ctx, callback)
	local options = require("bigquery-options")
	local context = options.context(ctx.bufnr, ctx.cursor)
	local items = {}
	if context and context.position > context.keyword.last and context.depth == 0 then
		local segment = context.segment
		local key = segment[1]
		local at_key = #segment == 0 or (#segment == 1 and key.kind == "word")
		-- A key may already have "= value" after the cursor. Preserve that suffix.
		local line = vim.api.nvim_buf_get_lines(ctx.bufnr, ctx.cursor[1] - 1, ctx.cursor[1], false)[1]
		local first, last = ctx.cursor[2], ctx.cursor[2]
		while first > 0 and line:sub(first, first):match("[%w_]") do
			first = first - 1
		end
		while line:sub(last + 1, last + 1):match("[%w_]") do
			last = last + 1
		end
		local has_equals = context.has_equals
		if at_key then
			for _, option in ipairs(context.info.options) do
				if not context.used[option.name] or (key and option.name:upper() == key.value) then
					items[#items + 1] = {
						label = option.name,
						detail = option.type,
						kind = vim.lsp.protocol.CompletionItemKind.Property,
						documentation = options.option_contents(option),
						labelDetails = { description = option.summary },
						textEdit = {
							newText = option.name .. (has_equals and "" or " = "),
							range = {
								start = { line = ctx.cursor[1] - 1, character = first },
								["end"] = { line = ctx.cursor[1] - 1, character = last },
							},
						},
					}
				end
			end
		end
	end
	local cluster = not context and require("bigquery-ddl").cluster_context(ctx.bufnr, ctx.cursor)
	if cluster then
		for _, column in ipairs(cluster.columns) do
			if column.clusterable and not cluster.used[column.name:lower()] then
				local quoted = cluster.quoted or column.quoted or not column.name:match("^[%a_][%w_]*$")
				items[#items + 1] = {
					label = column.name,
					detail = column.type,
					kind = vim.lsp.protocol.CompletionItemKind.Field,
					textEdit = {
						newText = cluster.separator
							.. (quoted and ("`" .. column.name:gsub("`", "\\`") .. "`") or column.name),
						range = cluster.range,
					},
					labelDetails = { description = column.description or "" },
					documentation = require("bigquery-ddl").column_contents(column),
				}
			end
		end
	end
	callback({ items = items, is_incomplete_forward = true, is_incomplete_backward = true })
end

return Source
