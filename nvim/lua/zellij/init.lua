local wire = require("zellij.protobuf")
local M = {}

---Create a client for a resolved socket identity: { path, device, inode }.
function M.new(identity)
	local path, device, inode = unpack(identity)
	local active, closed = {}, false
	local client = {}

	---Send one generated Action table without retrying it.
	---Options: terminal_id, client_id, expect_output, timeout_ms (default 2000).
	---The callback receives (error, output, response) on Neovim's main loop; returns a cancel function.
	function client:request(action, options, complete)
		assert(type(complete) == "function", "A Zellij response callback is required")
		options = options or {}
		local timeout = options.timeout_ms or 2000
		assert(type(timeout) == "number" and timeout > 0, "Zellij request timeout must be positive")
		local expect_output = options.expect_output
		local pipe, timer, finished = nil, nil, false
		local function finish(error, output, response)
			if finished then
				return
			end
			finished = true
			if timer and not timer:is_closing() then
				timer:stop()
				timer:close()
			end
			if pipe then
				active[pipe] = nil
				pipe:read_stop()
				pipe:close()
			end
			vim.schedule(function()
				complete(error, output, response)
			end)
		end
		local function cancel()
			finish("Zellij request cancelled; outcome may be unknown")
		end
		local stat = vim.uv.fs_lstat(path)
		if closed then
			finish("Zellij client is closed")
			return cancel
		end
		if not stat or stat.type ~= "socket" or stat.dev ~= device or stat.ino ~= inode then
			finish("Zellij session socket changed; reconnect before sending another request")
			return cancel
		end
		local encoded, frame = pcall(function()
			return wire.frame(wire.encode("ClientToServerMsg", {
				action = {
					action = action,
					terminal_id = options.terminal_id,
					client_id = options.client_id,
					is_cli_client = true,
				},
			}))
		end)
		if not encoded then
			finish("Invalid Zellij request: " .. tostring(frame))
			return cancel
		end
		pipe = vim.uv.new_pipe(false)
		active[pipe] = cancel
		local buffer = ""
		pipe:connect(path, function(error)
			if finished then
				return
			end
			if error then
				finish("Cannot connect to Zellij: " .. error)
				return
			end
			pipe:read_start(function(read_error, bytes)
				if finished then
					return
				end
				if read_error or not bytes then
					finish("Zellij connection was lost; request outcome may be unknown")
					return
				end
				local decoded, decode_error = pcall(function()
					buffer = buffer .. bytes
					while #buffer >= 4 do
						local size = wire.frame_size(buffer)
						if #buffer < size + 4 then
							return
						end
						local message = wire.decode("ServerToClientMsg", buffer:sub(5, size + 4))
						buffer = buffer:sub(size + 5)
						if message.log_error then
							finish(table.concat(message.log_error.lines or {}, "\n"), nil, message)
							return
						elseif message.log then
							finish(nil, table.concat(message.log.lines or {}, "\n"), message)
							return
						elseif message.unblock_input_thread and not expect_output then
							finish(nil, "", message)
							return
						elseif message.exit then
							finish(
								message.exit.payload or "Zellij closed the connection; request outcome may be unknown",
								nil,
								message
							)
							return
						end
					end
				end)
				if not decoded then
					finish("Invalid Zellij IPC response: " .. tostring(decode_error))
				end
			end)
			pipe:write(frame, function(write_error)
				if not finished and write_error then
					finish("Zellij request write failed: " .. write_error)
				end
			end)
		end)
		-- warning: A timeout cannot establish whether an action ran; never replay it.
		timer = vim.defer_fn(function()
			finish("Zellij request timed out; outcome may be unknown")
		end, timeout)
		return cancel
	end

	---Cancel outstanding requests and prevent new ones.
	function client:close()
		closed = true
		while next(active) do
			local _, cancel = next(active)
			cancel()
		end
	end
	return client
end

---Resolve the current session once. Returns (client, error); launches no per-request processes.
function M.connect()
	local resolved, result = pcall(function()
		return vim.system({ "zellij-context", "socket" }, { text = true, timeout = 2000 }):wait()
	end)
	if not resolved then
		return nil, "Cannot resolve Zellij session socket: " .. tostring(result)
	end
	local ok, identity = pcall(vim.json.decode, result.stdout or "")
	if result.code ~= 0 or not ok or type(identity) ~= "table" then
		local message = vim.trim(result.stderr or "")
		return nil, message ~= "" and message or "Cannot resolve Zellij session socket; run make zellij-helpers"
	end
	return M.new(identity)
end

return M
