-- Run through the installed configuration after Noice's VimEnter setup:
-- nvim --headless -i NONE '+lua dofile("nvim/tests/hover.lua")'
local function workflow()
	vim.o.columns = 150
	vim.o.lines = 40
	local source = { "SELECT address FROM shipments;" }
	vim.api.nvim_buf_set_lines(0, 0, -1, false, source)
	local contents = {
		kind = "markdown",
		value = table.concat({
			"| Name | Type | Mode | Description |",
			"| --- | --- | --- | --- |",
			"| `address` | RECORD | NULLABLE | destination |",
			"| &nbsp;&nbsp;city | STRING | REQUIRED | 東京 \\| city |",
			"",
			"```sql",
			"| code | untouched |",
			"| --- | --- |",
			"| x | y |",
			"```",
		}, "\n"),
	}
	local original = vim.deepcopy(contents)
	local request = vim.lsp.buf_request
	local sent = false
	vim.lsp.buf_request = function(_, method, _, callback)
		assert(method == "textDocument/hover", "Expected the hover request")
		sent = true
		callback(nil, { contents = contents }, { bufnr = vim.api.nvim_get_current_buf() })
	end
	vim.lsp.buf.hover()
	vim.lsp.buf_request = request
	assert(sent, "Hover bypassed the LSP entrypoint")
	local docs = require("noice.lsp.docs")
	assert(
		vim.wait(2000, function()
			return docs._messages.hover and docs._messages.hover:win() ~= nil
		end, 10),
		"Hover popup did not open"
	)
	local win = docs._messages.hover:win()
	local lines = vim.api.nvim_buf_get_lines(vim.api.nvim_win_get_buf(win), 0, -1, false)
	local boundaries
	for r = 1, 4 do
		local positions = {}
		for c in lines[r]:gmatch("()|") do
			if lines[r]:sub(c - 1, c - 1) ~= "\\" then
				positions[#positions + 1] = vim.fn.strdisplaywidth(lines[r]:sub(1, c - 1))
			end
		end
		assert(#positions == 5, "Schema row lost a cell")
		boundaries = boundaries or positions
		assert(vim.deep_equal(boundaries, positions), "Rendered table boundaries are misaligned")
	end
	assert(lines[4]:find("|   city", 1, true), "Nested field indentation was lost")
	assert(vim.tbl_contains(lines, "| code | untouched |"), "Fenced code was reformatted")
	assert(vim.wo[win].conceallevel == 0 and not vim.wo[win].wrap, "Popup options break column alignment")
	assert(vim.deep_equal(contents, original), "Hover modified the server response")
	assert(vim.deep_equal(source, vim.api.nvim_buf_get_lines(0, 0, -1, false)), "Hover modified the source")
	docs.on_close()
end

vim.api.nvim_create_autocmd("VimEnter", {
	once = true,
	callback = function()
		vim.schedule(function()
			local ok, err = xpcall(workflow, debug.traceback)
			if not ok then
				io.stderr:write(err .. "\n")
				vim.cmd.cquit(1)
			else
				io.stdout:write("Hover table workflow passed\n")
				vim.cmd("qa!")
			end
		end)
	end,
})
