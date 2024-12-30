vim.keymap.set("n", "K", function()
	vim.lsp.buf.hover()
end, {
	noremap = true,
	silent = true,
})
vim.keymap.set("n", "<leader>cd", function()
	vim.lsp.buf.definition()
end, {
	noremap = true,
	silent = true,
})
vim.keymap.set("n", "<leader>cr", function()
	vim.lsp.buf.references()
end, {
	noremap = false,
	silent = true,
})
-- go to errors first, warnings second
vim.keymap.set("n", "<c-p>", function()
	vim.diagnostic.goto_prev()
end, {
	noremap = true,
	silent = true,
})
vim.keymap.set("n", "<c-n>", function()
	vim.diagnostic.goto_next()
end, {
	noremap = true,
	silent = true,
})

vim.keymap.set("n", "<space>wa", vim.lsp.buf.add_workspace_folder, { noremap = true, silent = true })
vim.keymap.set("n", "<space>wr", vim.lsp.buf.remove_workspace_folder, { noremap = true, silent = true })
