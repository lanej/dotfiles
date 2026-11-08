local M = {}

local function has_lsp(method)
	local buf = vim.api.nvim_get_current_buf()
	for _, client in ipairs(vim.lsp.get_clients({ bufnr = buf })) do
		if client.initialized and not client:is_stopped() and client:supports_method(method, buf) then
			return true
		end
	end
	return false
end

local function project_options()
	local buf = vim.api.nvim_get_current_buf()
	return {
		cwd = vim.fs.root(buf, { ".git" }) or vim.fs.dirname(vim.api.nvim_buf_get_name(buf)) or vim.fn.getcwd(),
	}
end

local function text_search(title)
	local word = vim.fn.expand("<cword>")
	if word == "" then
		return
	end
	local opts = project_options()
	opts.search = word
	opts.rg_opts =
		"--column --line-number --no-heading --color=always --smart-case --hidden --glob=!.git --fixed-strings --word-regexp"
	opts.prompt = title .. " · Text matches❯ "
	require("fzf-lua").grep(opts)
end

function M.goto_definition()
	local fzf = require("fzf-lua")
	if has_lsp("textDocument/definition") then
		return fzf.lsp_definitions({ jump1 = true })
	end
	local word = vim.fn.expand("<cword>")
	local pattern = "\\C^" .. vim.fn.escape(word, [[\.^$~[]*]]) .. "$"
	-- WHY: Tag lookup must not invoke vim.lsp.tagfunc when LSP is unavailable.
	local tagfunc = vim.bo.tagfunc
	vim.bo.tagfunc = ""
	local ok, matches = pcall(vim.fn.taglist, pattern)
	vim.bo.tagfunc = tagfunc
	if ok and word ~= "" and #matches > 0 then
		local opts = project_options()
		opts.search = "^" .. vim.fn.escape(word, [=[\.^$|?*+(){}[]]=]) .. "\t"
		opts.no_esc = true
		opts.prompt = "Definitions · Tags❯ "
		return fzf.tags(opts)
	end
	if not ok then
		vim.notify("Tags: " .. tostring(matches), vim.log.levels.WARN)
	end
	text_search("Definitions")
end

function M.references()
	if has_lsp("textDocument/references") then
		return require("fzf-lua").lsp_references()
	end
	text_search("References")
end

function M.implementations()
	if has_lsp("textDocument/implementation") then
		return require("fzf-lua").lsp_implementations()
	end
	text_search("Implementations")
end

function M.buffer_symbols()
	local fzf = require("fzf-lua")
	local opts = {
		winopts = { relative = "cursor", width = 0.5, height = 0.8, border = "double" },
	}
	if has_lsp("textDocument/documentSymbol") then
		return fzf.lsp_document_symbols(opts)
	end
	opts.cwd = project_options().cwd
	opts.prompt = "Buffer symbols · Tags (saved)❯ "
	return fzf.btags(opts)
end

function M.workspace_symbols()
	local fzf = require("fzf-lua")
	if has_lsp("workspace/symbol") then
		return fzf.lsp_live_workspace_symbols({})
	end
	local opts = project_options()
	opts.prompt = "Workspace symbols · Tags❯ "
	return fzf.tags(opts)
end

return M
