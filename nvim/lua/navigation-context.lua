local M = {}

local function clean(value)
	return (type(value) == "string" and value or "")
		:gsub("[%z\1-\32\127]", " ")
		:gsub(" ", " ")
		:gsub(" +", " ")
		:match("^%s*(.-)%s*$")
end

local function clip(text, width)
	if vim.fn.strdisplaywidth(text) <= width then
		return text
	end
	if width < 2 then
		return ""
	end
	local result = ""
	for _, code in ipairs(vim.fn.str2list(text)) do
		local char = vim.fn.nr2char(code)
		if vim.fn.strdisplaywidth(result .. char .. "…") > width then
			break
		end
		result = result .. char
	end
	return result .. "…"
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
	local ansi = require("fzf-lua.utils").ansi_codes
	local result = {}
	if change[1] > 0 then
		result[#result + 1] = ansi.green("+" .. abbreviated(change[1]))
	end
	if change[2] > 0 then
		result[#result + 1] = ansi.red("−" .. abbreviated(change[2]))
	end
	return table.concat(result, " ")
end

local function short_path(root, filename)
	local relative = root and vim.fs.relpath(root, filename) or filename
	local parts = vim.split(relative or filename, "/", { plain = true, trimempty = true })
	if #parts > 2 then
		return "…/" .. table.concat(parts, "/", #parts - 1)
	end
	return table.concat(parts, "/")
end

local function label(symbol, parent, filename, root, width, document, git_width)
	local name = clean(symbol.name)
	local kind = vim.lsp.protocol.SymbolKind[symbol.kind] or "Unknown"
	local remaining = width - vim.fn.strdisplaywidth(name) - vim.fn.strdisplaywidth(kind) - git_width - 4
	local context = {}
	local candidates = { clean(symbol.detail), clean(symbol.containerName or parent) }
	if not document then
		-- WHY: The hidden native path column must not make same-named workspace symbols indistinguishable.
		table.insert(candidates, 1, clean(short_path(root, filename)))
	end
	for _, text in ipairs(candidates) do
		if text ~= "" and text ~= name and remaining >= 6 then
			local part = clip(text, math.min(remaining - 2, 28))
			context[#context + 1] = part
			remaining = remaining - vim.fn.strdisplaywidth(part) - 2
		end
	end
	return name .. (#context > 0 and ("\t" .. table.concat(context, " · ")) or "")
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
	local changes, additions = git_changes(root)
	local original = handler.handler
	local utils = require("fzf-lua.utils")
	local _, _, mute = utils.ansi_from_hl("Comment", "")
	local badges, lookup = {}, {}
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
	local function enrich(symbols, parent)
		local result = {}
		for _, symbol in ipairs(symbols) do
			local copy = vim.tbl_extend("force", {}, symbol)
			local file = symbol.location and vim.uri_to_fname(symbol.location.uri) or filename
			local git = for_file(file)
			lookup[file] = git
			lookup[vim.uri_from_fname(file)] = git
			local relative = vim.fs.relpath(opts.cwd or root or vim.fn.getcwd(), file)
			if relative then
				lookup[relative] = git
			end
			copy.name = label(
				symbol,
				parent,
				file,
				root,
				width,
				document,
				vim.fn.strdisplaywidth((utils.strip_ansi_coloring(git)))
			)
			copy.containerName = nil
			if symbol.children then
				copy.children = enrich(symbol.children, symbol.name)
			end
			result[#result + 1] = copy
		end
		return result
	end
	-- WHY: Clone the handler for this picker; never alter shared FzfLua handlers or LSP replies.
	opts.lsp_handler = vim.tbl_extend("force", {}, handler, {
		handler = function(options, emit, method, result, ctx, config)
			local symbols = enrich(vim.islist(result) and result or { result })
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
						body = title .. "  " .. mute(detail)
					end
					row = head .. (git ~= "" and (git .. " ") or "") .. body .. tail
				end
				emit(row, ...)
			end, method, symbols, ctx, config)
		end,
	})
end

return M
