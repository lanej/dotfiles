vim.api.nvim_set_keymap("n", "<leader>rn", "<cmd>lua require('lspsaga.rename').rename()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>lf", "<cmd>lua require'lspsaga.provider'.lsp_finder()<CR>", {
  noremap = true,
  silent = true,
})
 
