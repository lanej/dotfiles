require("nvim-treesitter").setup()

-- MDX: custom parser combining Markdown + JSX (not in nvim-treesitter built-in list).
-- Registered on TSUpdate because install/update reloads the parser table, dropping
-- entries added directly.
vim.api.nvim_create_autocmd("User", {
	pattern = "TSUpdate",
	callback = function()
		local parsers = require("nvim-treesitter.parsers")
		parsers.mdx = {
			install_info = {
				url = "https://github.com/srazzak/tree-sitter-mdx",
				branch = "main",
			},
		}
		parsers.sql_bigquery = {
			install_info = {
				url = "https://github.com/lanej/tree-sitter-sql-bigquery",
				branch = "fix/query-time-travel-and-if",
				revision = "db6ed431534e3f60189481a533c7662328866ad8",
				queries = "queries",
			},
		}
	end,
})

require("bigquery").setup()

-- Install parsers that aren't already present
if not vim.env.DOTFILES_NVIM_BOOTSTRAP then
	require("nvim-treesitter.install").install(require("treesitter-parsers"))
end

-- Install a missing parser synchronously so the buffer's first draw has treesitter.
-- Languages that fail or time out are not retried this session, so a bad parser
-- can't stall every buffer of that filetype.
local available
local failed = {}

local function ensure_parser(lang)
	if vim.treesitter.language.add(lang) then
		return true
	end
	if failed[lang] then
		return false
	end
	available = available or require("nvim-treesitter").get_available()
	if not vim.list_contains(available, lang) then
		return false
	end
	local ok, installed = require("nvim-treesitter").install(lang):pwait(60000)
	if not (ok and installed) then
		failed[lang] = true
		vim.notify("treesitter: failed to install parser for " .. lang, vim.log.levels.WARN)
		return false
	end
	return vim.treesitter.language.add(lang) == true
end

-- Enable treesitter highlighting and indentation per filetype
vim.api.nvim_create_autocmd("FileType", {
	callback = function(args)
		local lang = vim.treesitter.language.get_lang(args.match)
		if not (lang and ensure_parser(lang)) then
			return
		end
		pcall(vim.treesitter.start, args.buf, lang)
		-- The BigQuery grammar ships highlights only; retain the SQL ftplugin's indent.
		if lang ~= "sql_bigquery" and pcall(require, "nvim-treesitter.indent") then
			vim.bo.indentexpr = "v:lua.require('nvim-treesitter').indentexpr()"
		end
	end,
})

-- Node selection (built-in vim.treesitter.select): <leader>o selects the node under
-- the cursor (e.g. the whole table from its `{`) and expands outward on repeat;
-- <leader>i shrinks inward.
vim.keymap.set({ "n", "x" }, "<leader>o", function() vim.treesitter.select("parent", vim.v.count1) end)
vim.keymap.set("x", "<leader>i", function() vim.treesitter.select("child", vim.v.count1) end)

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
