vim.opt.runtimepath:prepend(vim.fn.stdpath("config"))
for _, name in ipairs({ "nvim-treesitter", "nvim-treesitter-textobjects" }) do
	vim.opt.runtimepath:append(vim.env.NVIM_BNF_PLUGINS .. "/" .. name)
end
vim.cmd("filetype on")
require("treesitter")
assert(vim.list_contains(require("treesitter-parsers"), "bnf"), "Bootstrap must include the BNF parser")

vim.cmd.edit(vim.env.NVIM_BNF_FIXTURE)
assert(vim.bo.filetype == "bnf", "The real filetype detector must recognize .bnf")
assert(vim.treesitter.highlighter.active[vim.api.nvim_get_current_buf()], "Opening BNF must start highlighting")
assert(vim.bo.indentexpr == "", "BNF must retain filetype indentation without an indent query")
local parser = vim.treesitter.get_parser(0, "bnf")
local root = parser:parse(true)[1]:root()
assert(not root:has_error(), root:sexpr())
local query = assert(vim.treesitter.query.get("bnf", "highlights"), "The installer must provide BNF queries")
local captures = {}
for id, node in query:iter_captures(root, 0) do
	local capture = query.captures[id]
	captures[capture] = captures[capture] or {}
	captures[capture][vim.treesitter.get_node_text(node, 0)] = true
end
assert(captures["type.definition"]["<expression>"], "Production names must be highlighted as definitions")
assert(captures.type["<number>"], "Nonterminals must be highlighted")
assert(captures.string and captures.string['"+"'] and captures.string['""'], "Quoted and empty terminals must be highlighted")
assert(captures.comment["# continuation"], "Comments must be highlighted")
assert(captures.operator["::="] and captures.operator["|"], "Definitions and alternatives must be highlighted")

vim.api.nvim_buf_set_lines(0, 0, -1, false, { '<broken> ::= "unterminated' })
assert(parser:parse(true)[1]:root():has_error(), "Malformed BNF must remain visible as a parse error")
print("PASS: opening BNF installs its parser, recognizes the filetype, parses grammar and escaped terminals, and highlights definitions, terminals, comments and operators.")
