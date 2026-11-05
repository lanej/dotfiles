local M = {}

function M.setup()
	local colors = require("baleia").setup({})
	local function colorize(buf)
		if vim.bo[buf].filetype ~= "zellij-scrollback" or vim.b[buf].scrollback_colored then
			return
		end
		vim.b[buf].scrollback_colored = true
		vim.bo[buf].modeline = false
		-- WHY: Rendering strips ANSI codes; the snapshot must still close with :q.
		vim.bo[buf].buftype = "nofile"
		vim.bo[buf].bufhidden = "wipe"
		local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
		if table.concat(lines, "\n"):find("\27[", 1, true) then
			colors.once(buf)
		else
			vim.bo[buf].syntax = "sh"
		end
	end
	vim.api.nvim_create_autocmd("FileType", {
		group = vim.api.nvim_create_augroup("ZellijScrollback", { clear = true }),
		pattern = "zellij-scrollback",
		callback = function(event)
			colorize(event.buf)
		end,
	})
	colorize(vim.api.nvim_get_current_buf())
end

return M
