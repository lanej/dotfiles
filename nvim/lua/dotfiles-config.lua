-- Resolve machine overrides and composed sets through the same consumer as Make.
local M = {}
local settings

function M.enabled(key)
	if not settings then
		local source = assert(vim.uv.fs_realpath(debug.getinfo(1, "S").source:sub(2)))
		local root = vim.fs.dirname(vim.fs.dirname(vim.fs.dirname(source)))
		local python = vim.fn.exepath("python3")
		local result = python ~= ""
			and vim.system({ python, root .. "/scripts/dotfiles-config.py", "--format", "json" }, { text = true })
				:wait(10000)
		local ok, resolved = pcall(vim.json.decode, result and result.stdout or "")
		if result and result.code == 0 and ok and type(resolved) == "table" and type(resolved.settings) == "table" then
			settings = resolved.settings
		else
			settings = {}
			vim.schedule(function()
				vim.notify(
					"Could not resolve dotfiles configuration; using default editor features. "
						.. (result and vim.trim(result.stderr or "") or "Python 3.11+ is required."),
					vim.log.levels.WARN
				)
			end)
		end
	end
	return settings[key] == true
end

return M
