-- PKM LSP configuration
-- Provides wikilink autocomplete and frontmatter field completion for markdown files
-- Supports: [[wikilinks]], frontmatter field names and values
--
-- Smart selection: uses pkm-lsp in PKM workspaces (.lancedb), Marksman elsewhere

-- Start PKM LSP or Marksman for markdown files based on workspace type
vim.api.nvim_create_autocmd("FileType", {
	pattern = "markdown",
	callback = function(args)
		local bufnr = args.buf

		-- Check if any markdown LSP is already attached to this buffer
		local clients = vim.lsp.get_clients({ bufnr = bufnr })
		for _, client in ipairs(clients) do
			if client.name == "pkm-lsp" or client.name == "marksman" then
				vim.notify(client.name .. " already attached", vim.log.levels.DEBUG)
				return
			end
		end

		-- Detect workspace type by checking for PKM markers
		local root_dir = vim.fs.root(args.file, { ".lancedb", ".git", ".marksman.toml" })
		local is_pkm_workspace = root_dir and vim.fn.isdirectory(root_dir .. "/.lancedb") == 1

		if is_pkm_workspace then
			-- PKM workspace: use pkm-lsp for wikilink completions
			local client_id = vim.lsp.start({
				name = "pkm-lsp",
				cmd = { "pkm", "lsp" },
				root_dir = root_dir,
				settings = {},
				on_attach = function(client, bufnr)
					vim.notify("PKM LSP attached to buffer " .. bufnr, vim.log.levels.DEBUG)
				end,
			})

			if client_id then
				vim.notify("PKM LSP started", vim.log.levels.DEBUG)
			end
		elseif root_dir then
			-- Regular markdown: use Marksman for wikilink support
			local client_id = vim.lsp.start({
				name = "marksman",
				cmd = { "marksman", "server" },
				root_dir = root_dir,
				filetypes = { "markdown" },
				settings = {},
				on_attach = function(client, bufnr)
					vim.notify("Marksman LSP attached to buffer " .. bufnr, vim.log.levels.DEBUG)
				end,
			})

			if client_id then
				vim.notify("Marksman LSP started", vim.log.levels.DEBUG)
			end
		end
	end,
})
