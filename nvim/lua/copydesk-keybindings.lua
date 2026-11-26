vim.api.nvim_create_autocmd("User", {
	group = vim.api.nvim_create_augroup("DotfilesCopydeskKeybindings", { clear = true }),
	pattern = "CopydeskAttach",
	callback = function(event)
		local copydesk = require("copydesk")
		local function bind(mode, key, action, description)
			vim.keymap.set(mode, "<localleader>s" .. key, action, { buffer = event.data.buf, desc = description })
		end

		bind("n", "c", copydesk.comment, "Comment on the current line")
		bind("x", "c", copydesk.comment_selection, "Comment on the selected lines")
		bind("n", "s", copydesk.documents, "Choose a Copydesk document")
		bind("n", "r", copydesk.responses, "Inspect Copydesk responses")
		bind("n", "d", copydesk.changes, "Jump to Copydesk changes")
		bind("n", "v", copydesk.compare, "Compare Copydesk revisions")
		bind("n", "m", copydesk.resolve, "Adopt the incoming Copydesk revision")
		bind("n", "l", function()
			if vim.fn.confirm("Reload the Copydesk document and discard local edits?", "&Cancel\n&Reload", 1) == 2 then
				copydesk.reload(true)
			end
		end, "Reload the Copydesk document")
		bind("n", "x", copydesk.reconnect, "Reconnect Copydesk")
	end,
})
