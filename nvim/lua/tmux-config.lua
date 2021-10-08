vim.g.tmux_navigator_no_mappings =1
vim.g.tmux_navigator_save_on_switch = 1

vim.api.nvim_set_keymap('n', '<C-h>',':TmuxNavigateLeft<cr>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<C-j>',':TmuxNavigateDown<cr>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<C-k>',':TmuxNavigateUp<cr>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<C-l>',':TmuxNavigateRight<cr>', { noremap = true, silent = true })
