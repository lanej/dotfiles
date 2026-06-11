require("nvim-treesitter").setup()

-- MDX: custom parser combining Markdown + JSX (not in nvim-treesitter built-in list)
-- Install/update with :TSInstall mdx
local parsers = require("nvim-treesitter.parsers")
parsers["mdx"] = {
	install_info = {
		url = "https://github.com/srazzak/tree-sitter-mdx",
		files = { "src/parser.c", "src/scanner.c" },
		branch = "main",
	},
	filetype = "mdx",
}

-- Install parsers that aren't already present
require("nvim-treesitter.install").install(
	{ "lua", "bash", "rust", "python", "ruby", "json", "yaml", "toml", "typst", "xml", "regex", "markdown", "markdown_inline", "mdx" },
	{ skip = { installed = true } }
)

-- Enable treesitter highlighting and indentation per filetype
vim.api.nvim_create_autocmd("FileType", {
	callback = function()
		pcall(vim.treesitter.start)
		if pcall(require, "nvim-treesitter.indent") then
			vim.bo.indentexpr = "v:lua.require('nvim-treesitter').indentexpr()"
		end
	end,
})

-- Textobjects
require("nvim-treesitter-textobjects").setup({
	select = { lookahead = true },
	move = { set_jumps = true },
})

local sel = require("nvim-treesitter-textobjects.select")
local mov = require("nvim-treesitter-textobjects.move")
local swp = require("nvim-treesitter-textobjects.swap")

local function map(modes, lhs, fn)
	vim.keymap.set(modes, lhs, fn)
end

local g = "textobjects"

-- Select textobjects
map({ "x", "o" }, "am", function() sel.select_textobject("@function.outer", g) end)
map({ "x", "o" }, "im", function() sel.select_textobject("@function.inner", g) end)
map({ "x", "o" }, "ac", function() sel.select_textobject("@class.outer", g) end)
map({ "x", "o" }, "ic", function() sel.select_textobject("@class.inner", g) end)
map({ "x", "o" }, "ab", function() sel.select_textobject("@block.outer", g) end)
map({ "x", "o" }, "ib", function() sel.select_textobject("@block.inner", g) end)
map({ "x", "o" }, "ap", function() sel.select_textobject("@parameter.outer", g) end)
map({ "x", "o" }, "ip", function() sel.select_textobject("@parameter.inner", g) end)
map({ "x", "o" }, "ai", function() sel.select_textobject("@conditional.outer", g) end)
map({ "x", "o" }, "ii", function() sel.select_textobject("@conditional.inner", g) end)
map({ "x", "o" }, "ax", function() sel.select_textobject("@call.outer", g) end)
map({ "x", "o" }, "ix", function() sel.select_textobject("@call.inner", g) end)
map({ "x", "o" }, "an", function() sel.select_textobject("@statement.outer", g) end)

-- Move
map("n", "]m", function() mov.goto_next_start("@function.outer", g) end)
map("n", "]]", function() mov.goto_next_start("@class.outer", g) end)
map("n", "]b", function() mov.goto_next_start("@block.outer", g) end)
map("n", "]M", function() mov.goto_next_end("@function.outer", g) end)
map("n", "][", function() mov.goto_next_end("@class.outer", g) end)
map("n", "]B", function() mov.goto_next_end("@block.outer", g) end)
map("n", "[m", function() mov.goto_previous_start("@function.outer", g) end)
map("n", "[[", function() mov.goto_previous_start("@class.outer", g) end)
map("n", "[b", function() mov.goto_previous_start("@block.outer", g) end)
map("n", "[M", function() mov.goto_previous_end("@function.outer", g) end)
map("n", "[]", function() mov.goto_previous_end("@class.outer", g) end)
map("n", "[B", function() mov.goto_previous_end("@block.outer", g) end)

-- Swap
map("n", "<leader>a", function() swp.swap_next("@parameter.inner", g) end)
map("n", "<leader>m", function() swp.swap_next("@function.outer", g) end)
map("n", "<leader>A", function() swp.swap_previous("@parameter.inner", g) end)
map("n", "<leader>M", function() swp.swap_previous("@function.outer", g) end)
