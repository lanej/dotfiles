require('gitsigns').setup({
  signs = {
    topdelete = {
      text = '^',
    },
  },
})

vim.keymap.set('n', '<leader>gw', require('gitsigns').stage_buffer, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>gl', require('gitsigns').blame_line, { silent = true, noremap = true })
vim.keymap.set('n', ']c', require('gitsigns').next_hunk, { silent = true, noremap = true })
vim.keymap.set('n', '[c', require('gitsigns').prev_hunk, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>hp', require('gitsigns').preview_hunk, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>hs', require('gitsigns').stage_hunk, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>hr', require('gitsigns').reset_hunk, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>hR', require('gitsigns').reset_buffer, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>hu', require('gitsigns').undo_stage_hunk, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>hU', require('gitsigns').reset_buffer_index, { silent = true, noremap = true })
vim.keymap.set('n', 'vh', require('gitsigns').select_hunk, { silent = true, noremap = true })
