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

local function git_status(root)
	if not root then
		return {}
	end
	local ok, process = pcall(
		vim.system,
		{ "git", "--no-optional-locks", "-C", root, "status", "--porcelain=v1", "-z", "--untracked-files=all" },
		{ text = false }
	)
	if not ok then
		return {}
	end
	local result = process:wait(1000)
	if result.code ~= 0 then
		return {}
	end
	local records = vim.split(result.stdout or "", "\0", { plain = true, trimempty = true })
	local statuses, index = {}, 1
	while index <= #records do
		local record = records[index]
		local status = record:sub(1, 2)
		statuses[vim.fs.normalize(root .. "/" .. record:sub(4))] = status
		-- NOTE: Porcelain -z puts the rename/copy destination before a second source-path record.
		index = index + (status:find("[RC]") and 2 or 1)
	end
	return statuses
end

local function badge(status)
	if not status then
		return ""
	end
	local icons = {
		M = { "", "yellow" },
		A = { "", "green" },
		D = { "", "red" },
		R = { "", "yellow" },
		C = { "", "cyan" },
		T = { "", "magenta" },
		["?"] = { "", "magenta" },
	}
	local ansi = require("fzf-lua.utils").ansi_codes
	if status:find("U", 1, true) or status == "AA" or status == "DD" then
		return ansi.red("")
	end
	local result = {}
	for index = 1, 2 do
		local code = status:sub(index, index)
		if code ~= " " and not (index == 2 and code == "?" and status:sub(1, 1) == "?") then
			local icon = icons[code]
			if icon then
				local color = index == 1 and code ~= "?" and "green" or icon[2]
				result[#result + 1] = ansi[color](icon[1])
			end
		end
	end
	return table.concat(result)
end

local function short_path(root, filename)
	local relative = root and vim.fs.relpath(root, filename) or filename
	local parts = vim.split(relative or filename, "/", { plain = true, trimempty = true })
	if #parts > 2 then
		return "…/" .. table.concat(parts, "/", #parts - 1)
	end
	return table.concat(parts, "/")
end

local function label(symbol, parent, filename, root, width, document)
	local name = clean(symbol.name)
	local remaining = width - vim.fn.strdisplaywidth(name) - 18
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
	local statuses = git_status(root)
	local original = handler.handler
	local utils = require("fzf-lua.utils")
	local _, _, mute = utils.ansi_from_hl("Comment", "")
	local badges, lookup = {}, {}
	for path, status in pairs(statuses) do
		badges[path] = badge(status)
	end
	local function enrich(symbols, parent)
		local result = {}
		for _, symbol in ipairs(symbols) do
			local copy = vim.tbl_extend("force", {}, symbol)
			local file = symbol.location and vim.uri_to_fname(symbol.location.uri) or filename
			local git = badges[vim.fs.normalize(file)] or ""
			lookup[file] = git
			lookup[vim.uri_from_fname(file)] = git
			local relative = vim.fs.relpath(opts.cwd or root or vim.fn.getcwd(), file)
			if relative then
				lookup[relative] = git
			end
			copy.name = label(symbol, parent, file, root, width, document)
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
