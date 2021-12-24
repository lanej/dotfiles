local lsp = require "lspconfig"

lsp.solargraph.setup {}
lsp.gopls.setup {}
lsp.vimls.setup {}
lsp.yamlls.setup {}
lsp.sumneko_lua.setup {
  cmd = { "lua-language-server" },
  settings = {
    Lua = {
      diagnostics = {
        globals = { "vim" },
      },
    },
  },
}
lsp.pylsp.setup {}
lsp.texlab.setup {}
lsp.jsonls.setup {
  commands = {
    Format = { function() vim.lsp.buf.range_formatting({}, { 0, 0 }, { vim.fn.line("$"), 0 }) end },
  },
}

lsp.rust_analyzer.setup({})

-- Enable diagnostics
vim.lsp.handlers["textDocument/publishDiagnostics"] =
  vim.lsp.with(vim.lsp.diagnostic.on_publish_diagnostics, {
    virtual_text = true,
    signs = false,
    update_in_insert = true,
  })

vim.api.nvim_set_keymap("n", "K", "<cmd>lua vim.lsp.buf.hover()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>cd", "<cmd>lua vim.lsp.buf.definition()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>cr", "<cmd>lua vim.lsp.buf.references()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>d", "<cmd>lua vim.lsp.buf.formatting_sync()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>ci", "<cmd>lua vim.lsp.buf.implementation()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>cy", "<cmd>lua vim.lsp.buf.type_definition()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>ca", "<cmd>lua vim.lsp.buf.code_action()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<c-p>", "<cmd>lua vim.lsp.diagnostic.goto_prev()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<c-n>", "<cmd>lua vim.lsp.diagnostic.goto_next()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<space>c", "<cmd>lua vim.lsp.diagnostic.set_loclist()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "g?", "<cmd>lua vim.lsp.diagnostic.show_line_diagnostics()<CR>", {
  noremap = true,
  silent = true,
})
