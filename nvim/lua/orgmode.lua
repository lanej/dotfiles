local parser_configs = require('nvim-treesitter.parsers').get_parser_configs()

parser_configs.norg_meta = {
  install_info = {
    url = "https://github.com/nvim-neorg/tree-sitter-norg-meta",
    files = {
      "src/parser.c",
    },
    branch = "main",
  },
}

parser_configs.norg_table = {
  install_info = {
    url = "https://github.com/nvim-neorg/tree-sitter-norg-table",
    files = {
      "src/parser.c",
    },
    branch = "main",
  },
}

require('neorg').setup {
  load = {
    ["core.defaults"] = {},
    ["core.norg.dirman"] = {
      config = {
        workspaces = {
          home = "~/share/notes/home",
        },
      },
    },
    ["core.norg.journal"] = {},
    ["core.norg.concealer"] = {},
    -- ["core.norg.completion"] = {},
  },
}

vim.api.nvim_set_keymap("n", "<leader>oc", "<cmd>Neorg gtd capture<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>oi", "<cmd>Neorg workspace home<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>oe", "<cmd>Neorg gtd edit<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>ov", "<cmd>Neorg gtd views<CR>", {
  noremap = true,
  silent = true,
})
