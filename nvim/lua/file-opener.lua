local M = {}

function M.identity()
	return {
		pid = vim.fn.getpid(),
		socket = vim.v.servername,
		session = vim.env.ZELLIJ_SESSION_NAME,
		pane = tonumber(vim.env.ZELLIJ_PANE_ID),
	}
end

function M.open(target, expected)
	if expected then
		local current = M.identity()
		for _, field in ipairs({ "pid", "socket", "session", "pane" }) do
			assert(current[field] == expected[field], "The destination editor changed; select the file again")
		end
	end
	assert(type(target.path) == "string" and target.path:sub(1, 1) == "/", "Expected an absolute filename")
	assert(vim.fn.filereadable(target.path) == 1, "The selected file is no longer readable")
	local buffer = vim.fn.bufadd(target.path)
	vim.fn.bufload(buffer)
	local windows = vim.fn.win_findbuf(buffer)
	if #windows > 0 then
		vim.api.nvim_set_current_win(windows[1])
	else
		-- set_current_buf preserves modified buffers and reports errors such as a
		-- modified current buffer with 'hidden' disabled instead of forcing a switch.
		vim.api.nvim_set_current_buf(buffer)
	end
	local line = math.min(math.max(target.line or 1, 1), vim.api.nvim_buf_line_count(buffer))
	local content = vim.api.nvim_buf_get_lines(buffer, line - 1, line, false)[1] or ""
	local column = math.min(math.max((target.column or 1) - 1, 0), math.max(#content - 1, 0))
	vim.api.nvim_win_set_cursor(0, { line, column })
	vim.cmd("normal! zv")
	return M.identity()
end

function M.setup()
	if not vim.env.ZELLIJ_SESSION_NAME or not vim.env.ZELLIJ_PANE_ID then
		return
	end
	local group = vim.api.nvim_create_augroup("DotfilesFileOpener", { clear = true })
	local registration
	vim.api.nvim_create_autocmd("VimEnter", {
		group = group,
		once = true,
		callback = function()
			if vim.fn.executable("zellij-helper") == 0 or vim.v.servername == "" then
				return
			end
			registration = vim.system(
				{ "zellij-helper", "editor-register", vim.v.servername, tostring(vim.fn.getpid()) },
				{},
				function(result)
					if result.code ~= 0 then
						vim.schedule(function()
							vim.notify("File opener registration: " .. vim.trim(result.stderr), vim.log.levels.WARN)
						end)
					end
				end
			)
		end,
	})
	vim.api.nvim_create_autocmd("VimLeavePre", {
		group = group,
		callback = function()
			if registration then
				-- Finish registration before removing it, including a quick editor exit.
				registration:wait(1000)
				vim.system({ "zellij-helper", "editor-unregister", vim.v.servername, tostring(vim.fn.getpid()) })
					:wait(1000)
			end
		end,
	})
end

return M
