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
	blink.hide()
	local declaration = {
		"CREATE TABLE deliveries (",
		"  amount NUMERIC OPTIONS(round /* rounding */ = 'ROUND_HALF_EVEN')",
		") OPTIONS(",
		"  description = 'Deliveries, OPTIONS(ignored)',",
		"  requ",
	}
	vim.api.nvim_buf_set_lines(buf, 0, -1, false, declaration)
	vim.api.nvim_win_set_cursor(0, { 5, #declaration[5] })
	blink.show({ providers = { "lsp" } })
	assert(
		vim.wait(2000, function()
			return blink.is_menu_visible() and #blink.get_items() > 0
		end, 10),
		"Offline table OPTIONS completion did not open"
	)
	local option_index, option
	for index, item in ipairs(blink.get_items()) do
		if item.label == "require_partition_filter" then
			option_index, option = index, item
		end
		assert(item.label ~= "rounding_mode", "Column option appeared in table completion")
		assert(item.label ~= "description", "Already specified option appeared again")
	end
	assert(option and option.detail == "BOOL", "Table option type was omitted")
	local menu_text = table.concat(vim.api.nvim_buf_get_lines(menu.win:get_buf(), 0, -1, false), "\n")
	assert(menu_text:match("require_partition_filter%s+BOOL"), "OPTIONS menu omitted the parameter type")
	assert(option.documentation.value:find("Supported values: TRUE, FALSE.", 1, true), "Option help omitted values")
	accepted = false
	blink.accept({
		index = option_index,
		callback = function()
			accepted = true
		end,
	})
	assert(
		vim.wait(2000, function()
			return accepted
		end, 10),
		"Option completion was not accepted"
	)
	assert(
		vim.api.nvim_buf_get_lines(buf, 4, 5, false)[1] == "  require_partition_filter = ",
		"Option assignment was not inserted"
	)

	blink.hide()
	vim.api.nvim_win_set_cursor(0, { 2, assert(declaration[2]:find("round", 1, true)) + #"round" - 1 })
	blink.show({ providers = { "lsp" } })
	assert(
		vim.wait(2000, function()
			return blink.is_menu_visible() and #blink.get_items() > 0
		end, 10),
		"Column OPTIONS menu did not open"
	)
	local column_index
	for index, item in ipairs(blink.get_items()) do
		if item.label == "rounding_mode" then
			column_index = index
		end
		assert(item.label ~= "require_partition_filter", "Table option appeared in column completion")
	end
	assert(column_index, "Column rounding_mode was not suggested")
	accepted = false
	blink.accept({
		index = column_index,
		callback = function()
			accepted = true
		end,
	})
	assert(
		vim.wait(2000, function()
			return accepted
		end, 10),
		"Column option was not accepted"
	)
	assert(
		vim.api.nvim_buf_get_lines(buf, 1, 2, false)[1]
			== "  amount NUMERIC OPTIONS(rounding_mode /* rounding */ = 'ROUND_HALF_EVEN')",
		"Editing a key duplicated its assignment"
	)
	blink.hide()
	local comment = "  require_partition_filter = TRUE, -- further options"
	vim.api.nvim_buf_set_lines(buf, 4, 5, false, { comment })
	vim.api.nvim_win_set_cursor(0, { 5, #comment })
	blink.show({ providers = { "lsp" } })
	vim.wait(200, function()
		return false
	end, 10)
	assert(not blink.is_menu_visible(), "OPTIONS completion appeared inside an unfinished line comment")
	blink.hide()
	local clustered = {
		"CREATE TABLE deliveries (",
		"  carrier_id STRING(36),",
		"  carrier STRING,",
		"  `case` STRING OPTIONS(description = 'Case category assigned by the carrier.'),",
		"  metadata STRUCT<carrier_shadow STRING OPTIONS(description = 'Nested description')> OPTIONS(description = 'Outer metadata'),",
		"  carrier_history ARRAY<STRING>,",
		"  carrier_estimate FLOAT64,",
		"  carrier_tenant STRING COLLATE 'und:ci'",
		")",
		"CLUSTER BY carrier_id, ca;",
	}
	vim.api.nvim_buf_set_lines(buf, 0, -1, false, clustered)
	vim.api.nvim_win_set_cursor(0, { 10, #clustered[10] - 1 })
	-- Use the configured providers to prove local candidates reach the normal menu.
	blink.show()
	assert(
		vim.wait(2000, function()
			for _, item in ipairs(blink.get_items()) do
				if item.source_id == "lsp" and item.label == "case" then
					return blink.is_menu_visible()
				end
			end
		end, 10),
		"CLUSTER BY did not offer the declared column in the normal menu"
	)
	local cluster_index
	for index, item in ipairs(blink.get_items()) do
		if item.source_id == "lsp" then
			if item.label == "case" then
				cluster_index = index
				assert(item.detail == "STRING", "Clustering column type was omitted")
				assert(
					item.documentation.value:find("Case category assigned by the carrier.", 1, true),
					"Column documentation omitted its description"
				)
				assert(
					item.documentation.value:find("Unicode text encoded as UTF-8.", 1, true),
					"Column documentation omitted its type meaning"
				)
			end
			assert(item.label ~= "carrier_id", "Already clustered column appeared again")
			assert(
				item.label ~= "carrier_shadow"
					and item.label ~= "carrier_history"
					and item.label ~= "carrier_estimate"
					and item.label ~= "carrier_tenant",
				"Ineligible clustering column was suggested"
			)
		end
	end
	local described_menu = table.concat(vim.api.nvim_buf_get_lines(menu.win:get_buf(), 0, -1, false), "\n")
	assert(
		described_menu:find("Case category assigned by the carrier.", 1, true),
		"Completion row omitted the column description"
	)
	local documentation = require("blink.cmp.completion.windows.documentation")
	blink.select_next({ auto_insert = false })
	assert(
		vim.wait(2000, function()
			return blink.get_selected_item_idx() == 1
		end, 10),
		"Menu did not select its first item"
	)
	if cluster_index > 1 then
		blink.select_next({ auto_insert = false, count = cluster_index - 1 })
	end
	assert(
		vim.wait(2000, function()
			return blink.get_selected_item_idx() == cluster_index
		end, 10),
		"Column selection failed"
	)
	blink.show_documentation()
	assert(
		vim.wait(2000, function()
			if not documentation.win:is_open() then
				return false
			end
			local text = table.concat(vim.api.nvim_buf_get_lines(documentation.win:get_buf(), 0, -1, false), "\n")
			return text:find("Case category assigned by the carrier.", 1, true)
				and text:find("Unicode text encoded as UTF-8.", 1, true)
		end, 10),
		"Completion documentation popup omitted the column/type descriptions"
	)
	accepted = false
	blink.accept({
		index = assert(cluster_index),
		callback = function()
			accepted = true
		end,
	})
	assert(
		vim.wait(2000, function()
			return accepted
		end, 10),
		"Clustering column was not accepted"
	)
	assert(
		vim.api.nvim_buf_get_lines(buf, 9, 10, false)[1] == "CLUSTER BY carrier_id, `case`;",
		"Clustering completion changed the clause"
	)
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
