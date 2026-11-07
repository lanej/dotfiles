-- Run the client navigation contract through the installed configuration.
-- Fixed LSP responses keep this independent of bqls, gcloud, and credentials.
-- Set NVIM_TEST_BQLS_LIVE=1 to additionally exercise real local SQL resolution.
-- nvim --headless -i NONE '+lua dofile("nvim/tests/definition.lua")' '+qa!'
local temp = vim.fn.tempname()
local client_id
local live = vim.env.NVIM_TEST_BQLS_LIVE == "1"
local previous_config
local previously_enabled
local function transport(respond)
	return function(dispatchers)
		local closing, id = false, 0
		local function close()
			if closing then
				return
			end
			closing = true
			vim.schedule(function()
				dispatchers.on_exit(0, 0)
			end)
		end
		return {
			request = function(method, params, callback)
				id = id + 1
				local response
				if method == "initialize" then
					response = { capabilities = { definitionProvider = true, hoverProvider = true } }
				elseif method ~= "shutdown" then
					response = respond(method, params, callback)
					if response == "delayed" then
						return true, id
					end
				end
				vim.schedule(function()
					callback(nil, response)
				end)
				return true, id
			end,
			notify = function(method)
				if method == "exit" then
					close()
				end
				return true
			end,
			is_closing = function()
				return closing
			end,
			terminate = close,
		}
	end
end
local function location(path, line, character)
	return {
		uri = vim.uri_from_fname(path),
		range = {
			start = { line = line, character = character },
			["end"] = { line = line, character = character },
		},
	}
end
local function workflow()
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
	-- These are server replies for explicit request positions, not a mock SQL
	-- resolver. Only live mode can establish the server's SQL interpretation.
	if not live then
		previous_config = vim.deepcopy(vim.lsp.config.bqls)
		previously_enabled = vim.lsp.is_enabled("bqls")
		vim.lsp.enable("bqls", false)
		local replies = {
			[vim.uri_from_fname(query)] = {
				["1:14"] = location(query, 0, 5),
				["0:35"] = location(ddl, 1, 13),
			},
			[vim.uri_from_fname(ddl)] = {
				["7:12"] = location(ddl, 3, 2),
				["6:25"] = location(ddl, 4, 2),
			},
		}
		vim.lsp.config("bqls", {
			cmd = transport(function(method, params)
				assert(method == "textDocument/definition", "Unexpected local request: " .. method)
				local positions = assert(replies[params.textDocument.uri], "Unexpected source document")
				local key = params.position.line .. ":" .. params.position.character
				local reply = assert(positions[key], "Unexpected definition position: " .. key)
				return { reply }
			end),
		})
		vim.lsp.enable("bqls")
	end
	vim.cmd.edit(vim.fn.fnameescape(query))
	local source_buf = vim.api.nvim_get_current_buf()
	assert(
		vim.wait(20000, function()
			local client = vim.lsp.get_clients({ name = "bqls", bufnr = source_buf })[1]
			if client and client.initialized then
				client_id = client.id
				return true
			end
		end, 100),
		"bqls did not attach for navigation"
	)
	vim.api.nvim_win_set_cursor(0, { 2, 14 })
	vim.cmd.normal("gd")
	assert(
		vim.wait(5000, function()
			return vim.deep_equal(vim.api.nvim_win_get_cursor(0), { 1, 5 })
		end, 10),
		"gd did not resolve the CTE"
	)
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
		vim.wait(5000, function()
			return vim.deep_equal(vim.api.nvim_win_get_cursor(0), { 4, 2 })
		end, 10),
		"Clustering column did not resolve its declaration"
	)
	vim.cmd.normal(vim.api.nvim_replace_termcodes("<C-o>", true, false, true))
	assert(vim.deep_equal(vim.api.nvim_win_get_cursor(0), { 8, 12 }), "Column jump lost its return position")
	vim.api.nvim_win_set_cursor(0, { 7, 25 })
	vim.cmd.normal(vim.g.mapleader .. "cd")
	assert(
		vim.wait(5000, function()
			return vim.deep_equal(vim.api.nvim_win_get_cursor(0), { 5, 2 })
		end, 10),
		"Partition column did not resolve its declaration"
	)
	vim.cmd.normal(vim.api.nvim_replace_termcodes("<C-o>", true, false, true))
	assert(vim.deep_equal(vim.api.nvim_win_get_cursor(0), { 7, 25 }), "Partition jump lost its return position")
	vim.cmd.buffer(source_buf)

	-- Continue the same navigation workflow with a table that has no local DDL.
	-- The transport fixture exercises real LSP dispatch without requiring warehouse access.
	vim.lsp.enable("bqls", false)
	assert(
		vim.wait(5000, function()
			return #vim.lsp.get_clients({ name = "bqls", bufnr = source_buf }) == 0
		end, 10),
		"Previous bqls client did not stop"
	)
	local requests = {}
	local delayed
	client_id = vim.lsp.start({
		name = "bqls",
		root_dir = temp,
		cmd = transport(function(method, params, callback)
			requests[#requests + 1] = method
			if method == "textDocument/definition" then
				return {
					{
						uri = "bqls://project/demo/dataset/deliveries/schema/live_journeys",
						range = { start = { line = 0, character = 0 }, ["end"] = { line = 0, character = 0 } },
					},
				}
			end
			assert(method == "bqls/virtualTextDocument", "Unexpected schema request: " .. method)
			assert(params.textDocument.uri:find("/schema/live_journeys", 1, true), "Schema URI missing")
			local response = {
				contents = {
					kind = "markdown",
					value = "Table: demo.deliveries.live_journeys\n\n| Name | Type |\n| --- | --- |\n| delivery_id | STRING |",
				},
			}
			if delayed then
				delayed = function()
					callback(nil, response)
				end
				return "delayed"
			end
			return response
		end),
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
	assert(vim.tbl_contains(requests, "bqls/virtualTextDocument"), "Server schema document was not requested")
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
	print("BigQuery definition workflow passed (" .. (live and "live local server" or "fixture LSP transport") .. ")")
end
local ok, err = xpcall(workflow, debug.traceback)
if client_id then
	local client = vim.lsp.get_client_by_id(client_id)
	if client then
		client:stop(true)
	end
end
-- Restoring automatic activation must not start the real server on fixture
-- buffers that remain loaded after navigating back from the DDL document.
for _, buf in ipairs(vim.api.nvim_list_bufs()) do
	if vim.api.nvim_buf_get_name(buf):sub(1, #temp + 1) == temp .. "/" then
		vim.api.nvim_buf_delete(buf, { force = true })
	end
end
if previous_config then
	vim.lsp.enable("bqls", false)
	vim.lsp.config.bqls = previous_config
	vim.lsp.enable("bqls", previously_enabled)
end
vim.wait(100)
vim.fn.delete(temp, "rf")
if not ok then
	vim.api.nvim_err_writeln(err)
	vim.cmd.cquit(1)
end
