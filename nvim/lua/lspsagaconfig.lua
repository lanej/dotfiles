require("lspsaga").setup({
	diagnostic = {
		show_code_action = false,
	},
	symbol_in_winbar = {
		enable = true,
		separator = " ",
		ignore_patterns = {},
		hide_keyword = true,
		show_file = true,
		folder_level = 3,
		respect_root = true,
		color_mode = true,
	},
	code_action_lightbulb = {
		enable = false,
	},
	lightbulb = {
		enable = false,
	},
})
