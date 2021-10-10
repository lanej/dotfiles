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

local completion_servers = { "rust_analyzer", "solargraph", "gopls" }

for _, server in ipairs(completion_servers) do
  require("lspconfig")[server].setup {
    capabilities = require("cmp_nvim_lsp").update_capabilities(vim.lsp.protocol
                                                                 .make_client_capabilities()),
  }
end

require("lspconfig").sumneko_lua.setup {
  cmd = { "lua-language-server" },
  capabilities = require("cmp_nvim_lsp").update_capabilities(vim.lsp.protocol
                                                               .make_client_capabilities()),
}

require("nvim-autopairs.completion.cmp").setup({
  map_cr = true, --  map <CR> on insert mode
  map_complete = true, -- it will auto insert `(` (map_char) after select function or method item
  auto_select = true, -- automatically select the first item
  insert = false, -- use insert confirm behavior instead of replace
  map_char = { -- modifies the function or method delimiter by filetypes
    all = "(",
    tex = "{",
  },
})
