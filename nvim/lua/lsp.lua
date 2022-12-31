local cmp = require 'cmp'

local feedkey = function(key, mode)
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes(key, true, true, true), mode, true)
end

cmp.setup({
  snippet = {
    expand = function(args)
      vim.fn["vsnip#anonymous"](args.body) -- For `vsnip` users.
    end,
  },
  window = {
    -- completion = cmp.config.window.bordered(),
    -- documentation = cmp.config.window.bordered(),
  },
  formatting = {
    format = function(entry, vim_item)
      if vim.tbl_contains({ 'path' }, entry.source.name) then
        local icon, hl_group = require('nvim-web-devicons').get_icon(entry:get_completion_item().label)
        if icon then
          vim_item.kind = icon
          vim_item.kind_hl_group = hl_group
          return vim_item
        end
      end
      return require("lspkind").cmp_format({ with_text = true })(entry, vim_item)
    end
  },
  mapping = cmp.mapping.preset.insert({
    ["<Tab>"] = cmp.mapping(function()
      if vim.fn["vsnip#available"](1) == 1 then
        feedkey("<Plug>(vsnip-expand-or-jump)", "")
      end
    end, { "i", "s" }),
    ["<S-Tab>"] = cmp.mapping(function()
      if vim.fn["vsnip#jumpable"](-1) == 1 then
        feedkey("<Plug>(vsnip-jump-prev)", "")
      end
    end, { "i", "s" }),
    ['<C-k>'] = cmp.mapping.scroll_docs(-4),
    ['<C-j>'] = cmp.mapping.scroll_docs(4),
    ['<C-Space>'] = cmp.mapping.complete(),
    ['<C-e>'] = cmp.mapping.abort(),

    ['<CR>'] = function(fallback)
      if cmp.visible() then
        cmp.confirm({ select = true }) -- Accept currently selected item. Set `select` to `false` to only confirm explicitly selected items.
      else
        fallback() -- If you use vim-endwise, this fallback will behave the same as vim-endwise.
      end
    end
  }),
  sources = cmp.config.sources({
    { name = 'nvim_lsp' },
    { name = 'vsnip' }, -- For vsnip users.
  }, {
    { name = 'buffer' },
  })
})

-- Set configuration for specific filetype.
cmp.setup.filetype('gitcommit', {
  sources = cmp.config.sources({
    { name = 'cmp_git' }, -- You can specify the `cmp_git` source if you were installed it.
  }, {
    { name = 'buffer' },
  })
})

-- Use buffer source for `/` and `?` (if you enabled `native_menu`, this won't work anymore).
cmp.setup.cmdline({ '/', '?' }, {
  mapping = cmp.mapping.preset.cmdline(),
  sources = {
    { name = 'buffer' }
  }
})

-- Use cmdline & path source for ':' (if you enabled `native_menu`, this won't work anymore).
cmp.setup.cmdline(':', {
  mapping = cmp.mapping.preset.cmdline(),
  sources = cmp.config.sources({
    { name = 'path' }
  }, {
    { name = 'cmdline' }
  })
})

local capabilities = require('cmp_nvim_lsp').default_capabilities()
local completion_servers = {
  "solargraph",
  "gopls",
  "pylsp",
}
for _, server in ipairs(completion_servers) do
  require("lspconfig")[server].setup {
    capabilities = capabilities,
  }
end

require("lspconfig").sumneko_lua.setup {
  cmd = {
    "lua-language-server",
  },
  settings = {
    Lua = {
      diagnostics = {
        globals = { "vim", "describe", "it" },
      },
    },
  },
  capabilities = capabilities,
}

local lsp_attach = function(client, buf)
  vim.api.nvim_buf_set_option(buf, "formatexpr", "v:lua.vim.lsp.formatexpr()")
  vim.api.nvim_buf_set_option(buf, "omnifunc", "v:lua.vim.lsp.omnifunc")
  vim.api.nvim_buf_set_option(buf, "tagfunc", "v:lua.vim.lsp.tagfunc")
end

-- Setup rust_analyzer via rust-tools.nvim
require("rust-tools").setup({
  tools = {
    inlay_hints = {
      highlight = "InlayHint",
    },
  },
  server = {
    capabilities = capabilities,
    on_attach = lsp_attach,
    settings = {
      ["rust-analyzer"] = {
        lens = {
          enable = true,
        },
        checkonsave = {
          command = "clippy",
        },
      },
    },
  },
})

vim.api.nvim_set_keymap("n", "K", "<cmd>lua vim.lsp.buf.hover()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>cd", "<cmd>lua vim.lsp.buf.definition()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>df", "<cmd>lua vim.lsp.buf.format()<CR>", {
  noremap = true,
  silent = false,
})
vim.api.nvim_set_keymap("n", "<c-p>", "<cmd>lua vim.diagnostic.goto_prev()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<c-n>", "<cmd>lua vim.diagnostic.goto_next()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<space>c", "<cmd>lua vim.diagnostic.set_loclist()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "g?", "<cmd>lua vim.diagnostic.show_line_diagnostics()<CR>", {
  noremap = true,
  silent = true,
})
