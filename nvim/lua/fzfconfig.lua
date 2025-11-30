local fzf_lua = require("fzf-lua")
local actions = require("fzf-lua.actions")

local skim_present = vim.fn.executable("sk") == 1

require("fzf-lua").setup({
	-- NOTE: Forcing fzf instead of sk to avoid NVIM_LISTEN_ADDRESS issue (ibhagwan/fzf-lua#1812)
	fzf_bin = "fzf",
	files = {
		cmd = "fd --type f --follow --hidden --exclude .git",
		file_icons = true,
		color_icons = true,
	},
	defaults = {
		compat_warn = false,
	},
	keymap = {
		builtin = {
			["<C-f>"] = "toggle-fullscreen",
			["<C-h>"] = "toggle-preview",
			["<C-r>"] = "toggle-preview-cw",
			["<C-j>"] = "half-page-down",
			["<C-k>"] = "half-page-up",
		},
		fzf = {
			["ctrl-b"] = "toggle-all",
		},
	},
	winopts = {
		border = "single",
		preview = {
			layout = "flex", -- use flex layout to enable flipping
			flip_columns = 140, -- #cols to switch to horizontal on flex
			vertical = "down:45%", -- vertical preview when flipped (results top, preview bottom)
			horizontal = "right:50%", -- horizontal preview default (results left, preview right)
		},
	},
	grep = {
		-- Shorten paths in grep results to save horizontal space for match text
		-- Using 2 chars per directory as a compromise between readability and space
		-- e.g., ~/.co/nv/lua/file.lua instead of ~/.config/nvim/lua/file.lua
		path_shorten = 2, -- shorten to 2 chars per directory (more readable than 1)
		rg_glob = true, -- enable glob parsing
		winopts = {
			preview = {
				layout = "flex",
				flip_columns = 120, -- when terminal < 120 cols, flip to vertical
			},
		},
	},
	lsp = {
		code_actions = {
			-- prompt           = 'Code Actions> ',
			-- async_or_timeout = 5000,
			-- when git-delta is installed use "codeaction_native" for beautiful diffs
			-- try it out with `:FzfLua lsp_code_actions previewer=codeaction_native`
			-- scroll up to `previewers.codeaction{_native}` for more previewer options
			previewer = "codeaction_native",
		},
	},
	-- winopts = {
	--   height  = 0.85,             -- window height
	--   width   = 0.80,             -- window width
	--   row     = 0.35,             -- window row position (0=top, 1=bottom)
	--   col     = 0.50,             -- window col position (0=left, 1=right)
	--   preview = {
	--     vertical   = 'down:62%',  -- up|down:size
	--     horizontal = 'right:62%', -- right|left:size
	--   },
	-- },
	buffers = {
		sort_lastused = true,
		ignore_current_buffer = true,
	},
	git = {
		branches = {
			prompt = "Branches❯ ",
			cmd = "git for-each-ref --format='%(refname:short)' --sort=-committerdate refs/heads/ | grep -v 'phabricator'",
			preview = 'git diff --stat --summary --color -p "$(git merge-base --fork-point $(git symbolic-ref refs/remotes/origin/HEAD))"...{} | delta',
			actions = {
				["default"] = {
					actions.git_switch,
					function(_)
						vim.cmd("ProsessionReset")
					end,
				},
			},
		},
		status = {
			actions = {
				["right"] = false,
				["left"] = false,
				["ctrl-x"] = { fn = actions.git_reset, reload = true },
				["ctrl-s"] = { fn = actions.git_stage_unstage, reload = true },
			},
		},
		commits = {
			preview = "echo {} | awk '{ print $1 }' | xargs git show | delta",
			actions = {
				["default"] = actions.git_buf_edit,
				["ctrl-s"] = actions.git_buf_split,
				["ctrl-v"] = actions.git_buf_vsplit,
				["ctrl-t"] = actions.git_buf_tabedit,
				["ctrl-c"] = actions.git_checkout,
			},
		},
	},
})

-- Registers (paste register or apply macro)
local extract_register_from = function(result)
	-- `selected[1]` is going to be "[2] contents of register 2"
	return result:match("^%[(.)%]")
end

vim.keymap.set("n", "<leader>rp", function()
	fzf_lua.registers({
		actions = {
			["default"] = function(selected)
				local register = extract_register_from(selected[1])
				vim.cmd('normal "' .. register .. "p")
			end,
			["@"] = function(selected)
				local register = extract_register_from(selected[1])
				vim.cmd("normal @" .. register)
			end,
		},
	})
end, {
	desc = "fzf_lua.registers",
})

-- Keymap to search for the word under the cursor using fzf-lua
vim.keymap.set("n", "<leader>aw", function()
	require("fzf-lua").grep_cword()
end, { noremap = true, silent = true })

-- Keymap to search for a pattern using fzf-lua
vim.keymap.set("n", "<leader>ag", function()
	require("fzf-lua").live_grep_resume({ cwd = vim.fn.expand("%:p:h") })
end, { noremap = true, silent = true })

-- Keymap to list available commands using fzf-lua
vim.keymap.set({ "n", "v" }, "<leader>ac", function()
	require("fzf-lua").commands()
end, { noremap = true, silent = true })

-- Keymap to list built-in commands using fzf-lua
vim.keymap.set("n", "<leader>ab", function()
	require("fzf-lua").builtin()
end, { noremap = true, silent = true })

-- Keymap to list lines in the current buffer using fzf-lua
vim.keymap.set("n", "<leader>al", function()
	require("fzf-lua").lines()
end, { noremap = true, silent = true })

-- Keymap to resume live grep search using fzf-lua
vim.keymap.set("n", "<leader>az", function()
	require("fzf-lua").live_grep_resume()
end, { noremap = true, silent = true })

-- Keymap to search for a pattern using fzf-lua
vim.keymap.set("n", "<leader>aa", function()
	require("fzf-lua").grep()
end, { noremap = true, silent = true })

-- Keymap to list tags in the current buffer using fzf-lua
vim.keymap.set("n", "<leader>at", function()
	require("fzf-lua").tags()
end, { noremap = true, silent = true })

-- Keymap to list files using fzf-lua (press <C-g> in picker to toggle gitignore)
vim.keymap.set("n", "<leader>ff", function()
	local fzf = require("fzf-lua")
	local no_ignore = false

	local function run_files(query)
		fzf.files({
			cmd = no_ignore and "fd --type f --follow --hidden --no-ignore --exclude .git"
				or "fd --type f --follow --exclude .git",
			prompt = no_ignore and "All Files❯ " or "Files❯ ",
			query = query or "",
			actions = {
				["ctrl-g"] = function(selected, opts)
					no_ignore = not no_ignore
					local current_query = (opts and opts.last_query) or ""
					vim.schedule(function()
						run_files(current_query)
					end)
				end,
			},
		})
	end

	run_files()
end, { noremap = true, silent = true })

-- Keymap to list files in the current directory using fzf-lua
vim.keymap.set("n", "<leader>fr", function()
	require("fzf-lua").files({ cwd = vim.fn.expand("%:p:h") })
end, { noremap = true, silent = true })

-- Keymap to list command history using fzf-lua
vim.keymap.set("n", "<leader>rr", function()
	require("fzf-lua").command_history()
end, { noremap = true, silent = true })

-- Keymap to list recently opened files using fzf-lua
vim.keymap.set("n", "<leader>fc", function()
	require("fzf-lua").oldfiles()
end, { noremap = true, silent = true })

-- Keymap to list lines in the current buffer using fzf-lua
vim.keymap.set("n", "<leader>bl", function()
	require("fzf-lua").blines()
end, {
	noremap = true,
	silent = true,
})

-- Keymap to list tags in the current buffer using fzf-lua
vim.keymap.set("n", "<leader>bt", function()
	require("fzf-lua").btags()
end, { noremap = true, silent = true })

-- Keymap to list git commits for the current buffer using fzf-lua
vim.keymap.set("n", "<leader>bc", function()
	require("fzf-lua").git_bcommits()
end, { noremap = true, silent = true })

-- Keymap to list git files using fzf-lua
vim.keymap.set("n", "<leader>gf", function()
	require("fzf-lua").git_files()
end, { noremap = true, silent = true })

-- Keymap to list git status using fzf-lua
-- Start with cwd, <C-g> toggles to project root
vim.keymap.set("n", "<leader>sf", function()
	local fzf = require("fzf-lua")

	-- Use current working directory as default
	local cwd_dir = vim.fn.getcwd()

	-- Find git root
	local git_root_cmd = vim.fn.systemlist("git -C " .. vim.fn.shellescape(cwd_dir) .. " rev-parse --show-toplevel 2>/dev/null")
	local git_root = vim.v.shell_error == 0 and git_root_cmd[1] or cwd_dir

	-- Calculate relative path from git root for filtering
	local rel_dir_from_root = ""
	if git_root and cwd_dir:sub(1, #git_root) == git_root then
		rel_dir_from_root = cwd_dir:sub(#git_root + 2) -- +2 to skip the trailing slash
	end

	-- State to track current mode
	local is_project_root = false

	local function run_git_status(query)
		-- Calculate relative path for display
		local rel_path
		if is_project_root then
			rel_path = "root"
		else
			rel_path = vim.fn.fnamemodify(cwd_dir, ":~:.")
			if rel_path == "." then
				rel_path = vim.fn.fnamemodify(cwd_dir, ":t")
			end
		end

		-- Use git status with path filter instead of changing cwd
		local git_status_cmd
		if is_project_root or rel_dir_from_root == "" then
			git_status_cmd = nil -- Use default
		else
			git_status_cmd = "git -c color.status=false status --short -- " .. vim.fn.shellescape(rel_dir_from_root)
		end

		fzf.git_status({
			cmd = git_status_cmd,
			query = query or "",
			prompt = "GitStatus(" .. rel_path .. ")❯ ",
			file_icons = true,
			color_icons = true,
			actions = {
				["default"] = actions.file_edit,
				["ctrl-g"] = function(selected, opts)
					-- Toggle mode and preserve query
					is_project_root = not is_project_root

					-- Preserve current query
					local current_query = (opts and opts.last_query) or ""

					vim.schedule(function()
						run_git_status(current_query)
					end)
				end,
			},
		})
	end

	run_git_status()
end, { noremap = true, silent = true })

-- Keymap to list quickfix items using fzf-lua
vim.keymap.set("n", "<leader>qf", function()
	require("fzf-lua").quickfix()
end, { noremap = true, silent = true })

-- Keymap to list buffers using fzf-lua
vim.keymap.set("n", "<leader>bb", function()
	require("fzf-lua").buffers()
end, { noremap = true, silent = true })

-- Keymap to list git commits using fzf-lua
vim.keymap.set("n", "<leader>gc", function()
	require("fzf-lua").git_commits()
end, { noremap = true, silent = true })

-- Keymap to list git branches using fzf-lua
vim.keymap.set("n", "<leader>bp", function()
	require("fzf-lua").git_branches()
end, { noremap = true, silent = true })

-- Keymap to list document symbols using fzf-lua
vim.keymap.set("n", "<leader>bs", function()
	require("fzf-lua").lsp_document_symbols({
		winopts = {
			relative = "cursor", -- or 'cursor' for positioning relative to the cursor
			width = 0.5, -- width of the window (50% of the editor)
			height = 0.8, -- height of the window (30% of the editor)
			border = "double", -- border style (e.g., 'none', 'single', 'double', 'rounded')
		},
	})
end, { noremap = true, silent = true })

-- Keymap to list incoming calls using fzf-lua
vim.keymap.set("n", "<leader>cj", function()
	require("fzf-lua").lsp_incoming_calls()
end, { noremap = true, silent = true })

-- Keymap to list typedefs
vim.keymap.set("n", "<leader>ct", function()
	require("fzf-lua").lsp_typedefs()
end, { noremap = true, silent = true })

-- Keymap to list outgoing calls using fzf-lua
vim.keymap.set("n", "<leader>ck", function()
	require("fzf-lua").lsp_outgoing_calls()
end, { noremap = true, silent = true })

vim.keymap.set({ "n", "v" }, "<leader>cr", function()
	require("fzf-lua").lsp_references()
end, {
	noremap = true,
	silent = true,
})

vim.keymap.set({ "n", "v" }, "<leader>cd", function()
	require("fzf-lua").lsp_definitions({ jump1 = true })
end, {
	noremap = true,
	silent = true,
})

-- Keymap to list implementation calls using fzf-lua
vim.keymap.set("n", "<leader>cy", function()
	require("fzf-lua").lsp_implementations()
end, { noremap = true, silent = true })

-- Keymap to list workspace symbols using fzf-lua
vim.keymap.set("n", "<leader>ws", function()
	require("fzf-lua").lsp_live_workspace_symbols({})
end, { noremap = true, silent = true })

vim.keymap.set("n", "<leader>wd", function()
	-- prefer a larger preview window and horizontal split
	require("fzf-lua").diagnostics_workspace({
		winopts = { preview = { vertical = "up:68%", layout = "vertical:68%" } },
	})
end, { noremap = true, silent = true })

vim.keymap.set("n", "<leader>bd", function()
	-- prefer a larger preview window and horizontal split
	require("fzf-lua").diagnostics_document({
		winopts = { preview = { vertical = "up:68%", layout = "vertical:68%" } },
	})
end, { noremap = true, silent = true })

vim.keymap.set("n", "<leader>ss", function()
	require("fzf-lua").spell_suggest()
end, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>jj", function()
	require("fzf-lua").jumps()
end, { noremap = true, silent = true })
vim.keymap.set("n", "<leader>ah", function()
	require("fzf-lua").help_tags()
end, {
	noremap = true,
	silent = true,
})

vim.keymap.set({ "n", "v" }, "<leader>ca", function()
	local columns = vim.o.columns
	local winopts

	if columns >= 120 then
		-- Wide screen: use larger centered window with preview
		winopts = {
			relative = "editor",
			width = 0.6,
			height = 0.5,
			border = "double",
			preview = {
				layout = "flex",
				flip_columns = 100,
				vertical = "down:50%",
				horizontal = "right:50%",
			},
		}
	else
		-- Narrow screen: use compact cursor-relative window
		winopts = {
			relative = "cursor",
			width = 0.5,
			height = 0.3,
			border = "double",
		}
	end

	require("fzf-lua").lsp_code_actions({
		pager = false,
		winopts = winopts,
	})
end, {
	noremap = true,
	silent = true,
})

vim.keymap.set({ "n" }, "<leader>dc", function()
	require("fzf-lua").fzf_exec({
		prompt = "Diff Comments> ",
		previewer = false,
		-- preview = require 'fzf-lua'.shell.raw_preview_action_cmd(function(items) return vim.inspect(items) end),
		fn_transform = function(x)
			return require("fzf-lua").make_entry.file(x, { file_icons = true, color_icons = true })
		end,
	}, function(callback)
		local comments = require("phab").get_comments()
		print(vim.inspect(comments))

		for _, comment in ipairs(comments) do
			callback(comment.author .. ": " .. comment.comment)
		end

		callback()
	end)
end, { noremap = true, silent = true })

-- Keymap to list changed files (diff from merge-base, including untracked, staged, and unstaged)
vim.keymap.set({ "n" }, "<leader>cf", function()
	-- Get git root to ensure we're in a git repo
	local git_root = vim.fn.systemlist('git rev-parse --show-toplevel 2>/dev/null')[1]
	if vim.v.shell_error ~= 0 or not git_root or git_root == '' then
		vim.notify('Not in a git repository', vim.log.levels.ERROR)
		return
	end

	-- Try to get origin HEAD, fall back to origin/master or origin/main
	local origin_head = vim.fn.systemlist('git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null')[1]
	local default_branch
	local merge_base

	if origin_head and origin_head ~= '' then
		default_branch = origin_head:match('refs/remotes/(.*)')
	else
		-- Fallback: check if origin/main or origin/master exists
		local has_main = vim.fn.systemlist('git rev-parse --verify origin/main 2>/dev/null')[1]
		local has_master = vim.fn.systemlist('git rev-parse --verify origin/master 2>/dev/null')[1]

		if vim.v.shell_error == 0 and has_main and has_main ~= '' then
			default_branch = 'origin/main'
		elseif has_master and has_master ~= '' then
			default_branch = 'origin/master'
		end
	end

	-- Try to get merge-base if we found a default branch
	if default_branch then
		merge_base = vim.fn.systemlist(string.format('git merge-base HEAD %s 2>/dev/null', default_branch))[1]
		if vim.v.shell_error ~= 0 or not merge_base or merge_base == '' then
			merge_base = nil -- Clear it if merge-base failed
		end
	end

	-- Build command based on whether we have a merge-base
	local cmd
	if merge_base then
		-- We have a merge-base: show all changes from fork point
		cmd = string.format(
			"bash -c '( git diff --name-only %s HEAD 2>/dev/null; git diff --name-only --cached 2>/dev/null; git diff --name-only 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null ) | sort -u'",
			merge_base
		)
	else
		-- No merge-base: just show staged + unstaged + untracked
		cmd = "bash -c '( git diff --name-only --cached 2>/dev/null; git diff --name-only 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null ) | sort -u'"
	end

	-- Execute command to get file list
	local files = vim.fn.systemlist(cmd)
	if vim.v.shell_error ~= 0 then
		vim.notify(string.format('Command failed with error %d: %s', vim.v.shell_error, table.concat(files, '\n')), vim.log.levels.ERROR)
		return
	end
	if #files == 0 then
		vim.notify('No changed files found', vim.log.levels.INFO)
		return
	end

	-- Use fzf_exec with git_status() to get proper git icons
	require("fzf-lua").fzf_exec(
		function(fzf_cb)
			-- Get git status for icons
			local git_status_output = vim.fn.systemlist('git status --porcelain')
			local status_map = {}
			for _, line in ipairs(git_status_output) do
				local status = line:sub(1, 2)
				local file = line:sub(4)
				status_map[file] = status
			end

			-- Format each file with make_entry
			for _, file in ipairs(files) do
				local entry = require("fzf-lua").make_entry.file(file, { file_icons = true, color_icons = true })
				fzf_cb(entry)
			end
			fzf_cb()
		end,
		{
			prompt = "ChangedFiles❯ ",
			previewer = "builtin",
			winopts = {
				preview = {
					layout = "flex",
					flip_columns = 120,
					vertical = "down:60%",
					horizontal = "right:60%",
				},
			},
			actions = {
				["default"] = function(selected, opts)
					if not selected or #selected == 0 then
						return
					end

					-- Use fzf-lua's path extraction to get the actual file path
					local file = require("fzf-lua").path.entry_to_file(selected[1], opts).path

					vim.cmd("edit " .. vim.fn.fnameescape(file))

					-- Get the first changed line from git diff
					local diff_base = merge_base or "HEAD"
					local diff_cmd = string.format("git diff %s --unified=0 -- %s | grep -E '^@@' | head -1", diff_base, vim.fn.shellescape(file))
					local hunk_header = vim.fn.system(diff_cmd)

					if vim.v.shell_error == 0 and hunk_header ~= "" then
						local new_start = hunk_header:match("%+(%d+)")
						if new_start then
							vim.cmd("normal! " .. new_start .. "G")
							vim.cmd("normal! zz")
						end
					end
				end,
			},
		}
	)
end, {
	noremap = true,
	silent = true,
})

-- Git status files relative to current buffer directory
vim.keymap.set({ "n" }, "<leader>sr", function()
	local current_dir = vim.fn.expand("%:p:h")
	local git_root = vim.fn.systemlist("git -C " .. current_dir .. " rev-parse --show-toplevel")[1]

	if not git_root or git_root == "" then
		vim.notify("Not in a git repository", vim.log.levels.ERROR)
		return
	end

	-- Get relative path from git root to current directory
	local relative_path = current_dir:gsub("^" .. vim.pesc(git_root) .. "/", "")
	if relative_path == current_dir then
		-- We're at git root
		relative_path = "."
	end

	-- Get changed and staged files in current directory
	local search_path = relative_path == "." and "" or (relative_path .. "/")

	-- Build command to get modified, staged, and untracked files
	-- Use git -C instead of cd to avoid shell escaping issues
	local cmd = string.format(
		"(git -C %s ls-files -m -- %s; git -C %s diff --name-only --cached -- %s; git -C %s ls-files -o --exclude-standard -- %s) | sort -u",
		vim.fn.shellescape(git_root),
		vim.fn.shellescape(search_path),
		vim.fn.shellescape(git_root),
		vim.fn.shellescape(search_path),
		vim.fn.shellescape(git_root),
		vim.fn.shellescape(search_path)
	)

	require("fzf-lua").files({
		cmd = cmd,
		prompt = "Git Status (Current Dir: " .. relative_path .. ")❯ ",
		actions = require("fzf-lua").defaults.actions.files,
		preview = "git diff HEAD {} 2>/dev/null | delta || cat {}",
	})
end, {
	noremap = true,
	silent = true,
	desc = "Git status relative to current directory",
})
