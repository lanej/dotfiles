local root = vim.env.DOTFILES_TEST_ROOT
vim.opt.rtp:prepend(root .. "/nvim")
local protobuf = require("zellij.protobuf")
local zellij = require("zellij")

local function check(mode)
	local path = "/tmp/zellij-lua-client-" .. vim.uv.os_getpid() .. "-" .. mode
	local server = vim.uv.new_pipe(false)
	assert(server:bind(path))
	local accepted, peer, received = 0, nil, nil
	server:listen(4, function(error)
		assert(not error, error)
		accepted = accepted + 1
		peer = vim.uv.new_pipe(false)
		server:accept(peer)
		local buffer = ""
		peer:read_start(function(read_error, bytes)
			if read_error or not bytes then
				return
			end
			buffer = buffer .. bytes
			if #buffer < 4 then
				return
			end
			local size = protobuf.frame_size(buffer)
			if #buffer < size + 4 then
				return
			end
			received = protobuf.decode("ClientToServerMsg", buffer:sub(5, size + 4))
			peer:read_stop()
			if mode == "query" then
				peer:write(protobuf.frame(protobuf.encode("ServerToClientMsg", { unblock_input_thread = {} })))
				local frame =
					protobuf.frame(protobuf.encode("ServerToClientMsg", { log = { lines = { "home", "work" } } }))
				peer:write(frame:sub(1, 2))
				vim.defer_fn(function()
					peer:write(frame:sub(3))
				end, 10)
			elseif mode == "error" then
				peer:write(
					protobuf.frame(
						protobuf.encode("ServerToClientMsg", { log_error = { lines = { "original server error" } } })
					)
				)
			elseif mode == "malformed" then
				peer:write(string.char(0, 0, 128, 0))
			end
		end)
	end)
	local stat = assert(vim.uv.fs_lstat(path))
	local client = zellij.new({ path, stat.dev, stat.ino })
	local replies, response_error, output, raw = 0, nil, nil, nil
	local cancel = client:request({ query_tab_names = {} }, {
		terminal_id = 0,
		client_id = 7,
		expect_output = true,
		timeout_ms = mode == "timeout" and 30 or 1000,
	}, function(error, response, message)
		assert(not vim.in_fast_event(), "Response callback ran in a fast event")
		replies, response_error, output, raw = replies + 1, error, response, message
	end)
	if mode == "cancel" or mode == "close" then
		assert(
			vim.wait(1000, function()
				return received ~= nil
			end, 1),
			"Request never reached server"
		)
		if mode == "cancel" then
			cancel()
			cancel()
		else
			client:close()
			client:close()
		end
	end
	assert(
		vim.wait(2000, function()
			return replies > 0
		end, 1),
		"Response callback never ran"
	)
	assert(replies == 1 and accepted == 1, "Request was replayed or completed more than once")
	assert(received.action.terminal_id == 0 and received.action.client_id == 7)
	assert(received.action.action.query_tab_names, "Generated non-navigation action was lost")
	if mode == "query" then
		assert(not response_error and output == "home\nwork", tostring(response_error))
	elseif mode == "error" then
		assert(response_error == "original server error" and raw.log_error.lines[1] == response_error)
	elseif mode == "malformed" then
		assert(response_error:find("frame exceeds limit", 1, true))
	elseif mode == "timeout" then
		assert(response_error:find("timed out", 1, true))
	else
		assert(response_error:find("cancelled", 1, true))
	end
	client:close()
	local rejected = false
	client:request({ query_tab_names = {} }, {}, function(error)
		rejected = error == "Zellij client is closed"
	end)
	assert(
		vim.wait(1000, function()
			return rejected
		end, 1),
		"Closed client accepted a request"
	)
	if peer and not peer:is_closing() then
		peer:close()
	end
	server:close()
	vim.uv.fs_unlink(path)
end

for _, mode in ipairs({ "query", "error", "malformed", "timeout", "cancel", "close" }) do
	check(mode)
end
print("PASS: reusable Zellij client handles fragmented replies, errors, cancellation, close, and uncertain timeouts")
