local M = {}
local projects = {}

local function bigquery_project(path)
	local root = vim.fs.root(path, ".git")
	if not root then
		return false
	end
	if projects[root] ~= nil then
		return projects[root]
	end

	-- Project config is authoritative; do not use the global formatter config
	-- to classify every SQL dialect as BigQuery.
	local config = root .. "/.sql-formatter.json"
	if vim.fn.filereadable(config) == 1 then
		local ok, settings = pcall(function()
			return vim.json.decode(table.concat(vim.fn.readfile(config), "\n"))
		end)
		if ok and type(settings) == "table" and type(settings.language) == "string" then
			projects[root] = settings.language:lower() == "bigquery"
			return projects[root]
		end
	end

	-- Use repository identity so temporary and persistent worktrees both work.
	local result = vim.system({ "git", "-C", root, "config", "--get", "remote.origin.url" }, { text = true }):wait(1000)
	local remote = vim.trim(result.stdout or ""):gsub("%.git$", "")
	projects[root] = result.code == 0 and remote:match("[:/]easypost%-sandbox/looker%-development$") ~= nil
	return projects[root]
end

function M.setup()
	vim.treesitter.language.register("sql_bigquery", "sql.bigquery")
	vim.filetype.add({
		extension = {
			bqsql = "sql.bigquery",
			sql = function(path, buf)
				if path:lower():match("%.bigquery%.sql$") or path:lower():match("%.bq%.sql$") then
					return "sql.bigquery"
				end
				if vim.api.nvim_buf_is_valid(buf) then
					for _, line in ipairs(vim.api.nvim_buf_get_lines(buf, 0, 5, false)) do
						if line:lower():match("^%s*#standardsql%s*$") then
							return "sql.bigquery"
						end
					end
				end
				return bigquery_project(path) and "sql.bigquery" or "sql"
			end,
		},
	})
end

return M
