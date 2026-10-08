-- Run against the installed bqls fork and completion configuration:
-- nvim --headless -i NONE '+lua dofile("nvim/tests/completion.lua")'
local function workflow()
	vim.o.columns = 120
	vim.o.lines = 40
	local path = vim.fn.tempname() .. ".bqsql"
	local source = {
		"WITH shipments AS (SELECT 'usps' AS carrier, 1 AS pieces, ['ground'] AS services)",
		"SELECT  FROM shipments;",
	}
	vim.fn.writefile(source, path)
	vim.cmd.edit(vim.fn.fnameescape(path))
	local buf = vim.api.nvim_get_current_buf()
	assert(
		vim.wait(20000, function()
			local client = vim.lsp.get_clients({ name = "bqls", bufnr = buf })[1]
			return client and client.initialized
		end, 100),
		"bqls did not attach"
	)
	local client = assert(vim.lsp.get_clients({ name = "bqls", bufnr = buf })[1])
	assert(client.config.cmd[1] == vim.fn.expand("~/.local/bin/bqls"), "Installed fork was not selected")
	vim.api.nvim_win_set_cursor(0, { 2, 7 })
	assert(vim.api.nvim_get_mode().mode == "i", "Completion workflow did not enter Insert mode")
	local blink = require("blink.cmp")
	blink.show({ providers = { "lsp" } })
	assert(
		vim.wait(10000, function()
			return blink.is_menu_visible() and #blink.get_items() > 0
		end, 20),
		"LSP completion menu did not open"
	)
	local items = blink.get_items()
	local carrier_index, carrier, relation, services
	for index, item in ipairs(items) do
		if item.label == "carrier" then
			carrier_index, carrier = index, item
		elseif item.label == "shipments" then
			relation = item
		elseif item.label == "services" then
			services = item
		end
	end
	assert(carrier and carrier.detail == "STRING", "Column type was not supplied as completion detail")
	assert(services and services.detail == "ARRAY<STRING>", "Array type was lost")
	assert(relation and relation.detail == "CTE", "CTE was not distinguished from a column")
	assert(carrier.kind == vim.lsp.protocol.CompletionItemKind.Field, "Column lost its Field kind")
	assert(relation.kind == vim.lsp.protocol.CompletionItemKind.Module, "CTE has a field kind")
	local menu = require("blink.cmp.completion.windows.menu")
	local lines = vim.api.nvim_buf_get_lines(menu.win:get_buf(), 0, -1, false)
	local column_line, table_line
	for _, line in ipairs(lines) do
		if line:find("carrier", 1, true) then
			column_line = line
		elseif line:find("shipments", 1, true) then
			table_line = line
		end
	end
	assert(column_line and column_line:match("carrier%s+STRING"), "Menu omitted the SQL type")
	assert(
		table_line and table_line:find("󰓫", 1, true) and table_line:match("shipments%s+CTE"),
		"Table icon/type missing"
	)
	assert(vim.deep_equal(source, vim.api.nvim_buf_get_lines(buf, 0, -1, false)), "Opening completion modified SQL")
	local accepted = false
	blink.accept({
		index = carrier_index,
		callback = function()
			accepted = true
		end,
	})
	assert(
		vim.wait(2000, function()
			return accepted
		end, 10),
		"Completion was not accepted"
	)
	assert(
		vim.api.nvim_buf_get_lines(buf, 1, 2, false)[1] == "SELECT carrier FROM shipments;",
		"Completion inserted presentation details into SQL: " .. vim.api.nvim_buf_get_lines(buf, 1, 2, false)[1]
	)
	client:stop(true)
	vim.fn.delete(path)
end

vim.api.nvim_create_autocmd("VimEnter", {
	once = true,
	callback = function()
		vim.cmd.startinsert()
		vim.defer_fn(function()
			local ok, err = xpcall(workflow, debug.traceback)
			if not ok then
				io.stderr:write(err .. "\n")
				vim.cmd.cquit(1)
			else
				io.stdout:write("BigQuery completion workflow passed\n")
				vim.cmd("qa!")
			end
		end, 50)
	end,
})
