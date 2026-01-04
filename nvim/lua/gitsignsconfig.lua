require("gitsigns").setup({
	signs = {
		topdelete = {
			text = "^",
		},
	},
	-- Enable inline diff highlighting by default (word-level only)
	word_diff = true, -- Show word-level diffs by default (toggle with <leader>hd)
	diff_opts = {
		internal = true, -- Use internal diff library for better performance
	},
	-- Automatically set base to origin/HEAD (main/master) on BufEnter
	on_attach = function(bufnr)
		local gitsigns = require("gitsigns")

		-- Get the default branch (origin/HEAD -> origin/main or origin/master)
		local origin_head = vim.fn.systemlist("git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null")[1]
		if origin_head and origin_head ~= "" then
			-- Extract just the branch name (e.g., "refs/remotes/origin/main" -> "origin/main")
			local default_branch = origin_head:match("refs/remotes/(.*)")
			if default_branch then
				-- Get merge base between current branch and default branch
				local merge_base =
					vim.fn.systemlist(string.format("git merge-base HEAD %s 2>/dev/null", default_branch))[1]
				if merge_base and merge_base ~= "" then
					-- Set base to the merge-base commit
					gitsigns.change_base(merge_base, true) -- true = global (affects all buffers)
				end
			end
		end
	end,
})

-- Very subtle word-level diff highlighting using Nord palette diff backgrounds
-- Using Nord's pre-defined dim diff colors for background-only highlighting
-- Base background is nord0 (#2E3440), these are barely-tinted versions from Nord theme
local function set_gitsigns_highlights()
	vim.api.nvim_set_hl(0, "GitSignsAddInline", { bg = "#45523E", fg = nil }) -- Nord DiffAdded
	vim.api.nvim_set_hl(0, "GitSignsDeleteInline", { bg = "#4F2D30", fg = nil }) -- Nord DiffRemoved
	vim.api.nvim_set_hl(0, "GitSignsChangeInline", { bg = "#524633", fg = nil }) -- Nord DiffModified
	vim.api.nvim_set_hl(0, "GitSignsAddLnInline", { bg = "#45523E", fg = nil }) -- Nord DiffAdded (buffer)
	vim.api.nvim_set_hl(0, "GitSignsDeleteLnInline", { bg = "#4F2D30", fg = nil }) -- Nord DiffRemoved (buffer)
	vim.api.nvim_set_hl(0, "GitSignsChangeLnInline", { bg = "#524633", fg = nil }) -- Nord DiffModified (buffer)
	vim.api.nvim_set_hl(0, "GitSignsAddVirtLnInline", { bg = "#45523E", fg = nil }) -- Nord DiffAdded (virtual lines)
	vim.api.nvim_set_hl(0, "GitSignsDeleteVirtLnInline", { bg = "#4F2D30", fg = nil }) -- Nord DiffRemoved (virtual lines)
	vim.api.nvim_set_hl(0, "GitSignsChangeVirtLnInline", { bg = "#524633", fg = nil }) -- Nord DiffModified (virtual lines)
end

-- Apply highlights immediately
set_gitsigns_highlights()

-- Reapply after colorscheme changes (fixes issue where colorscheme reloads override highlights)
vim.api.nvim_create_autocmd("ColorScheme", {
	pattern = "*",
	callback = set_gitsigns_highlights,
	desc = "Reapply gitsigns inline diff highlights after colorscheme changes",
})

vim.keymap.set("n", "<leader>gw", require("gitsigns").stage_buffer, { silent = true, noremap = true })
vim.keymap.set("n", "<leader>gl", require("gitsigns").blame_line, { silent = true, noremap = true })
vim.keymap.set("n", "]c", function()
	require("gitsigns").nav_hunk("next")
end, { silent = true, noremap = true })
vim.keymap.set("n", "[c", function()
	require("gitsigns").nav_hunk("prev")
end, { silent = true, noremap = true })
vim.keymap.set("n", "<leader>hp", require("gitsigns").preview_hunk, { silent = true, noremap = true })
vim.keymap.set("n", "<leader>hs", require("gitsigns").stage_hunk, { silent = true, noremap = true })
vim.keymap.set("n", "<leader>hr", require("gitsigns").reset_hunk, { silent = true, noremap = true })
vim.keymap.set("n", "<leader>hR", require("gitsigns").reset_buffer, { silent = true, noremap = true })
vim.keymap.set("n", "<leader>hu", require("gitsigns").undo_stage_hunk, { silent = true, noremap = true })
vim.keymap.set("n", "<leader>hU", require("gitsigns").reset_buffer_index, { silent = true, noremap = true })
vim.keymap.set("n", "vh", require("gitsigns").select_hunk, { silent = true, noremap = true })

-- Toggle inline diff highlighting (shows changes highlighted in buffer)
vim.keymap.set(
	"n",
	"<leader>hd",
	require("gitsigns").toggle_word_diff,
	{ silent = true, noremap = true, desc = "Toggle inline word diff" }
)
vim.keymap.set(
	"n",
	"<leader>hD",
	require("gitsigns").toggle_deleted,
	{ silent = true, noremap = true, desc = "Toggle deleted lines" }
)

-- Toggle between comparing against HEAD (uncommitted changes) and merge-base (branch changes)
vim.keymap.set("n", "<leader>gb", function()
	require("gitsigns").change_base(nil, true) -- Reset to default (HEAD/index)
	vim.notify("Gitsigns: comparing against HEAD (uncommitted changes)", vim.log.levels.INFO)
end, { silent = true, noremap = true, desc = "Compare against HEAD" })

vim.keymap.set("n", "<leader>gB", function()
	local origin_head = vim.fn.systemlist("git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null")[1]
	if origin_head and origin_head ~= "" then
		local default_branch = origin_head:match("refs/remotes/(.*)")
		if default_branch then
			local merge_base = vim.fn.systemlist(string.format("git merge-base HEAD %s 2>/dev/null", default_branch))[1]
			if merge_base and merge_base ~= "" then
				require("gitsigns").change_base(merge_base, true)
				vim.notify("Gitsigns: comparing against " .. default_branch .. " (branch changes)", vim.log.levels.INFO)
			end
		end
	end
end, { silent = true, noremap = true, desc = "Compare against default branch" })
