local M = {}

local function clean(value)
	return (type(value) == "string" and value or "")
		:gsub("[%z\1-\32\127]", " ")
		:gsub(" ", " ")
		:gsub(" +", " ")
		:match("^%s*(.-)%s*$")
end

local function clip(text, width, from_end)
	if vim.fn.strdisplaywidth(text) <= width then
		return text
	end
	if width < 2 then
		return ""
	end
	local result = ""
	local codes = vim.fn.str2list(text)
	for index = 1, #codes do
		local char = vim.fn.nr2char(codes[from_end and (#codes - index + 1) or index])
		local candidate = from_end and (char .. result) or (result .. char)
		if vim.fn.strdisplaywidth(candidate .. "…") > width then
			break
		end
		result = candidate
	end
	return from_end and ("…" .. result) or (result .. "…")
end

local function git_changes(root)
	local changes, additions = {}, {}
	if not root then
		return changes, additions
	end
	local deadline = vim.uv.hrtime() + 1000000000
	local function run(arguments)
		local remaining = math.floor((deadline - vim.uv.hrtime()) / 1000000)
		if remaining <= 0 then
			return nil
		end
		local command = { "git", "--no-optional-locks", "-C", root }
		vim.list_extend(command, arguments)
		local ok, process = pcall(vim.system, command, { text = false })
		if not ok then
			return nil
		end
		local result = process:wait(remaining)
		return result.code == 0 and result.stdout or nil
	end
	local status = run({ "status", "--porcelain=v1", "-z", "--untracked-files=all" })
	local records = vim.split(status or "", "\0", { plain = true, trimempty = true })
	local index = 1
	while index <= #records do
		local record = records[index]
		local state = record:sub(1, 2)
		if state == "??" or state:sub(1, 1) == "A" then
			additions[vim.fs.normalize(root .. "/" .. record:sub(4))] = true
		end
		index = index + (state:find("[RC]") and 2 or 1)
	end
	-- WHY: Compare working files with HEAD so staged and unstaged edits are counted once together.
	local diff = run({ "diff", "--numstat", "-z", "--find-renames", "--no-ext-diff", "--no-textconv", "HEAD", "--" })
	records = vim.split(diff or "", "\0", { plain = true })
	index = 1
	while index <= #records do
		local added, removed, path = records[index]:match("^([^\t]+)\t([^\t]+)\t(.*)$")
		local step = 1
		if path == "" then
			path, step = records[index + 2], 3
		end
		if path then
			-- NOTE: Git reports '-' for binary files; absence of numeric data is not a zero count.
			changes[vim.fs.normalize(root .. "/" .. path)] = tonumber(added) and { tonumber(added), tonumber(removed) }
				or false
		end
		index = index + step
	end
	return changes, additions
end

local function new_file_lines(filename)
	local stat = vim.uv.fs_lstat(filename)
	if not stat or stat.type ~= "file" or stat.size > 1024 * 1024 then
		return nil
	end
	local fd = vim.uv.fs_open(filename, "r", 0)
	if not fd then
		return nil
	end
	local contents = vim.uv.fs_read(fd, stat.size, 0)
	vim.uv.fs_close(fd)
	if not contents or contents:find("\0", 1, true) then
		return nil
	end
	local _, lines = contents:gsub("\n", "")
	if #contents > 0 and contents:sub(-1) ~= "\n" then
		lines = lines + 1
	end
	return { lines, 0 }
end

local function abbreviated(number)
	local unit, suffix = 1, ""
	if number >= 1000000 then
		unit, suffix = 1000000, "m"
	elseif number >= 1000 then
		unit, suffix = 1000, "k"
	end
	if unit == 1 then
		return tostring(number)
	end
	return (string.format("%.1f", math.floor(number / unit * 10) / 10):gsub("%.0$", "")) .. suffix
end

local function badge(change)
	if not change then
		return ""
	end
	local utils = require("fzf-lua.utils")
	local result = {}
	if change[1] > 0 then
		result[#result + 1] = utils.ansi_from_hl("GitSignsAdd", "+" .. abbreviated(change[1]))
	end
	if change[2] > 0 then
		result[#result + 1] = utils.ansi_from_hl("GitSignsDelete", "−" .. abbreviated(change[2]))
	end
	return table.concat(result, " ")
end

local function short_paths(symbols, root, unique)
	local files, tree, paths = {}, { children = {} }, {}
	for _, symbol in ipairs(symbols) do
		if symbol.location then
			local file = vim.fs.normalize(vim.uri_to_fname(symbol.location.uri))
			if not files[file] then
				local parts = vim.split(file, "/", { plain = true, trimempty = true })
				files[file] = parts
				local node = tree
				for index = #parts, 1, -1 do
					local part = parts[index]
					node.children[part] = node.children[part] or { count = 0, children = {} }
					node = node.children[part]
					node.count = node.count + 1
				end
			end
		end
	end
	for file, parts in pairs(files) do
		-- WHY: Native FzfLua streams clients independently, so separate replies cannot share a suffix index.
		if not unique then
			paths[file] = (root and vim.fs.relpath(root, file)) or file
		end
		local node = tree
		for index = #parts, 1, -1 do
			node = node.children[parts[index]]
			if node.count == 1 or index == 1 then
				paths[file] = paths[file] or table.concat(parts, "/", index)
				break
			end
		end
	end
	return paths
end

local function label(symbol, parent, path, width, prefix_width)
	local name = clean(symbol.name)
	local remaining = width - vim.fn.strdisplaywidth(name) - prefix_width - 4
	local context = { "", "", "" }
	local candidates = { clean(symbol.detail), clean(symbol.containerName or parent) }
	if path then
		-- WHY: The hidden native path column must not make same-named workspace symbols indistinguishable.
		local text = clean(path)
		local part = clip(text, remaining - 2, true)
		remaining = remaining - vim.fn.strdisplaywidth(part) - 2
		local detail = candidates[1]
		if detail ~= "" and remaining >= 6 then
			local signature = clip(detail, remaining - 2)
			context[1] = signature
			remaining = remaining - vim.fn.strdisplaywidth(signature) - 2
		end
		if part ~= "" then
			context[2] = part
		end
	end
	for index, text in ipairs(candidates) do
		if not (path and index == 1) and text ~= "" and text ~= name and remaining >= 6 then
			local part = clip(text, math.min(remaining - 2, 28))
			context[index == 1 and 1 or 3] = part
			remaining = remaining - vim.fn.strdisplaywidth(part) - 2
		end
	end
	return name .. (table.concat(context) ~= "" and ("\t" .. table.concat(context, "\t")) or "")
end

function M.attach(opts, width)
	local handler = opts.lsp_handler
	if opts._navigation_context or not handler then
		return
	end
	local document = handler.method == "textDocument/documentSymbol"
	if not document and handler.method ~= "workspace/symbol" then
		return
	end
	opts._navigation_context = true
	local buf = vim.api.nvim_get_current_buf()
	local filename = vim.api.nvim_buf_get_name(buf)
	local root = vim.fs.root(buf, { ".git" })
	local unique = #vim.lsp.get_clients({ bufnr = buf, method = handler.method }) <= 1
	local changes, additions = git_changes(root)
	local original = handler.handler
	local utils = require("fzf-lua.utils")
	local _, _, mute = utils.ansi_from_hl("FzfLuaFzfInfo", "")
	local _, _, signature = utils.ansi_from_hl("FzfLuaSymbolSignature", "")
	local _, _, file_name = utils.ansi_from_hl("FzfLuaSymbolFile", "")
	local function symbol_context(text)
		local fields = vim.split(text, "\t", { plain = true })
		local parts = {}
		if fields[1] ~= "" then
			parts[#parts + 1] = signature(fields[1])
		end
		if fields[2] and fields[2] ~= "" then
			local directory, basename = fields[2]:match("^(.*[/])([^/]*)$")
			parts[#parts + 1] = (directory and mute(directory) or "") .. file_name(basename or fields[2])
		end
		if fields[3] and fields[3] ~= "" then
			parts[#parts + 1] = mute(fields[3])
		end
		return table.concat(parts, mute(" · "))
	end
	local _, name_style, emphasize = utils.ansi_from_hl("FzfLuaSymbolName", "")
	local function symbol_name(text)
		local icon, name = text:match("^(.- )(.+)$")
		name = name or text
		if name_style then
			name = name:gsub("\27%[0m", "%0" .. name_style)
		end
		return (icon or "") .. emphasize(name)
	end
	local badges, lookup = {}, {}
	local signatures = require("navigation-signature").new()
	local function for_file(file)
		local path = vim.fs.normalize(file)
		if badges[path] == nil then
			local change = changes[path]
			if change == nil and additions[path] then
				change = new_file_lines(path)
			end
			badges[path] = badge(change)
		end
		return badges[path]
	end
	local function enrich(symbols, parent, paths, encoding)
		local result = {}
		for _, symbol in ipairs(symbols) do
			local copy = vim.tbl_extend("force", {}, symbol)
			local file = symbol.location and vim.uri_to_fname(symbol.location.uri) or filename
			if not document and clean(copy.detail) == "" then
				copy.detail = signatures.detail(symbol, file, encoding)
			end
			local git = for_file(file)
			local kind = vim.lsp.protocol.SymbolKind[symbol.kind] or "Unknown"
			local icon = (opts.symbol_icons or {})[kind] or ""
			lookup[file] = git
			lookup[vim.uri_from_fname(file)] = git
			local relative = vim.fs.relpath(opts.cwd or root or vim.fn.getcwd(), file)
			if relative then
				lookup[relative] = git
			end
			copy.name = label(
				copy,
				parent,
				paths[vim.fs.normalize(file)],
				width,
				vim.fn.strdisplaywidth((utils.strip_ansi_coloring(git))) + vim.fn.strdisplaywidth(icon)
			)
			copy.containerName = nil
			if symbol.children then
				copy.children = enrich(symbol.children, symbol.name, paths, encoding)
			end
			result[#result + 1] = copy
		end
		return result
	end
	-- WHY: Clone the handler for this picker; never alter shared FzfLua handlers or LSP replies.
	opts.lsp_handler = vim.tbl_extend("force", {}, handler, {
		handler = function(options, emit, method, result, ctx, config)
			local response = vim.islist(result) and result or { result }
			signatures.begin()
			local client = vim.lsp.get_client_by_id(ctx.client_id)
			local symbols = enrich(
				response,
				nil,
				document and {} or short_paths(response, root, unique),
				client and client.offset_encoding
			)
			original(options, function(row, ...)
				local separator = document and "\t\t" or utils.nbsp
				local start, finish = row:find(separator, 1, true)
				if start then
					local git = document and (badges[vim.fs.normalize(filename)] or "") or ""
					if not document then
						local tail = utils.strip_ansi_coloring(row:sub(finish + 1))
						for _, part in ipairs(vim.split(tail, utils.nbsp, { plain = true })) do
							local file = part:match("^(.-):%d+:%d+:")
							if file then
								git = lookup[file] or ""
								break
							end
						end
					end
					local head, body, tail
					if document then
						head, body, tail = row:sub(1, finish), row:sub(finish + 1), ""
					else
						head, body, tail = "", row:sub(1, start - 1):gsub(" +$", ""), row:sub(start)
					end
					local title, detail = body:match("^(.-)\t(.*)$")
					if title then
						body = symbol_name(title) .. "  " .. symbol_context(detail)
					else
						body = symbol_name(body)
					end
					row = head .. (git ~= "" and (git .. " ") or "") .. body .. tail
				end
				emit(row, ...)
			end, method, symbols, ctx, config)
		end,
	})
end

return M
