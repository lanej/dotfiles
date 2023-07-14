require('nvim-window').setup({
  -- The characters available for hinting windows.
  chars = { 'j', 'k', 'l', 'h', 'a', 's', 'd', 'f' },
  -- A group to use for overwriting the Normal highlight group in the floating
  -- window. This can be used to change the background color.
  normal_hl = 'Type',
  -- The highlight group to apply to the line that contains the hint characters.
  -- This is used to make them stand out more.
  hint_hl = 'Bold',
  -- The border style to use for the floating window.
  border = 'double'
})

vim.api.nvim_set_keymap('n', '<c-w><c-w>', '<cmd>lua require("nvim-window").pick()<CR>',
  { noremap = true, silent = true })
