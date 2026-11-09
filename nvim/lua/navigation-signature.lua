local M = {}

local function source(file)
	local buf = vim.fn.bufnr(file)
	if
		buf ~= -1
		and vim.api.nvim_buf_is_loaded(buf)
		and vim.fs.normalize(vim.api.nvim_buf_get_name(buf)) == vim.fs.normalize(file)
	then
		local stamp = "buffer:" .. buf .. ":" .. vim.api.nvim_buf_get_changedtick(buf)
		return stamp,
			function()
				if vim.api.nvim_buf_get_offset(buf, vim.api.nvim_buf_line_count(buf)) <= 1024 * 1024 then
					return table.concat(vim.api.nvim_buf_get_lines(buf, 0, -1, false), "\n")
				end
			end
	end
	local stat = vim.uv.fs_stat(file)
	if not stat or stat.type ~= "file" then
		return nil
	end
	local stamp = table.concat({ stat.size, stat.mtime.sec, stat.mtime.nsec }, ":")
	return stamp,
		function()
			if stat.size > 1024 * 1024 then
				return nil
			end
			local fd = vim.uv.fs_open(file, "r", 0)
			if not fd then
				return nil
			end
			local text = vim.uv.fs_read(fd, stat.size, 0)
			vim.uv.fs_close(fd)
			return text
		end
end

local functions = {
	function_item = true,
	function_signature_item = true,
	function_declaration = true,
	function_definition = true,
	method_declaration = true,
	method_definition = true,
}

function M.new()
	local cache, deadline = {}, 0
	return {
		begin = function()
			deadline = vim.uv.hrtime() + 250000000
		end,
		detail = function(symbol, file, encoding)
			if symbol.kind ~= 6 and symbol.kind ~= 9 and symbol.kind ~= 12 and symbol.kind ~= 13 then
				return nil
			end
			local position = symbol.location and symbol.location.range and symbol.location.range.start
			if not position then
				return nil
			end
			local stamp, read = source(file)
			if not stamp then
				return nil
			end
			local entry = cache[file]
			if not entry or entry.stamp ~= stamp then
				if vim.uv.hrtime() >= deadline then
					return nil
				end
				entry = { stamp = stamp }
				cache[file] = entry
				local text = read()
				local ft = vim.filetype.match({ filename = file })
				local lang = ft and vim.treesitter.language.get_lang(ft)
				if not text or not lang then
					return nil
				end
				local ok, parser = pcall(vim.treesitter.get_string_parser, text, lang)
				if not ok then
					return nil
				end
				local parsed, trees = pcall(parser.parse, parser)
				if not parsed or not trees[1] then
					return nil
				end
				entry.text, entry.lines, entry.root = text, vim.split(text, "\n", { plain = true }), trees[1]:root()
			end
			if not entry.root or not entry.lines[position.line + 1] then
				return nil
			end
			-- WHY: LSP character offsets may be UTF-16; Tree-sitter ranges always use byte columns.
			local column =
				vim.str_byteindex(entry.lines[position.line + 1], encoding or "utf-16", position.character, false)
			local node = entry.root:named_descendant_for_range(position.line, column, position.line, column)
			while node do
				if functions[node:type()] then
					local name, body = node:field("name")[1], node:field("body")[1]
					if
						name
						and vim.treesitter.get_node_text(name, entry.text) == symbol.name
						and not node:has_error()
					then
						local _, _, row, col = name:range()
						local end_row, end_col
						if body then
							end_row, end_col = body:start()
						else
							for child in node:iter_children() do
								if child:type() == "end" or child:type() == ";" then
									end_row, end_col = child:start()
									break
								end
							end
						end
						if not end_row then
							return nil
						end
						local lines = vim.list_slice(entry.lines, row + 1, end_row + 1)
						lines[#lines] = lines[#lines]:sub(1, end_col)
						lines[1] = lines[1]:sub(col + 1)
						return table.concat(lines, " "):gsub(";%s*$", "")
					end
					return nil
				end
				node = node:parent()
			end
		end,
	}
end

return M
