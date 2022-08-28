require('trouble').setup {
  vim.api.nvim_set_keymap('n', '<leader>tx', '<cmd>Trouble<cr>', {
    silent = true,
    noremap = true,
  }),
  vim.api.nvim_set_keymap('n', '<leader>tw', '<cmd>Trouble workspace_diagnostics<cr>', {
    silent = true,
    noremap = true,
  }),
  vim.api.nvim_set_keymap('n', '<leader>td', '<cmd>Trouble document_diagnostics<cr>', {
    silent = true,
    noremap = true,
  }),
  vim.api.nvim_set_keymap('n', '<leader>tl', '<cmd>Trouble loclist<cr>', {
    silent = true,
    noremap = true,
  }),
  vim.api.nvim_set_keymap('n', '<leader>tq', '<cmd>Trouble quickfix<cr>', {
    silent = true,
    noremap = true,
  }),
  vim.api.nvim_set_keymap('n', '<leader>cr', '<cmd>Trouble lsp_references<cr>', {
    silent = true,
    noremap = true,
  }),
  -- This doesn't seem to work
  --[[ vim.api.nvim_set_keymap('n', '<leader>cd', '<cmd>Trouble lsp_definitions<cr>', {
            silent = true,
            noremap = true,
          }), ]]
  vim.api.nvim_set_keymap('n', '<leader>ci', '<cmd>Trouble lsp_implementations<cr>', {
    silent = true,
    noremap = true,
  }),
  vim.api.nvim_set_keymap('n', '<leader>cy', '<cmd>Trouble lsp_type_definitions<cr>', {
    silent = true,
    noremap = true,
  }),
}
