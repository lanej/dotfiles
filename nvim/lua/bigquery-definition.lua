local M = {}

-- Neovim only handles navigation and the server's virtual-document protocol.
-- SQL names, scopes, declarations and schema selection are owned by bqls.
function M.goto_definition()
	local ctx = {
		buf = vim.api.nvim_get_current_buf(),
		win = vim.api.nvim_get_current_win(),
		cursor = vim.api.nvim_win_get_cursor(0),
		tick = vim.api.nvim_buf_get_changedtick(0),
	}
	local client
	for _, candidate in ipairs(vim.lsp.get_clients({ name = "bqls", bufnr = ctx.buf })) do
		if candidate.initialized and not candidate:is_stopped() then
			client = candidate
			break
		end
	end
	if not client then
		vim.notify("bqls is not ready for definition lookup", vim.log.levels.INFO)
		return
	end
	local function current()
		return vim.api.nvim_win_is_valid(ctx.win)
			and vim.api.nvim_get_current_win() == ctx.win
			and vim.api.nvim_win_get_buf(ctx.win) == ctx.buf
			and vim.api.nvim_buf_get_changedtick(ctx.buf) == ctx.tick
			and vim.deep_equal(vim.api.nvim_win_get_cursor(ctx.win), ctx.cursor)
	end
	local function open(loc)
		if not loc or not current() then
			return
		end
		local uri = loc.uri or loc.targetUri
		if not uri:match("^bqls://") then
			vim.lsp.util.show_document(loc, client.offset_encoding, { focus = true })
			return
		end
		client:request("bqls/virtualTextDocument", { textDocument = { uri = uri } }, function(err, result)
			if not current() then
				return
			end
			if err then
				vim.notify(err.message, vim.log.levels.WARN)
				return
			end
			local lines = result and result.contents and vim.lsp.util.convert_input_to_markdown_lines(result.contents)
				or {}
			if #lines == 0 then
				vim.notify("No definition found", vim.log.levels.INFO)
				return
			end
			local buf = vim.api.nvim_create_buf(false, true)
			vim.api.nvim_buf_set_name(buf, uri .. " [" .. buf .. "]")
			lines = require("markdown-tables").align(lines)
			vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
			vim.bo[buf].bufhidden = "wipe"
			vim.bo[buf].filetype = "markdown"
			vim.bo[buf].modifiable = false
			vim.bo[buf].readonly = true
			vim.cmd("normal! m'")
			vim.api.nvim_win_set_buf(ctx.win, buf)
		end, ctx.buf)
	end
	client:request(
		"textDocument/definition",
		vim.lsp.util.make_position_params(ctx.win, client.offset_encoding),
		function(err, result)
			if not current() then
				return
			end
			if err then
				vim.notify(err.message, vim.log.levels.WARN)
				return
			end
			local locations = result and (vim.islist(result) and result or { result }) or {}
			if #locations == 1 and not locations[1].bqlsCandidateName then
				open(locations[1])
			elseif #locations > 0 then
				vim.ui.select(locations, {
					prompt = "Choose SQL definition:",
					format_item = function(loc)
						local uri = loc.uri or loc.targetUri
						local range = loc.range or loc.targetSelectionRange
						return (loc.bqlsCandidateName and (loc.bqlsCandidateName .. " · ") or "")
							.. uri
							.. ":"
							.. (range.start.line + 1)
					end,
				}, open)
			else
				vim.notify("No definition found", vim.log.levels.INFO)
			end
		end,
		ctx.buf
	)
end

return M
