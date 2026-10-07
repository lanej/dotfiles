local M = {}

-- Parse cells rather than splitting on pipes: escaped pipes and fenced examples
-- must keep their Markdown meaning.
function M.align(lines, display_width)
	display_width = display_width or vim.fn.strdisplaywidth
	local source = table.concat(lines, "\n")
	local ok, parser = pcall(vim.treesitter.get_string_parser, source, "markdown")
	if not ok then
		return lines
	end
	local trees = parser:parse()
	local query = vim.treesitter.query.parse("markdown", "(pipe_table) @table")
	local result = vim.deepcopy(lines)
	local has_table = false
	for _, node in query:iter_captures(trees[1]:root(), source) do
		local first, col = node:range()
		-- Leave table prefixes in block quotes and lists alone.
		if col == 0 then
			has_table = true
			local rows, widths = {}, {}
			for row in node:iter_children() do
				local cells = {}
				for cell in row:iter_children() do
					if cell:type():match("^pipe_table_.*cell$") then
						local text = vim.trim(vim.treesitter.get_node_text(cell, source))
						cells[#cells + 1] = text
						local c = #cells
						widths[c] = math.max(widths[c] or 3, display_width(text))
					end
				end
				rows[#rows + 1] = cells
			end
			for r, cells in ipairs(rows) do
				local padded = {}
				for c, width in ipairs(widths) do
					local text = cells[c] or ""
					if r == 2 then
						local left = text:sub(1, 1) == ":" and ":" or ""
						local right = text:sub(-1) == ":" and ":" or ""
						padded[c] = left .. string.rep("-", width - #left - #right) .. right
					else
						padded[c] = text .. string.rep(" ", width - display_width(text))
					end
				end
				result[first + r] = "| " .. table.concat(padded, " | ") .. " |"
			end
		end
	end
	return result, has_table
end

function M.setup_hover()
	local hover = require("noice.lsp.hover")
	if M.original_hover then
		return
	end
	M.original_hover = hover.on_hover
	hover.on_hover = function(err, result, ctx, ...)
		local has_table = false
		if result and result.contents then
			local lines = require("noice.lsp.format").format_markdown(result.contents)
			local ok, aligned, found = pcall(M.align, lines, function(cell)
				-- Noice decodes entities before displaying text; measure that text.
				return vim.fn.strdisplaywidth(require("noice.text.markdown").html_entities(cell))
			end)
			has_table = ok and found or false
			if ok and not vim.deep_equal(lines, aligned) then
				result = vim.deepcopy(result)
				result.contents = { kind = "markdown", value = table.concat(aligned, "\n") }
			end
		end
		M.original_hover(err, result, ctx, ...)
		local message = require("noice.lsp.docs")._messages.hover
		if result and result.contents and message then
			message.opts.markdown_table = has_table
		end
	end
end

return M
