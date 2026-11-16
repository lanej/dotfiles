local Direction = require("zellij.protobuf").enum("Direction")
local directions = {
	h = Direction.DIRECTION_LEFT,
	j = Direction.DIRECTION_DOWN,
	k = Direction.DIRECTION_UP,
	l = Direction.DIRECTION_RIGHT,
}
local M = {}

local function navigate(pane, direction)
	local function query(name, json)
		local output = coroutine.yield({ [name] = json and { output_json = true } or {} }, true)
		return json and vim.json.decode(output) or output
	end
	local function owner()
		local rows = vim.split(query("list_clients"), "\n", { trimempty = true })
		assert(
			rows[1] and rows[1]:match("^CLIENT_ID%s+ZELLIJ_PANE_ID%s+RUNNING_COMMAND%s*$"),
			"Invalid Zellij client listing"
		)
		assert(#rows <= 2, "Pane navigation needs one attached client; use Ctrl-f h/j/k/l")
		local attached = {}
		for _, tab in ipairs(query("list_tabs", true)) do
			for _, id in ipairs(tab.other_focused_clients) do
				attached[id] = tab
			end
		end
		local count, client, tab = 0, nil, nil
		for id, focused_tab in pairs(attached) do
			count, client, tab = count + 1, id, focused_tab
		end
		assert(count == 1, "Pane navigation needs one attached client; use Ctrl-f h/j/k/l")
		if rows[2] then
			local listed, source = rows[2]:match("^(%d+)%s+(%S+)")
			assert(tonumber(listed) == client, "Cannot establish the active Zellij client")
			if source ~= "terminal_" .. pane then
				return nil
			end
		end
		for _, source in ipairs(query("list_panes", true)) do
			if not source.is_plugin and source.id == pane then
				if
					source.is_focused
					and not source.is_suppressed
					and not source.is_fullscreen
					and source.tab_id == tab.tab_id
					and not tab.is_fullscreen_active
				then
					return client
				end
				return nil
			end
		end
		error("The calling Zellij pane no longer exists")
	end
	local client = owner()
	if not client or owner() ~= client then
		return
	end
	local action = direction == "p" and { focus_last_pane = {} }
		or { move_focus = { direction = assert(directions[direction], "Invalid direction") } }
	coroutine.yield(action, false, client)
end

function M.new(client, pane, notify)
	local backend = {}
	function backend:navigate(direction, complete)
		local deadline = vim.uv.hrtime() + 2000000000
		local worker = coroutine.create(function()
			navigate(pane, direction)
		end)
		local function finish(error)
			if error then
				notify(error)
			end
			if complete then
				complete(error or "ok")
			end
		end
		local step
		step = function(error, output)
			if error then
				finish(error)
				return
			end
			local ok, action, query, target = coroutine.resume(worker, output)
			if not ok then
				finish(tostring(action))
				return
			end
			if coroutine.status(worker) == "dead" then
				finish()
				return
			end
			local remaining = math.ceil((deadline - vim.uv.hrtime()) / 1000000)
			if remaining <= 0 then
				finish("Zellij navigation deadline exceeded")
				return
			end
			client:request(
				action,
				{ terminal_id = pane, client_id = target, expect_output = query, timeout_ms = remaining },
				step
			)
		end
		step()
		return self
	end
	return backend
end

function M.setup()
	local options = { auto_save = "current", disable_on_zoom = false }
	if vim.env.ZELLIJ and vim.env.ZELLIJ_PANE_ID then
		local client, error = require("zellij-session").connect()
		if client then
			options.mux = M.new(client, tonumber(vim.env.ZELLIJ_PANE_ID), function(message)
				vim.notify(message, vim.log.levels.WARN)
			end)
			vim.api.nvim_create_autocmd("VimLeavePre", {
				once = true,
				callback = function()
					client:close()
				end,
			})
		else
			options.mux = require("Navigator.mux.vi"):new()
			vim.notify(error, vim.log.levels.WARN)
		end
	end
	require("Navigator").setup(options)
	for key, direction in pairs({ h = "Left", j = "Down", k = "Up", l = "Right" }) do
		vim.keymap.set({ "i", "n", "x" }, "<C-" .. key .. ">", "<Cmd>Navigator" .. direction .. "<cr>", {
			noremap = true,
			silent = true,
		})
	end
end

return M
