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

-- SEE: Shared GitSigns highlights, including staged and inline states, live in dotfiles-theme.
require("git-branch-signs").setup()

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
