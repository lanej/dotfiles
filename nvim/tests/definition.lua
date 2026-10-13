-- Run through the installed configuration:
-- nvim --headless -i NONE '+lua dofile("nvim/tests/definition.lua")' '+qa!'
local temp = vim.fn.tempname()
local client_id
local function workflow()
	vim.lsp.enable("bqls", false)
	vim.fn.mkdir(temp .. "/.git", "p")
	vim.fn.mkdir(temp .. "/sql", "p")
	temp = assert(vim.uv.fs_realpath(temp))
	vim.fn.writefile({ '{"language":"bigquery"}' }, temp .. "/.sql-formatter.json")
	local ddl = temp .. "/sql/create_deliveries.sql"
	local query = temp .. "/sql/report.bqsql"
	vim.fn.writefile({
		"-- CREATE TABLE `demo.deliveries.journeys` (decoy STRING);",
		"CREATE TABLE `demo.deliveries.journeys` (",
		"  metadata STRUCT<delivery_id STRING>,",
		"  delivery_id STRING NOT NULL,",
		"  cohort_date DATE",
		")",
		"PARTITION BY DATE_TRUNC(cohort_date, MONTH)",
		"CLUSTER BY delivery_id;",
	}, ddl)
	local source = {
		"WITH journeys AS (SELECT * FROM `demo.deliveries.journeys`)",
		"SELECT * FROM journeys;",
	}
	vim.fn.writefile(source, query)
	vim.cmd.edit(vim.fn.fnameescape(query))
	local source_buf = vim.api.nvim_get_current_buf()
	vim.api.nvim_win_set_cursor(0, { 2, 14 })
	vim.cmd.normal("gd")
	assert(vim.deep_equal(vim.api.nvim_win_get_cursor(0), { 1, 5 }), "gd did not resolve the CTE")
	vim.cmd.normal(vim.api.nvim_replace_termcodes("<C-o>", true, false, true))
	assert(vim.deep_equal(vim.api.nvim_win_get_cursor(0), { 2, 14 }), "Definition jump lost its return position")

	vim.api.nvim_win_set_cursor(0, { 1, 35 })
	vim.cmd.normal("gd")
	assert(
		vim.wait(5000, function()
			return vim.api.nvim_buf_get_name(0) == ddl
		end, 10),
		"gd did not open local CREATE TABLE SQL: " .. vim.api.nvim_buf_get_name(0)
	)
	assert(vim.deep_equal(vim.api.nvim_win_get_cursor(0), { 2, 13 }), "Definition selected comment text")
	vim.cmd.normal(vim.api.nvim_replace_termcodes("<C-o>", true, false, true))
	assert(vim.api.nvim_get_current_buf() == source_buf, "Definition jump did not return to source SQL")
	vim.cmd.buffer(vim.fn.bufnr(ddl))
	vim.api.nvim_win_set_cursor(0, { 8, 12 })
	vim.cmd.normal("gd")
	assert(
		vim.deep_equal(vim.api.nvim_win_get_cursor(0), { 4, 2 }),
		"Clustering column did not resolve its declaration"
	)
	vim.cmd.normal(vim.api.nvim_replace_termcodes("<C-o>", true, false, true))
	assert(vim.deep_equal(vim.api.nvim_win_get_cursor(0), { 8, 12 }), "Column jump lost its return position")
	vim.api.nvim_win_set_cursor(0, { 7, 25 })
	vim.cmd.normal(vim.g.mapleader .. "cd")
	assert(vim.deep_equal(vim.api.nvim_win_get_cursor(0), { 5, 2 }), "Partition column did not resolve its declaration")
	vim.cmd.normal(vim.api.nvim_replace_termcodes("<C-o>", true, false, true))
	assert(vim.deep_equal(vim.api.nvim_win_get_cursor(0), { 7, 25 }), "Partition jump lost its return position")
	vim.cmd.buffer(source_buf)

	-- Continue the same navigation workflow with a table that has no local DDL.
	-- The transport fixture exercises real LSP dispatch without requiring warehouse access.
	local requests = {}
	local delayed
	client_id = vim.lsp.start({
		name = "bqls",
		root_dir = temp,
		cmd = function()
			local closing = false
			local id = 0
			return {
				request = function(method, params, callback)
					id = id + 1
					requests[#requests + 1] = method
					local response
					if method == "initialize" then
						response = { capabilities = { definitionProvider = true, hoverProvider = true } }
					elseif method == "textDocument/definition" then
						response = {
							{
								uri = "bqls://project/demo/dataset/deliveries/table/live_journeys",
								range = { start = { line = 0, character = 0 }, ["end"] = { line = 0, character = 0 } },
							},
						}
					elseif method == "textDocument/hover" then
						assert(params.textDocument.uri == vim.uri_from_fname(query), "Schema request lost its source")
						response = {
							contents = {
								kind = "markdown",
								value = "Table: demo.deliveries.live_journeys\n\n| Name | Type |\n| --- | --- |\n| delivery_id | STRING |",
							},
						}
						if delayed then
							delayed = function()
								callback(nil, response)
							end
							return true, id
						end
					else
						assert(method == "shutdown", "Unexpected LSP request: " .. method)
					end
					vim.schedule(function()
						callback(nil, response)
					end)
					return true, id
				end,
				notify = function()
					return true
				end,
				is_closing = function()
					return closing
				end,
				terminate = function()
					closing = true
				end,
			}
		end,
	})
	assert(client_id, "Definition transport did not start")
	assert(
		vim.wait(2000, function()
			return vim.lsp.get_client_by_id(client_id).initialized
		end, 10),
		"Definition transport did not initialize"
	)
	source[1] = "WITH journeys AS (SELECT * FROM `demo.deliveries.live_journeys`)"
	vim.api.nvim_buf_set_lines(source_buf, 0, -1, false, source)
	vim.api.nvim_win_set_cursor(0, { 1, 35 })
	vim.cmd.normal(vim.g.mapleader .. "cd")
	assert(
		vim.wait(5000, function()
			return vim.bo.filetype == "markdown"
		end, 10),
		"Live schema fallback did not open"
	)
	assert(vim.bo.readonly and not vim.bo.modifiable, "Live schema must be read-only")
	assert(
		table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n"):find("delivery_id", 1, true),
		"Live schema omitted its fields"
	)
	assert(not vim.tbl_contains(requests, "bqls/virtualTextDocument"), "Definition fetched preview rows")
	vim.cmd.normal(vim.api.nvim_replace_termcodes("<C-o>", true, false, true))
	assert(vim.api.nvim_get_current_buf() == source_buf, "Live schema lost its return position")
	assert(vim.deep_equal(source, vim.api.nvim_buf_get_lines(0, 0, -1, false)), "Definition changed source SQL")

	delayed = true
	vim.cmd.normal("gd")
	assert(
		vim.wait(5000, function()
			return type(delayed) == "function"
		end, 10),
		"Delayed schema lookup was not requested"
	)
	vim.api.nvim_win_set_cursor(0, { 2, 0 })
	delayed()
	assert(vim.api.nvim_get_current_buf() == source_buf, "Stale schema response moved the editor")
	vim.bo.filetype = "sql"
	assert(vim.fn.maparg("gd", "n") == "", "BigQuery navigation leaked into generic SQL")
	print("BigQuery definition workflow passed")
end
local ok, err = xpcall(workflow, debug.traceback)
if client_id then
	vim.lsp.get_client_by_id(client_id):stop(true)
end
vim.fn.delete(temp, "rf")
if not ok then
	vim.api.nvim_err_writeln(err)
	vim.cmd.cquit(1)
end
