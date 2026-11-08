local M = {}

local kind_highlights = {
	File = "Directory",
	Module = "Include",
	Namespace = "Include",
	Package = "Include",
	Class = "Type",
	Struct = "Type",
	Interface = "Type",
	Enum = "Type",
	TypeParameter = "Type",
	Method = "Function",
	Function = "Function",
	Constructor = "Function",
	Property = "Identifier",
	Field = "Identifier",
	Variable = "Identifier",
	Key = "Identifier",
	Constant = "@constant",
	EnumMember = "@constant",
	String = "String",
	Number = "Number",
	Boolean = "Boolean",
	Null = "@constant",
	Array = "Type",
	Object = "Type",
	Event = "Special",
	Operator = "Operator",
}

local function previewer(spec)
	if type(spec) == "function" then
		return function()
			return previewer(spec())
		end
	end
	local config = require("fzf-lua.config")
	local defaults = config.globals.previewers.builtin
	local tags = type(spec) == "table" and spec._ctor == config.defaults.tags.previewer._ctor
	if
		spec ~= "builtin"
		and spec ~= true
		and not tags
		and not (type(spec) == "table" and spec._ctor == defaults._ctor)
	then
		return spec
	end
	local native = require("fzf-lua.previewer.builtin")[tags and "tags" or "buffer_or_file"]
	local custom = native:extend()
	function custom:update_title(entry)
		local title_entry = vim.tbl_extend("force", {}, entry)
		title_entry.bufnr = nil
		return native.update_title(self, title_entry)
	end
	return vim.tbl_extend("force", {}, defaults, type(spec) == "table" and spec or {}, {
		_ctor = function()
			return custom
		end,
		title_fnamemodify = function(title)
			return title
		end,
	})
end

local function symbol_title(opts)
	local method = opts.lsp_handler and opts.lsp_handler.method
	if method ~= "textDocument/documentSymbol" and method ~= "workspace/symbol" then
		return nil
	end
	local buf = vim.api.nvim_get_current_buf()
	local root = vim.fs.root(buf, { ".git" }) or opts.cwd or vim.fn.getcwd()
	local file = vim.api.nvim_buf_get_name(buf)
	local scope = method == "workspace/symbol" and vim.fs.basename(root)
		or vim.fs.relpath(root, file)
		or vim.fn.fnamemodify(file, ":~:.")
	local names, seen = {}, {}
	for _, client in ipairs(vim.lsp.get_clients({ bufnr = buf, method = method })) do
		if not seen[client.name] then
			names[#names + 1], seen[client.name] = client.name, true
		end
	end
	table.sort(names)
	return " " .. scope .. (#names > 0 and (" · " .. table.concat(names, ", ")) or "") .. " "
end

function M.window(opts)
	local wide = vim.o.columns >= 180
	local width = math.min(wide and 140 or 100, math.max(1, vim.o.columns - 6))
	if opts then
		require("navigation-context").attach(opts, (wide and math.floor(width * 0.45) or width) - 4)
		opts.previewer = previewer(opts.previewer)
	end
	return {
		title = opts and symbol_title(opts) or nil,
		width = width,
		height = math.min(wide and 22 or 26, math.max(1, vim.o.lines - 6)),
		row = 0.5,
		col = 0.5,
		border = "double",
		preview = {
			layout = wide and "horizontal" or "vertical",
			horizontal = "right:55%",
			vertical = "down:60%",
		},
	}
end

function M.symbols(document)
	return {
		symbol_style = 2,
		no_header_i = true,
		winopts = M.window,
		child_prefix = false,
		symbol_hl = function(kind)
			return kind_highlights[kind] or "Identifier"
		end,
		symbol_fmt = function(symbol)
			return symbol
		end,
		-- WHY: Hide location metadata only in fzf's display; native previews and jumps retain it.
		fzf_opts = document and { ["--delimiter"] = "\t+", ["--with-nth"] = "2..", ["--no-wrap"] = true }
			or { ["--delimiter"] = require("fzf-lua.utils").nbsp, ["--with-nth"] = "1", ["--no-wrap"] = true },
	}
end

function M.locations()
	return {
		winopts = M.window,
		fzf_opts = { ["--delimiter"] = ":", ["--with-nth"] = "1,4.." },
	}
end

return M
