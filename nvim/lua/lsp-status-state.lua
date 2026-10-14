-- Observe the RPC lifecycle without changing Neovim's error/exit handling.
local M = { failures = {} }
local states = setmetatable({}, { __mode = "k" })
local startup_failures = {}
local refresh_pending = false

local function refresh()
	if refresh_pending then
		return
	end
	refresh_pending = true
	vim.schedule(function()
		refresh_pending = false
		local lualine = package.loaded["lualine"]
		if lualine then
			lualine.refresh()
		end
	end)
end

local function root_key(config)
	return config.root_dir and vim.fs.normalize(config.root_dir):gsub("/$", "") or ""
end

function M.for_buffer(buf)
	local result = vim.tbl_extend("force", {}, M.failures[buf] or {})
	local filename = vim.fs.normalize(vim.api.nvim_buf_get_name(buf))
	for _, roots in pairs(startup_failures) do
		for root, failure in pairs(roots) do
			local filetypes = failure.config.filetypes
			if
				(not filetypes or vim.list_contains(filetypes, vim.bo[buf].filetype))
				and (root == "" or filename == root or vim.startswith(filename, root .. "/"))
			then
				result[failure.name] = failure
			end
		end
	end
	return result
end

function M.failed(client)
	return states[client.config] and states[client.config].failed
end

function M.wrap_cmd(cmd)
	return function(dispatchers, config)
		local state = { failed = false }
		states[config] = state
		refresh()
		local on_error, on_exit = dispatchers.on_error, dispatchers.on_exit
		dispatchers.on_error = function(...)
			state.failed = true
			refresh()
			return on_error(...)
		end
		dispatchers.on_exit = function(code, signal)
			if state.failed or code ~= 0 or signal ~= 0 then
				for _, client in ipairs(vim.lsp.get_clients({ _uninitialized = true })) do
					-- is_stopped() also returns true after an unexpected process exit.
					if client.config == config and not client._is_stopping then
						for buf in pairs(client.attached_buffers) do
							M.failures[buf] = M.failures[buf] or {}
							M.failures[buf][client.name] = {
								name = client.name,
								config = { filetypes = config.filetypes },
							}
						end
					end
				end
			end
			refresh()
			return on_exit(code, signal)
		end
		local ok, rpc = pcall(function()
			if type(cmd) == "function" then
				return cmd(dispatchers, config)
			end
			return vim.lsp.rpc.start(cmd, dispatchers, {
				cwd = config.cmd_cwd,
				env = config.cmd_env,
				detached = config.detached,
			})
		end)
		if not ok then
			startup_failures[config.name] = startup_failures[config.name] or {}
			startup_failures[config.name][root_key(config)] = {
				name = config.name,
				config = { filetypes = config.filetypes },
			}
			error(rpc, 0)
		end
		return rpc
	end
end

local group = vim.api.nvim_create_augroup("lsp_status_state", { clear = true })
vim.api.nvim_create_autocmd("LspAttach", {
	group = group,
	callback = function(event)
		local client = vim.lsp.get_client_by_id(event.data.client_id)
		if client and M.failures[event.buf] then
			M.failures[event.buf][client.name] = nil
		end
		if client and startup_failures[client.name] then
			startup_failures[client.name][root_key(client.config)] = nil
		end
		refresh()
	end,
})
vim.api.nvim_create_autocmd("BufWipeout", {
	group = group,
	callback = function(event)
		M.failures[event.buf] = nil
	end,
})

return M
