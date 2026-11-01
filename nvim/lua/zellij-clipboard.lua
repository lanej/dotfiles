local M = {}

function M.setup()
	if (vim.env.ZELLIJ or "") == "" or (vim.env.ZELLIJ_SESSION_NAME or "") == ""
		or vim.fn.executable("zellij-context") == 0 then
		return false
	end
	local context = vim.system({ "zellij-context", "provider" }, { text = true }):wait(1000)
	if context.code ~= 0 or vim.trim(context.stdout or "") ~= "zellij" then
		return false
	end
	vim.api.nvim_create_autocmd("TextYankPost", {
		group = vim.api.nvim_create_augroup("ZellijClipboard", { clear = true }),
		callback = function()
			local event = vim.v.event
			if event.operator ~= "y" or event.regname == "_" then
				return
			end
			if vim.fn.executable("zellij-clipboard") == 0 then
				vim.notify("Install clipboard support with make zellij", vim.log.levels.WARN)
				return
			end
			local text = table.concat(event.regcontents, "\n")
			if event.regtype == "V" then
				text = text .. "\n"
			end
			local copied = vim.system({ "zellij-clipboard", "copy" }, { stdin = text, text = true }):wait(2000)
			if copied.code ~= 0 then
				vim.notify(vim.trim(copied.stderr or "Copy failed"), vim.log.levels.WARN)
				return
			end
			-- Write-only OSC 52 reaches the local terminal even through SSH. A
			-- single string preserves linewise trailing newlines and block spaces.
			require("vim.ui.clipboard.osc52").copy("+")({ text })
		end,
	})
	return true
end

return M
