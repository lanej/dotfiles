require('lspsaga').setup({
  diagnostic = {
    show_code_action = false,
  },
  symbol_in_winbar = {
    enable = true,
    separator = " ",
    ignore_patterns={},
    hide_keyword = true,
    show_file = true,
    folder_level = 3,
    respect_root = true,
    color_mode = true,
  },
  code_action_lightbulb = {
    enable = false,
  },
})

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
