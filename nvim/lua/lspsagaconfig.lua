require('lspsaga').init_lsp_saga()

vim.api.nvim_set_keymap('v', '<leader>ca', '<cmd><C-U>Lspsaga range_code_action<CR>', {
  silent = true,
  noremap = true,
})
vim.api.nvim_set_keymap('n', '<leader>rn', '<cmd>Lspsaga rename<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>ca', '<cmd>Lspsaga code_action<CR>', {
  silent = true,
  noremap = true,
})
