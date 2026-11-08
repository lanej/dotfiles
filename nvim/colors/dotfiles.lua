-- SEE: Native groups and colors are generated from design-system/.
vim.cmd("highlight clear")
vim.o.background = "dark"
vim.o.termguicolors = true
vim.g.colors_name = "dotfiles"
require("dotfiles-theme").apply()
