-- Phabricator LSP configuration
-- Provides hover tooltips and autocomplete for Phabricator object references
-- Supports: T123 (tasks), D456 (revisions)

-- Start Phabricator LSP server for relevant file types
vim.api.nvim_create_autocmd("FileType", {
	pattern = { "markdown", "gitcommit", "text" },
	callback = function(args)
		-- Only start LSP if .arcrc exists (indicates Phabricator environment)
		if vim.fn.filereadable(vim.fn.expand("~/.arcrc")) == 0 then
			return
		end

		local client_id = vim.lsp.start({
			name = "phab-lsp",
			cmd = { "phab", "lsp", "stdio" },
			root_dir = vim.fn.getcwd(),
			settings = {},
			on_attach = function(client, bufnr)
				-- Optional: Add buffer-specific keymaps here
				vim.notify(string.format("Phabricator LSP attached to buffer %d", bufnr), vim.log.levels.DEBUG)
			end,
		})

		if client_id then
			vim.notify("Phabricator LSP started", vim.log.levels.DEBUG)
		end
	end,
})
