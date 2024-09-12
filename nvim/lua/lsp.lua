local cmp = require 'cmp'

local feedkey = function(key, mode)
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes(key, true, true, true), mode, true)
end

cmp.setup({
  preselect = cmp.PreselectMode.None,
  enabled = function() return vim.api.nvim_get_mode().mode ~= 'c' end,
  completion = {
    keyword_length = 3,
  },
  snippet = {
    expand = function(args)
      vim.fn["vsnip#anonymous"](args.body) -- For `vsnip` users.
      -- vim.snippet.expand(args.body) -- For native neovim snippets (Neovim v0.10+)
    end,
  },
  window = {
    completion = cmp.config.window.bordered(),
    documentation = cmp.config.window.bordered(),
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
    ["<Tab>"] = cmp.mapping(function(fallback)
      if vim.fn["vsnip#available"](1) == 1 then
        feedkey("<Plug>(vsnip-expand-or-jump)", "")
      else
        fallback()
      end
    end, { "i", "s" }),
    ["<S-Tab>"] = cmp.mapping(function(fallback)
      if vim.fn["vsnip#jumpable"](-1) == 1 then
        feedkey("<Plug>(vsnip-jump-prev)", "")
      else
        fallback()
      end
    end, { "i", "s" }),
    ['<C-k>'] = cmp.mapping.scroll_docs(-4),
    ['<C-j>'] = cmp.mapping.scroll_docs(4),
    ['<C-Space>'] = cmp.mapping.complete(),
    ['<C-e>'] = cmp.mapping.abort(),
    ['<CR>'] = cmp.mapping.confirm({ select = false }),
  }),
  sources = cmp.config.sources(
    {
      {
        name = 'nvim_lsp',
        option = {
          markdown_oxide = {
            keyword_pattern = [[\(\k\| \|\/\|#\)\+]]
          }
        }
      },
      { name = 'vsnip' },
      { name = 'tmux' },
      { name = 'path' },
      { name = 'emoji' },
      { name = "natdat" },
      {
        name = 'buffer',
        option = {
          get_bufnrs = function()
            local bufs = {}
            for _, win in ipairs(vim.api.nvim_list_wins()) do
              bufs[vim.api.nvim_win_get_buf(win)] = true
            end
            return vim.tbl_keys(bufs)
          end
        }
      }
    }
  )
})

require("CopilotChat.integrations.cmp").setup()

-- -- setup Markdown Oxide daily note commands
-- if client.name == "markdown_oxide" then
--   vim.api.nvim_create_user_command(
--     "Daily",
--     function(args)
--       local input = args.args
--
--       vim.lsp.buf.execute_command({ command = "jump", arguments = { input } })
--     end,
--     { desc = 'Open daily note', nargs = "*" }
--   )
-- end

-- Set configuration for specific filetype.
cmp.setup.filetype('gitcommit', {
  sources = cmp.config.sources(
    {
      { name = 'git' }, -- You can specify the `cmp_git` source if you were installed it.
      { name = 'tmux' },
      { name = 'buffer' },
    })
})

cmp.setup.filetype('copilot-*', {
  sources = cmp.config.sources(
    {
      { name = 'nvim_lsp' },
      { name = 'git' },
      { name = 'buffer' },
      { name = 'path' },
      { name = 'tmux' },
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
  sources = cmp.config.sources(
    {
      { name = 'cmdline' },
      { name = 'path' },
    })
})

local capabilities = require('cmp_nvim_lsp').default_capabilities()

local completion_servers = {
  "solargraph",
  "gopls",
  "pylsp",
  "tsserver",
  "html",
  "marksman",
}
for _, server in ipairs(completion_servers) do
  require("lspconfig")[server].setup {
    capabilities = capabilities,
    on_attach = function(client)
      client.server_capabilities.semanticTokensProvider = nil
    end
  }
end

require("lspconfig").terraformls.setup {
  capabilities = capabilities,
}

vim.api.nvim_create_autocmd({ "BufWritePre" }, {
  pattern = { "*.tf", "*.tfvars" },
  callback = function() vim.lsp.buf.format() end,
})

require("lspconfig").html.setup {
  capabilities = capabilities,
  init_options = { provideFormatter = true },
}

-- An example nvim-lspconfig capabilities setting
local markdown_oxide_capabilities = require("cmp_nvim_lsp").default_capabilities(vim.lsp.protocol
  .make_client_capabilities())

-- Ensure that dynamicRegistration is enabled! This allows the LS to take into account actions like the
-- Create Unresolved File code action, resolving completions for unindexed code blocks, ...
markdown_oxide_capabilities.workspace = {
  didChangeWatchedFiles = {
    dynamicRegistration = true,
  },
}

require("lspconfig").markdown_oxide.setup({
  capabilities = markdown_oxide_capabilities, -- again, ensure that capabilities.workspace.didChangeWatchedFiles.dynamicRegistration = true
  -- on_attach = on_attach                       -- configure your on attach config
})

require("lspconfig").lua_ls.setup {
  cmd = {
    "lua-language-server",
  },
  capabilities = capabilities,
  -- on_attach = function(client) client.server_capabilities.semanticTokensProvider = nil end,
  format = {
    enable = true,
    defaultConfig = {
      column_limit = "120",
      indent_width = "2",
      use_tab = "false",
      tab_width = "2",
      continuation_indent_width = "2",
      spaces_before_call = "1",
      keep_simple_control_block_one_line = "true",
      keep_simple_function_one_line = "true",
      keep_control_block_one_line = "true",
      align_args = "true",
      break_after_functioncall_lp = "false",
      break_before_functioncall_rp = "false",
      spaces_inside_functioncall_parens = "false",
      spaces_inside_functiondef_parens = "false",
      align_parameter = "true",
      chop_down_parameter = "true",
      break_after_functiondef_lp = "false",
      break_before_functiondef_rp = "false",
      align_table_field = "false",
      break_after_table_lb = "false",
      break_before_table_rb = "false",
      chop_down_table = "true",
      chop_down_kv_table = "true",
      table_sep = "",
      extra_sep_at_table_end = "true",
      spaces_inside_table_braces = "false",
      break_after_operator = "true",
      double_quote_to_single_quote = "true",
      single_quote_to_double_quote = "false",
      spaces_around_equals_in_field = "true",
      line_breaks_after_function_body = "1",
      line_separator = "input",
    }
  }
}

local lsp_attach = function(_, buf)
  vim.api.nvim_buf_set_option(buf, "formatexpr", "v:lua.vim.lsp.formatexpr()")
  vim.api.nvim_buf_set_option(buf, "omnifunc", "v:lua.vim.lsp.omnifunc")
  vim.api.nvim_buf_set_option(buf, "tagfunc", "v:lua.vim.lsp.tagfunc")
end

-- Setup rust_analyzer via rust-tools.nvim
require("rust-tools").setup({
  --[[ tools = {
    inlay_hints = {
      highlight = "InlayHint",
    },
  }, ]]
  server = {
    capabilities = capabilities,
    on_attach = lsp_attach,
    settings = {
      ["rust-analyzer"] = {
        checkOnSave = {
          command = "clippy",
          extraArgs = { "--all", "--", "-W", "clippy::all" },
        },
        procMacro = {
          enable = false,
        },
        diagnostics = { disabled = { "unresolved-proc-macro" } }
      },
    },
  },
})

cmp.mapping(function()
  if cmp.get_active_entry() then
    cmp.confirm()
  else
    require 'ultimate-autopair.maps.cr'.cmpnewline()
  end
end)

vim.api.nvim_set_keymap("n", "K", "<cmd>lua vim.lsp.buf.hover()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>cd", "<cmd>lua vim.lsp.buf.definition()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>cr", "<cmd>lua vim.lsp.buf.references()<CR>", {
  noremap = false,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>df", "<cmd>lua vim.lsp.buf.format()<CR>", {
  noremap = false,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<c-p>", "<cmd>lua vim.diagnostic.goto_prev()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<c-n>", "<cmd>lua vim.diagnostic.goto_next()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<space>c", "<cmd>lua vim.lsp.diagnostic.set_loclist()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "g?", "<cmd>lua vim.lsp.diagnostic.get_line_diagnostics()<CR>", {
  noremap = true,
  silent = true,
})

vim.keymap.set('n', '<space>wa', vim.lsp.buf.add_workspace_folder, { noremap = true, silent = true })
vim.keymap.set('n', '<space>wr', vim.lsp.buf.remove_workspace_folder, { noremap = true, silent = true })
vim.keymap.set('n', '<space>wl', function()
  print(vim.inspect(vim.lsp.buf.list_workspace_folders()))
end, { noremap = true, silent = true })

require("cmp_git").setup()
