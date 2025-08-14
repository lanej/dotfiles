local telescope = require("telescope")
local actions = require("telescope.actions")
local layout = require("telescope.actions.layout")
local builtin = require("telescope.builtin")

telescope.load_extension("fzf")

telescope.setup({
	defaults = {
		vimgrep_arguments = {
			"rg",
			"--color=never",
			"--no-heading",
			"--with-filename",
			"--line-number",
			"--column",
			"--smart-case",
			"--hidden",
			"--follow",
			"--glob",
			"!.git/",
		},
		prompt_prefix = " ",
		selection_caret = " ",
		entry_prefix = "  ",
		initial_mode = "insert",
		selection_strategy = "reset",
		sorting_strategy = "ascending",
		layout_strategy = "horizontal",
		layout_config = {
			prompt_position = "top",
			-- horizontal = { preview_width = 0.6 },
			-- vertical = { width = 0.8, height = 0.9, preview_height = 0.5 },
			-- width = 0.8,
			-- height = 0.85,
			preview_cutoff = 160,
		},
		theme = "nord",
		border = true,
		borderchars = { "─", "│", "─", "│", "╭", "╮", "╯", "╰" },
		color_devicons = true,
		mappings = {
			i = {
				["<C-f>"] = actions.toggle_selection + actions.move_selection_next,
				-- ["<C-h>"] = actions.toggle_preview,
				["<C-j>"] = actions.move_selection_next,
				["<C-k>"] = actions.move_selection_previous,
				["<C-r>"] = layout.toggle_preview,
			},
			n = {
				["<C-f>"] = actions.toggle_selection + actions.move_selection_next,
				-- ["<C-h>"] = actions.toggle_preview,
				["<C-j>"] = actions.move_selection_next,
				["<C-k>"] = actions.move_selection_previous,
				["<C-r>"] = layout.toggle_preview,
			},
		},
	},
	pickers = {
		find_files = {
			find_command = { "fd", "--type", "f", "--hidden", "--follow", "--exclude", ".git" },
		},
		buffers = {
			sort_lastused = true,
			ignore_current_buffer = true,
		},
		git_branches = {
			prompt_title = "Branches❯ ",
			git_command = { "git", "for-each-ref", "--format=%(refname:short)", "--sort=-committerdate", "refs/heads/" },
			previewer = require("telescope.previewers").git_branch_log,
		},
		git_commits = {
			previewer = require("telescope.previewers").git_commit_diff_as_was,
		},
	},
	extensions = {
		fzf = {
			fuzzy = true,
			override_generic_sorter = true,
			override_file_sorter = true,
			case_mode = "smart_case",
		},
	},
})

vim.keymap.set("n", "<leader>ff", builtin.find_files, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>fr", function()
	builtin.find_files({ cwd = vim.fn.expand("%:p:h"), no_ignore = true, hidden = true })
end, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>fc", builtin.oldfiles, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bl", builtin.current_buffer_fuzzy_find, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bb", builtin.buffers, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bt", builtin.current_buffer_tags, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bc", builtin.git_bcommits, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>gf", builtin.git_files, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>gc", builtin.git_commits, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bp", builtin.git_branches, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>sf", builtin.git_status, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>qf", builtin.quickfix, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>rr", builtin.command_history, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>aw", builtin.grep_string, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>ag", function()
	builtin.live_grep({ cwd = vim.fn.expand("%:p:h") })
end, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>az", builtin.live_grep, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>aa", builtin.grep_string, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>ac", builtin.commands, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>ab", builtin.builtin, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>al", builtin.current_buffer_fuzzy_find, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>at", builtin.tags, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bs", builtin.lsp_document_symbols, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>cj", builtin.lsp_incoming_calls, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>ct", builtin.lsp_type_definitions, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>ck", builtin.lsp_outgoing_calls, { noremap = true, silent = true })
vim.keymap.set({ "n", "v" }, "<leader>cr", builtin.lsp_references, { noremap = true, silent = true })
vim.keymap.set({ "n", "v" }, "<leader>cd", builtin.lsp_definitions, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>cy", builtin.lsp_implementations, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>ws", builtin.lsp_workspace_symbols, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>wd", builtin.diagnostics, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bd", builtin.diagnostics, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>ss", builtin.spell_suggest, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>jj", builtin.jumplist, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>ah", builtin.help_tags, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>ca", "<cmd>lua vim.lsp.buf.code_action()<CR>", { noremap = true, silent = true })
