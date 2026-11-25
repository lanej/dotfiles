local api = require("beads.api")
local M = {}

function M.local_project()
	-- The service controller uses this path independently of XDG_STATE_HOME.
	local state = vim.fn.expand("~/.local/state/beads-service")
	local file = state .. "/endpoint.json"
	assert(vim.fn.filereadable(file) == 1, "No local Beads endpoint. Check `beads-service status`.")
	local ok, endpoint = pcall(function()
		return vim.json.decode(table.concat(vim.fn.readfile(file), "\n"))
	end)
	assert(
		ok
			and type(endpoint) == "table"
			and endpoint.ready == true
			and type(endpoint.url) == "string"
			and endpoint.url:match("^http://127%.0%.0%.1:%d+$")
			and type(endpoint.database) == "string"
			and endpoint.database:match("^[%w_%-]+$")
			and endpoint.workspace == state .. "/workspace",
		"Invalid local Beads endpoint record. Check `beads-service status`."
	)
	local context = api.discover_context(endpoint.url)
	assert(
		context.backend == "dolt"
			and context.dolt_mode == "server"
			and context.database == endpoint.database
			and context.repo_root == endpoint.workspace
			and context.beads_dir == endpoint.workspace .. "/.beads"
			and vim.tbl_contains(context.capabilities, "project.enforce"),
		"Beads context differs from the local service record. Check `beads-service status`."
	)
	return { name = endpoint.database, settings = { url = endpoint.url, project_id = context.project_id } }
end

return M
