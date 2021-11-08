--nnoremap <silent>gr <cmd>lua require('lspsaga.rename').rename()<CR>

vim.api.nvim_set_keymap("n", "<leader>rn", "<cmd>lua require('lspsaga.rename').rename()<CR>", {
  noremap = true,
  silent = true,
})
