require('trouble').setup {
  focus = true,
  follow = true,
  pinning = true,
  auto_jump = true, -- if there is only one result, jump to it
  vim.api.nvim_set_keymap('n', '<leader>dt', '<cmd>TroubleToggle<cr>', {
    silent = true,
    noremap = true,
  }),
  vim.api.nvim_set_keymap('n', '<leader>dd', '<cmd>Trouble diagnostics<cr>', {
    silent = true,
    noremap = true,
  }),
  vim.api.nvim_set_keymap('n', '<leader>cl', '<cmd>Trouble loclist<cr>', {
    silent = true,
    noremap = true,
  }),
  vim.api.nvim_set_keymap('n', '<leader>dq', '<cmd>Trouble close<cr>', {
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


vim.api.nvim_create_autocmd("FileType", {
  pattern = "trouble",
  callback = function()
    vim.keymap.set('n', '<c-n>', function() require("trouble").next() end, { noremap = true, silent = true, buffer = 0 })
    vim.keymap.set('n', '<c-p>', function() require("trouble").prev() end, { noremap = true, silent = true, buffer = 0 })
    vim.keymap.set('n', '<S-K>', function() require("trouble").toggle_preview() end, { noremap = true, silent = true, buffer = 0 })
    vim.keymap.set('n', '<c-Enter>', function() require("trouble").jump_close() end, { noremap = true, silent = true, buffer = 0 })
  end
})
