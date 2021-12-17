require"fzf-lua".setup {
  keymap = {
    builtin = {
      ["<C-f>"] = "toggle-fullscreen",
      ["<C-h>"] = "toggle-preview",
      ["<C-r>"] = "toggle-preview-cw",
      ["<C-j>"] = "preview-page-down",
      ["<C-k>"] = "preview-page-up",
      ["<C-u>"] = "preview-page-reset",
    },
  },
}

vim.api.nvim_set_keymap("n", "<leader>aw", "<cmd>lua require(\"fzf-lua\").grep_cword()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>ag", "<cmd>lua require(\"fzf-lua\").grep()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>ac", "<cmd>lua require(\"fzf-lua\").commands()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>al", "<cmd>lua require(\"fzf-lua\").lines()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>az", "<cmd>lua require(\"fzf-lua\").live_grep_resume()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>aa", "<cmd>lua require(\"fzf-lua\").grep()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>at", "<cmd>lua require(\"fzf-lua\").tags()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>f", "<cmd>lua require(\"fzf-lua\").files()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>af",
                        "<cmd>lua require(\"fzf-lua\").files({ cwd = vim.fn.getcwd() })<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>rr", "<cmd>lua require(\"fzf-lua\").command_history()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>bl", "<cmd>lua require(\"fzf-lua\").grep_curbuf()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>bt", "<cmd>lua require(\"fzf-lua\").btags()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>bc", "<cmd>lua require(\"fzf-lua\").git_bcommits()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>gf", "<cmd>lua require(\"fzf-lua\").git_files()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>gf", "<cmd>lua require(\"fzf-lua\").files()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>of", "<cmd>lua require(\"fzf-lua\").oldfiles()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>bb", "<cmd>lua require(\"fzf-lua\").buffers()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>gc", "<cmd>lua require(\"fzf-lua\").git_commits()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>bp", "<cmd>lua require(\"fzf-lua\").git_branches()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>bs",
                        "<cmd>lua require(\"fzf-lua\").lsp_document_symbols()<CR>", {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap("n", "<leader>as",
                        "<cmd>lua require(\"fzf-lua\").lsp_workspace_symbols()<CR>", {
  noremap = true,
  silent = true,
})
