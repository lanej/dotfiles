local cmp = require "cmp"

cmp.setup({
  snippet = {
    expand = function(args) vim.fn["vsnip#anonymous"](args.body) end,
  },
  mapping = {
    ["<C-d>"] = cmp.mapping.scroll_docs(-4),
    ["<C-f>"] = cmp.mapping.scroll_docs(4),
    ["<C-Space>"] = cmp.mapping.complete(),
    ["<C-e>"] = cmp.mapping.close(),
    ["<CR>"] = cmp.mapping.confirm({
      select = true,
    }),
  },
  sources = {
    {
      name = "path",
    },
    {
      name = "nvim_lsp",
    },
    {
      name = "buffer",
    },
    {
      name = "vsnip",
    },
  },
})

require("lspconfig").rust_analyzer.setup {
  capabilities = require("cmp_nvim_lsp").update_capabilities(vim.lsp.protocol
                                                               .make_client_capabilities()),
}

require("lspconfig").solargraph.setup {
  capabilities = require("cmp_nvim_lsp").update_capabilities(vim.lsp.protocol
                                                               .make_client_capabilities()),
}

require("lspconfig").sumneko_lua.setup {
  cmd = { "lua-language-server" },
  capabilities = require("cmp_nvim_lsp").update_capabilities(vim.lsp.protocol
                                                               .make_client_capabilities()),
}

require("lspconfig").gopls.setup {
  capabilities = require("cmp_nvim_lsp").update_capabilities(vim.lsp.protocol
                                                               .make_client_capabilities()),
}
