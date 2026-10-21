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
	-- Bright signs compare the buffer with the index; staged signs stay dim.
	signs_staged_enable = true,
	sign_priority = 6,
	linehl = false,
	on_attach = function(bufnr)
		vim.schedule(function()
			require("git-branch-signs").refresh(bufnr)
		end)
	end,
})

-- Very subtle word-level diff highlighting using Nord palette diff backgrounds
-- Using Nord's pre-defined dim diff colors for background-only highlighting
-- Base background is nord0 (#2E3440), these are barely-tinted versions from Nord theme
local function set_gitsigns_highlights()
	local colors = {
		Add = { "#A3BE8C", "#66755B" },
		Change = { "#EBCB8B", "#80704F" },
		Delete = { "#BF616A", "#80565B" },
		Topdelete = { "#BF616A", "#80565B" },
		Changedelete = { "#EBCB8B", "#80704F" },
	}
	for kind, color in pairs(colors) do
		vim.api.nvim_set_hl(0, "GitSigns" .. kind, { fg = color[1] })
		vim.api.nvim_set_hl(0, "GitSignsStaged" .. kind, { fg = color[2] })
	end
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

require("git-branch-signs").setup()

-- Apply highlights immediately
set_gitsigns_highlights()

-- Reapply after colorscheme changes (fixes issue where colorscheme reloads override highlights)
vim.api.nvim_create_autocmd("ColorScheme", {
	pattern = "*",
	callback = set_gitsigns_highlights,
	desc = "Reapply gitsigns inline diff highlights after colorscheme changes",
})

vim.keymap.set("n", "<leader>gW", require("gitsigns").stage_buffer, { silent = true, noremap = true })
vim.keymap.set("n", "<leader>gl", require("gitsigns").blame_line, { silent = true, noremap = true })
vim.keymap.set("n", "]c", function()
	require("git-branch-signs").navigate("next")
end, { silent = true, noremap = true })
vim.keymap.set("n", "[c", function()
	require("git-branch-signs").navigate("prev")
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

-- Keep hunk actions based on the index; toggle only the branch gutter layer.
vim.keymap.set("n", "<leader>gx", function()
	require("git-branch-signs").enable(false)
	vim.notify("Gitsigns: showing unstaged and staged changes", vim.log.levels.INFO)
end, { silent = true, noremap = true, desc = "Hide committed branch signs" })

vim.keymap.set("n", "<leader>gX", function()
	require("git-branch-signs").enable(true)
	vim.notify("Gitsigns: also showing committed branch changes", vim.log.levels.INFO)
end, { silent = true, noremap = true, desc = "Show committed branch signs" })
