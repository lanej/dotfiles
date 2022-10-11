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
vim.api.nvim_set_keymap('n', ']c', ':Gitsigns next_hunk<CR>', {
  silent = true,
  noremap = true,
})
vim.api.nvim_set_keymap('n', '[c', ':Gitsigns prev_hunk<CR>', {
  silent = true,
  noremap = true,
})
vim.api.nvim_set_keymap('n', '<leader>hp', ':Gitsigns preview_hunk<CR>', {
  silent = true,
  noremap = true,
})
vim.api.nvim_set_keymap('n', '<leader>hs', ':Gitsigns stage_hunk<CR>', {
  silent = true,
  noremap = true,
})
vim.api.nvim_set_keymap('n', '<leader>hr', ':Gitsigns reset_hunk<CR>', {
  silent = true,
  noremap = true,
})
vim.api.nvim_set_keymap('n', '<leader>hu', ':Gitsigns undo_stage_hunk<CR>', {
  silent = true,
  noremap = true,
})
vim.api.nvim_set_keymap('n', 'vh', ':Gitsigns select_hunk<CR>', {
  silent = true,
  noremap = true,
})
