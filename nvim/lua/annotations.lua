local M = {}

function M.setup()
	require("todo-comments").setup({
		keywords = {
			WTF = { icon = "🤨", color = "warning", alt = { "DAFUQ", "GAH" } },
			SEE = { icon = "👀", color = "info", alt = { "REF" } },
			TODO = { icon = "🫥", color = "info" },
			WHY = { icon = " ", color = "hint" },
			rationale = { icon = " ", color = "hint" },
			warning = { icon = " ", color = "warning" },
			workaround = { icon = " ", color = "warning" },
			todo = { icon = "🫥", color = "info" },
			fixme = { icon = " ", color = "error" },
		},
		highlight = {
			pattern = {
				-- rationale: Capture the full scoped label first and its type second for plugin styling and search messages.
				[[<((rationale|warning|workaround|todo|fixme)%(\([a-z0-9][a-z0-9._/-]*\))?:) \S@=]],
				[[.*<[A-Z]@=(KEYWORDS)\s*:]],
			},
		},
		search = {
			pattern = [[\b(KEYWORDS)(\([a-z0-9][a-z0-9._/-]*\))?:]],
		},
	})
	vim.keymap.set("n", "<leader>an", "<cmd>TodoFzfLua<CR>", {
		silent = true,
		desc = "Search code annotations",
	})
end

return M
