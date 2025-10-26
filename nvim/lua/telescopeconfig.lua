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
				["<Tab>"] = actions.toggle_selection + actions.move_selection_next,
				["<C-f>"] = actions.toggle_selection + actions.move_selection_next,
				-- ["<C-h>"] = actions.toggle_preview,
				["<C-j>"] = actions.move_selection_next,
				["<C-k>"] = actions.move_selection_previous,
				["<C-r>"] = layout.toggle_preview,
				["<C-i>"] = function(prompt_bufnr)
					local current_picker = require("telescope.actions.state").get_current_picker(prompt_bufnr)
					local no_ignore = current_picker.no_ignore_state or false

					-- Toggle no_ignore to include/exclude gitignored files
					actions.close(prompt_bufnr)
					builtin.find_files({
						no_ignore = not no_ignore,
						hidden = true,
						prompt_title = not no_ignore and "Find Files (all)" or "Find Files",
						attach_mappings = function(prompt_bufnr, map)
							local picker = require("telescope.actions.state").get_current_picker(prompt_bufnr)
							picker.no_ignore_state = not no_ignore
							return true
						end,
					})
				end,
			},
			n = {
				["<Tab>"] = actions.toggle_selection + actions.move_selection_next,
				["<C-f>"] = actions.toggle_selection + actions.move_selection_next,
				-- ["<C-h>"] = actions.toggle_preview,
				["<C-j>"] = actions.move_selection_next,
				["<C-k>"] = actions.move_selection_previous,
				["<C-r>"] = layout.toggle_preview,
				["<C-i>"] = function(prompt_bufnr)
					local current_picker = require("telescope.actions.state").get_current_picker(prompt_bufnr)
					local no_ignore = current_picker.no_ignore_state or false

					-- Toggle no_ignore to include/exclude gitignored files
					actions.close(prompt_bufnr)
					builtin.find_files({
						no_ignore = not no_ignore,
						hidden = true,
						prompt_title = not no_ignore and "Find Files (all)" or "Find Files",
						attach_mappings = function(prompt_bufnr, map)
							local picker = require("telescope.actions.state").get_current_picker(prompt_bufnr)
							picker.no_ignore_state = not no_ignore
							return true
						end,
					})
				end,
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
			prompt_title = "Branches (local & remote)",
			git_command = {
				"git",
				"for-each-ref",
				"--format=%(if)%(HEAD)%(then)* %(else)  %(end)%(refname:short) %(color:yellow)%(committerdate:relative)%(color:reset)",
				"--sort=-committerdate",
				"refs/heads/",
			},
			previewer = require("telescope.previewers").new_termopen_previewer({
				get_command = function(entry)
					local branch = entry.value:gsub("^%s*%*?%s*", ""):gsub("%s.*$", "")
					return {
						"sh",
						"-c",
						string.format(
							"git diff --stat=80 --stat-count=10 HEAD..%s 2>/dev/null | sort -k3 -nr || echo 'No differences'; echo '---'; git diff HEAD..%s 2>/dev/null || echo 'No differences'",
							branch,
							branch
						),
					}
				end,
			}),
			layout_strategy = "horizontal",
			layout_config = {
				width = 0.95,
				height = 0.9,
				preview_width = 0.65,
			},
		},
		git_commits = {
			previewer = require("telescope.previewers").git_commit_diff_as_was,
		},
		lsp_document_symbols = {
			layout_strategy = "vertical",
			layout_config = {
				width = 0.95,
				height = 0.9,
				preview_height = 0.4,
			},
			previewer = require("telescope.previewers").vim_buffer_vimgrep.new({}),
			fname_width = 30,
			symbol_width = 60,
			show_line = true,
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
vim.keymap.set("n", "<leader>cf", function()
	-- Get the base branch (usually main or master)
	local base_branch = vim.fn
		.system("git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'")
		:gsub("\n", "")
	if base_branch == "" then
		-- Fallback to common branch names if origin/HEAD is not set
		local branches = vim.fn.system("git branch -r"):gsub("\n", " ")
		if branches:match("origin/main") then
			base_branch = "main"
		elseif branches:match("origin/master") then
			base_branch = "master"
		else
			vim.notify("Could not determine base branch", vim.log.levels.ERROR)
			return
		end
	end

	-- Get the merge base
	local merge_base = vim.fn.system("git merge-base HEAD origin/" .. base_branch):gsub("\n", "")
	if merge_base == "" then
		vim.notify("Could not find merge base with origin/" .. base_branch, vim.log.levels.ERROR)
		return
	end

	-- Get changed files with their status (added/modified)
	local changed_files = vim.fn.systemlist("git diff --name-status --diff-filter=AM " .. merge_base)
	if #changed_files == 0 then
		vim.notify("No changed files found", vim.log.levels.INFO)
		return
	end

	-- Parse the git output to create entries similar to git_files
	local results = {}
	for _, line in ipairs(changed_files) do
		local status, file = line:match("^([AM])%s+(.+)$")
		if status and file then
			local status_text = status == "A" and "added" or "modified"
			local display = string.format("%-9s %s", status_text, file)
			table.insert(results, {
				value = file,
				display = display,
				ordinal = file,
				path = file,
			})
		end
	end

	-- Use telescope to display the files with git status
	require("telescope.pickers")
		.new({}, {
			prompt_title = "Changed Files (vs " .. base_branch .. ")",
			finder = require("telescope.finders").new_table({
				results = results,
				entry_maker = function(entry)
					return entry
				end,
			}),
			sorter = require("telescope.config").values.generic_sorter({}),
			previewer = require("telescope.previewers").vim_buffer_cat.new({}),
			attach_mappings = function(prompt_bufnr, map)
				actions.select_default:replace(function()
					actions.close(prompt_bufnr)
					local selection = require("telescope.actions.state").get_selected_entry()
					if selection then
						vim.cmd("edit " .. selection.path)
					end
				end)
				return true
			end,
		})
		:find()
end, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>fc", builtin.oldfiles, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bl", builtin.current_buffer_fuzzy_find, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bb", builtin.buffers, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bt", builtin.current_buffer_tags, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bc", builtin.git_bcommits, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>gf", builtin.git_files, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>gc", builtin.git_commits, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>bp", function()
	builtin.git_branches({
		prompt_title = "Git Branches (checkout)",
		attach_mappings = function(prompt_bufnr, map)
			actions.select_default:replace(function()
				actions.close(prompt_bufnr)
				local selection = require("telescope.actions.state").get_selected_entry()
				if selection then
					local branch = selection.value
					-- Handle remote branches by creating local tracking branch
					if branch:match("^origin/") and not branch:match("^origin/HEAD") then
						local local_branch = branch:gsub("^origin/", "")
						-- Check if local branch already exists
						local cmd = string.format("git show-ref --verify --quiet refs/heads/%s", local_branch)
						if vim.fn.system(cmd):match("") then
							-- Local branch exists, just checkout
							vim.cmd("Git checkout " .. local_branch)
						else
							-- Create and checkout tracking branch
							vim.cmd("Git checkout -b " .. local_branch .. " " .. branch)
						end
					else
						-- Local branch, just checkout
						local clean_branch = branch:gsub("^%s*%*?%s*", ""):gsub("%s.*$", "")
						vim.cmd("Git checkout " .. clean_branch)
					end
				end
			end)
			return true
		end,
	})
end, { noremap = true, silent = true })
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
vim.keymap.set("n", "<leader>bs", function()
	builtin.lsp_document_symbols({
		layout_strategy = "horizontal",
		layout_config = {
			width = 0.95,
			height = 0.9,
			preview_width = 0.5,
		},
		previewer = require("telescope.previewers").vim_buffer_cat.new({}),
		fname_width = 30,
		symbol_width = 60,
		show_line = true,
	})
end, { noremap = true, silent = true })
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

-- Find and replace workflow: search with telescope, send to quickfix, then replace
vim.keymap.set("n", "<leader>ar", function()
	builtin.live_grep({
		attach_mappings = function(_, map)
			-- Add easier keybinds for selection
			map("i", "<C-Space>", actions.toggle_selection + actions.move_selection_next)
			map("n", "<C-Space>", actions.toggle_selection + actions.move_selection_next)
			-- Send to quickfix
			map("i", "<C-q>", actions.send_selected_to_qflist + actions.open_qflist)
			map("n", "<C-q>", actions.send_selected_to_qflist + actions.open_qflist)
			map("i", "<M-q>", actions.send_to_qflist + actions.open_qflist)
			map("n", "<M-q>", actions.send_to_qflist + actions.open_qflist)
			return true
		end,
	})
	vim.defer_fn(function()
		vim.notify(
			"Select: CTRL-Space | Send selected: CTRL-Q | Send all: ALT-Q | Then: :cfdo %s/old/new/gc | update",
			vim.log.levels.INFO
		)
	end, 100)
end, { noremap = true, silent = true, desc = "Find and replace across project" })
