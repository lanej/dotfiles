require"nvim-treesitter.configs".setup({
  ensure_installed = "maintained",
  highlight = { enable = true },
  indent = { enable = true },
  textobjects = {
    select = {
      enable = true,
      lookahead = true,
      keymaps = {
        ["af"] = "@function.outer",
        ["if"] = "@function.inner",
        ["ac"] = "@class.outer",
        ["ic"] = "@class.inner",
        ["ab"] = "@block.outer",
        ["ib"] = "@block.inner",
        ["ap"] = "@parameter.outer",
        ["ip"] = "@parameter.inner",
        ["ai"] = "@conditional.outer",
        ["ii"] = "@conditional.inner",
        ["ax"] = "@call.outer",
        ["ix"] = "@call.inner",
        ["an"] = "@statement.outer",
      },
    },
    swap = {
      enable = true,
      swap_next = { ["<leader>a"] = "@parameter.inner" },
      swap_previous = { ["<leader>A"] = "@parameter.inner" },
    },
    move = {
      enable = true,
      set_jumps = true, -- whether to set jumps in the jumplist
      goto_next_start = { ["]f"] = "@function.outer", ["]]"] = "@class.outer", ["]b"] = "@block.outer" },
      goto_next_end = { ["]F"] = "@function.outer", ["]["] = "@class.outer", ["]B"] = "@block.outer"  },
      goto_previous_start = { ["[f"] = "@function.outer", ["[["] = "@class.outer", ["[b"] = "@block.outer" },
      goto_previous_end = { ["[F"] = "@function.outer", ["[]"] = "@class.outer", ["[B"] = "@block.outer" },
    },
  },
})

-- vnoremap as :lua require"treesitter-unit".select()<CR>
-- onoremap as :<c-u>lua require"treesitter-unit".select()<CR>
