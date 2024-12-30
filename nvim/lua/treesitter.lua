require("nvim-treesitter.configs").setup({
	ensure_installed = { "lua", "bash", "rust", "python", "ruby", "json", "yaml", "toml" },
	auto_install = true,
	highlight = { enable = true },
	indent = { enable = true },
	rainbow = {
		enable = true,
		disable = {
			"lua",
		}, -- list of languages you want to disable the plugin for
		extended_mode = false, -- Also highlight non-bracket delimiters like html tags, boolean or table: lang -> boolean
		max_file_lines = nil, -- Do not enable for files with more than n lines, int
		colors = {
			"#555555",
			"#777777",
			"#999999",
			"#bbbbbb",
			"#cccccc",
		}, -- table of hex strings
		-- termcolors = {} -- table of colour name strings
	},
	textobjects = {
		select = {
			enable = true,
			lookahead = true,
			keymaps = {
				["am"] = "@function.outer",
				["im"] = "@function.inner",
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
			swap_next = {
				["<leader>a"] = "@parameter.inner",
				["<leader>m"] = "@function.outer",
			},
			swap_previous = {
				["<leader>A"] = "@parameter.inner",
				["<leader>M"] = "@function.outer",
			},
		},
		move = {
			enable = true,
			set_jumps = true, -- whether to set jumps in the jumplist
			goto_next_start = {
				["]m"] = "@function.outer",
				["]]"] = "@class.outer",
				["]b"] = "@block.outer",
			},
			goto_next_end = {
				["]M"] = "@function.outer",
				["]["] = "@class.outer",
				["]B"] = "@block.outer",
			},
			goto_previous_start = {
				["[m"] = "@function.outer",
				["[["] = "@class.outer",
				["[b"] = "@block.outer",
			},
			goto_previous_end = {
				["[M"] = "@function.outer",
				["[]"] = "@class.outer",
				["[B"] = "@block.outer",
			},
		},
	},
})
