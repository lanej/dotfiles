require("nvim-tree").setup({
  disable_netrw = false,
  hijack_netrw = true,
  auto_close = true,
  diagnostics = {
    enable = true,
    show_on_dirs = true,
  },
})

vim.api.nvim_set_keymap("n", "<leader>ntt", "<cmd>:NvimTreeToggle<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>ntc", "<cmd>:NvimTreeClose<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>ntf", "<cmd>:NvimTreeFindFile<CR>", {
  noremap = true,
  silent = true,
})
