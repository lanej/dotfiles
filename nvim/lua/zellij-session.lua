local M = {}

---Resolve the current session once. Returns (client, error); launches no per-request processes.
function M.connect()
	local resolved, result = pcall(function()
		return vim.system({ "zellij-context", "socket" }, { text = true, timeout = 2000 }):wait()
	end)
	if not resolved then
		return nil, "Cannot resolve Zellij session socket: " .. tostring(result)
	end
	local ok, identity = pcall(vim.json.decode, result.stdout or "")
	if result.code ~= 0 or not ok or type(identity) ~= "table" then
		local message = vim.trim(result.stderr or "")
		return nil, message ~= "" and message or "Cannot resolve Zellij session socket; run make zellij-helpers"
	end
	return require("zellij").new(identity)
end

return M
