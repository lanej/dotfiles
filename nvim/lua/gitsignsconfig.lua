require('gitsigns').setup({
  signs = {
    topdelete = {
      text = '^',
    },
  },
})

vim.api.nvim_set_keymap('n', '<leader>gw', ':Gitsigns stage_buffer<CR>', {
  silent = true,
  noremap = true,
})
vim.api.nvim_set_keymap('n', '<leader>gl', ':Gitsigns blame_line<CR>', {
  silent = true,
  noremap = true,
})

