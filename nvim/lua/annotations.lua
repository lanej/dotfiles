local M = {}

function M.setup()
	require("todo-comments").setup({
		keywords = {
			WTF = { icon = "🤨", color = "warning", alt = { "DAFUQ", "GAH" } },
			SEE = { icon = "👀", color = "info", alt = { "REF" } },
			TODO = { icon = "🫥", color = "info" },
			WHY = { icon = " ", color = "hint" },
		},
	})
	vim.keymap.set("n", "<leader>an", "<cmd>TodoFzfLua<CR>", {
		silent = true,
		desc = "Search code annotations",
	})
end

return M
