std = "luajit"
-- StyLua owns line wrapping, including generated tables with their own layout.
max_line_length = false
self = false

files["nvim/**/*.lua"] = { globals = { "vim" } }
files["scripts/bootstrap-nvim.lua"] = { globals = { "vim" } }
files["wezterm.lua"] = { std = "lua54" }
