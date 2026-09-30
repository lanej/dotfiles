vim.keymap.set("n", "K", function()
	vim.lsp.buf.hover()
end, {
	noremap = true,
	silent = true,
})
-- go to errors first, warnings second
vim.keymap.set("n", "<c-p>", function()
	vim.diagnostic.goto_prev({ float = false })
end, {
	noremap = true,
	silent = true,
})
vim.keymap.set("n", "<c-n>", function()
	vim.diagnostic.goto_next({ float = false })
end, {
	noremap = true,
	silent = true,
})

vim.keymap.set("n", "<space>wa", vim.lsp.buf.add_workspace_folder, { noremap = true, silent = true })
vim.keymap.set("n", "<space>wr", vim.lsp.buf.remove_workspace_folder, { noremap = true, silent = true })

-- There is no :LspRestart here (this config uses the native vim.lsp.enable()
-- API, not nvim-lspconfig's commands), so stop each attached client and
-- restart it from its own captured config.
vim.keymap.set("n", "<leader>lr", function()
	local bufnr = vim.api.nvim_get_current_buf()
	local clients = vim.lsp.get_clients({ bufnr = bufnr })
	if #clients == 0 then
		vim.notify("lsp: no clients attached", vim.log.levels.WARN)
		return
	end
	local configs = {}
	for _, client in ipairs(clients) do
		table.insert(configs, client.config)
		client:stop(true)
	end
	vim.defer_fn(function()
		for _, config in ipairs(configs) do
			vim.lsp.start(config, { bufnr = bufnr })
		end
		vim.notify("lsp: restarted", vim.log.levels.INFO)
	end, 300)
end, { noremap = true, silent = true, desc = "Restart LSP clients for buffer" })
