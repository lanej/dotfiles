require'hop'.setup()

vim.api.nvim_set_keymap('n', '<leader><leader>w', '<cmd>:HopWord<CR>',        { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<leader><leader>b', '<cmd>:HopWordBC<CR>',      { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<leader><leader>f', '<cmd>:HopWordAC<CR>',      { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<leader><leader>l', '<cmd>:HopLineStart<CR>',   { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<leader><leader>j', '<cmd>:HopLineStartAC<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<leader><leader>k', '<cmd>:HopLineStartBC<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', ';', '<cmd>:HopPattern<CR>', { noremap = true, silent = true })