local M = {}

function M.setup()
	local options = { auto_save = "current", disable_on_zoom = false }
	-- Both nesting directions inherit the outer mux's variables. Establish
	-- which live ancestor owns this editor before choosing its pane backend.
	local provider
	if vim.env.ZELLIJ and vim.env.ZELLIJ_PANE_ID then
		if vim.fn.executable("zellij-context") == 1 then
			local context = vim.system({ "zellij-context", "provider" }, { text = true }):wait(1000)
			provider = context.code == 0 and vim.trim(context.stdout or "") or nil
		end
		if provider ~= "zellij" and provider ~= "tmux" then
			-- An unresolved/stale environment must not move an outer mux pane.
			options.mux = require("Navigator.mux.vi"):new()
			vim.notify("Cannot identify the pane owner; install helpers with make zellij", vim.log.levels.WARN)
		end
	end
	if provider == "zellij" then
		local directions = { h = "left", j = "down", k = "up", l = "right", p = "previous" }
		options.mux = {
			navigate = function(self, direction)
				if vim.fn.executable("zellij-navigate") == 0 then
					vim.notify("Install the pane navigation helper with make zellij", vim.log.levels.WARN)
					return self
				end
				local result = vim.system({ "zellij-navigate", directions[direction] }, { text = true }):wait(5000)
				if result.code ~= 0 then
					local message = vim.trim(result.stderr or "")
					vim.notify(message ~= "" and message or "Zellij navigation failed", vim.log.levels.WARN)
				end
				return self
			end,
		}
	end
	require("Navigator").setup(options)
	for key, direction in pairs({ h = "Left", j = "Down", k = "Up", l = "Right" }) do
		vim.keymap.set({ "i", "n" }, "<C-" .. key .. ">", "<Cmd>Navigator" .. direction .. "<cr>", {
			noremap = true,
			silent = true,
		})
	end
end

return M
