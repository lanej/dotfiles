local cmp = require "cmp"

cmp.setup({
  snippet = {
    expand = function(args) vim.fn["vsnip#anonymous"](args.body) end,
  },
  mapping = {
    ["<C-d>"] = cmp.mapping.scroll_docs(-4),
    ["<C-f>"] = cmp.mapping.scroll_docs(4),
    ["<C-e>"] = cmp.mapping.close(),
    ["<CR>"] = cmp.mapping.confirm({
      select = true,
    }),
  },
  sources = {
    {
      name = "nvim_lsp",
    },
    {
      name = "buffer",
    },
    {
      name = "path",
    },
    {
      name = "vsnip",
    },
    {
      name = "tmux",
    },
  },
})

local capabilities = vim.lsp.protocol.make_client_capabilities()
capabilities.textDocument.completion.completionItem.snippetSupport = true
capabilities.textDocument.completion.completionItem.resolveSupport = {
  properties = {
    "documentation",
    "detail",
    "additionalTextEdits",
  },
}

require("lsp_signature").setup({
  bind = true,
  border = "single",
})
local completion_servers = {
  "rust_analyzer",
  "solargraph",
  "gopls",
  "pylsp",
}
for _, server in ipairs(completion_servers) do
  require("lspconfig")[server].setup {
    capabilities = require("cmp_nvim_lsp").update_capabilities(capabilities),
  }
end

require("lspconfig").sumneko_lua.setup {
  cmd = {
    "lua-language-server",
  },
  capabilities = require("cmp_nvim_lsp").update_capabilities(capabilities),
}
