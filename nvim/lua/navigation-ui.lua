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

function M.window()
	local wide = vim.o.columns >= 180
	return {
		width = math.min(wide and 140 or 100, math.max(1, vim.o.columns - 6)),
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
		symbol_style = 1,
		symbol_hl = function(kind)
			return kind_highlights[kind] or "Identifier"
		end,
		symbol_fmt = function(symbol)
			return symbol
		end,
		-- WHY: Hide location metadata only in fzf's display; native previews and jumps retain it.
		fzf_opts = document and { ["--delimiter"] = "\t+", ["--with-nth"] = "2.." }
			or { ["--delimiter"] = ":", ["--with-nth"] = "..-3" },
	}
end

function M.locations()
	return {
		winopts = M.window,
		fzf_opts = { ["--delimiter"] = ":", ["--with-nth"] = "1,4.." },
	}
end

return M
