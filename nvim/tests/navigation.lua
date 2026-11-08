-- nvim --headless -u NONE -l nvim/tests/navigation.lua
-- Isolated acceptance run: uv run --no-project scripts/test-nvim-navigation.py
-- GUTENTAGS_RUNTIME can point to a disposable checkout for testing before install.
local repo = vim.fn.getcwd()
local temp = vim.fn.tempname()
vim.fn.mkdir(temp, "p")
temp = assert(vim.uv.fs_realpath(temp))
vim.opt.runtimepath:prepend(repo .. "/nvim")
local lazy = vim.env.NVIM_TEST_PLUGIN_ROOT or vim.fn.expand("~/.local/share/nvim/lazy")
vim.opt.runtimepath:append(lazy .. "/fzf-lua")
vim.opt.runtimepath:append(lazy .. "/nvim-treesitter/runtime")
vim.opt.runtimepath:append(vim.env.NVIM_TEST_SITE or vim.fn.expand("~/.local/share/nvim/site"))
local gutentags = vim.env.GUTENTAGS_RUNTIME or lazy .. "/vim-gutentags"
vim.opt.runtimepath:append(gutentags)
vim.o.hidden = true
vim.o.columns = 160
vim.o.lines = 45
vim.o.swapfile = false
vim.g.mapleader = ","
require("tag-index").setup()
vim.g.gutentags_cache_dir = temp .. "/cache"
vim.cmd("runtime plugin/gutentags.vim")
require("fzfconfig")
local fzf = require("fzf-lua")
local grep = fzf.grep
local clients = {}
local transport

local function wait(predicate, message, timeout)
	assert(
		vim.wait(timeout or 5000, predicate, 10),
		message
			.. "\n"
			.. vim.inspect(vim.api.nvim_buf_get_lines(0, 0, -1, false))
			.. "\n"
			.. vim.fn.execute("messages")
	)
end
local function keys(mapping)
	vim.cmd.normal(vim.api.nvim_replace_termcodes(mapping, true, false, true))
end
local function write(path, lines)
	vim.fn.writefile(lines, path)
end
local function command(args)
	local result = vim.system(args, { text = true }):wait()
	assert(result.code == 0, result.stderr)
	return result.stdout
end
local function server(root, respond)
	local client = assert(vim.lsp.start({
		name = "navigation-fixture",
		root_dir = root,
		cmd = function(dispatchers)
			local closing, id = false, 0
			return {
				request = function(method, params, callback)
					id = id + 1
					local response
					if method == "initialize" then
						response = {
							capabilities = {
								definitionProvider = true,
								documentSymbolProvider = true,
								workspaceSymbolProvider = true,
								referencesProvider = true,
								implementationProvider = true,
							},
						}
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
				notify = function()
					return true
				end,
				is_closing = function()
					return closing
				end,
				terminate = function()
					closing = true
					vim.schedule(function()
						dispatchers.on_exit(0, 0)
					end)
				end,
			}
		end,
	}))
	table.insert(clients, client)
	wait(function()
		return vim.lsp.get_client_by_id(client).initialized
	end, "Fixture LSP did not initialize")
	return client
end
local function location(path, line, col)
	return {
		uri = vim.uri_from_fname(path),
		range = {
			start = { line = line or 0, character = col or 0 },
			["end"] = { line = line or 0, character = col or 0 },
		},
	}
end

local function workflow()
	local project = temp .. "/project with spaces"
	vim.fn.mkdir(project, "p")
	command({ "git", "init", "-q", project })
	vim.cmd.cd(vim.fn.fnameescape(project))
	write(project .. "/.gitignore", { "ignored.lua" })
	write(project .. "/ignored.lua", { "function ignored_symbol() end" })
	local target = project .. "/library file.lua"
	write(target, { "function destination() end", "function another_destination() end" })
	local source = project .. "/caller.lua"
	write(source, { "destination()", "missing_symbol()" })
	vim.cmd.edit(vim.fn.fnameescape(source))
	local source_buf = vim.api.nvim_get_current_buf()
	vim.bo.filetype = "lua"
	wait(function()
		return #vim.fn.taglist("^destination$") > 0
	end, "Initial background tags generation failed")
	assert(#vim.fn.taglist("^ignored_symbol$") == 0, "Initial index included ignored source")
	assert(not vim.uv.fs_stat(project .. "/tags"), "Index was written into project")
	local index = vim.fn.tagfiles()[1]
	vim.fn.mkdir(project .. "/a", "p")
	vim.fn.mkdir(project .. "/b", "p")
	write(project .. "/a/client.lua", { "function createShipment() end" })
	write(project .. "/b/client.lua", { "function createShipment() end" })
	command({ "git", "-C", project, "add", "--", "library file.lua" })
	write(project .. "/large.lua", vim.split(string.rep("local value = true\n", 1200), "\n", { trimempty = true }))

	local function picker(needle)
		wait(
			function()
				return vim.bo.buftype == "terminal"
					and table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n"):find(needle, 1, true)
			end,
			"Native picker did not display "
				.. needle
				.. " "
				.. vim.inspect(vim.api.nvim_buf_get_lines(0, 0, -1, false))
		)
	end
	local function close_picker()
		fzf.hide()
		wait(function()
			return vim.api.nvim_get_current_buf() == source_buf
		end, "Picker did not close")
	end

	-- LSP owns the complete interaction, including empty and slow replies.
	local requests, delayed = {}, nil
	transport = server(project, function(method, params, callback)
		table.insert(requests, method)
		if method == "textDocument/definition" then
			return { location(target), location(target, 1) }
		elseif method == "textDocument/documentSymbol" then
			return {
				{
					name = "ShippingClient",
					kind = 5,
					children = {
						{
							name = "server_outline",
							kind = 12,
							detail = "(parcel) → Receipt",
							range = location(source, 1).range,
							selectionRange = location(source, 1).range,
						},
						{
							name = "shipment",
							kind = 13,
							detail = "Option<Shipment>",
							range = location(source, 1).range,
							selectionRange = location(source, 1).range,
						},
					},
					range = location(source, 1).range,
					selectionRange = location(source, 1).range,
				},
			}
		elseif method == "workspace/symbol" then
			return {
				{ name = "server_symbol", kind = 12, containerName = "ShippingClient", location = location(target) },
				{ name = "large_symbol", kind = 12, location = location(project .. "/large.lua") },
				{
					name = "createShipment",
					kind = 12,
					containerName = "VeryLongShippingClient",
					detail = "(account,parcel,options) -> Shipment",
					location = location(project .. "/a/client.lua"),
				},
				{
					name = "createShipment",
					kind = 12,
					containerName = "VeryLongShippingClient",
					detail = "(account,parcel,options) -> Shipment",
					location = location(project .. "/b/client.lua"),
				},
			}
		elseif method == "textDocument/references" then
			delayed = true
			vim.defer_fn(function()
				callback(nil, { location(target), location(target, 1) })
			end, 1700)
			return "delayed"
		end
		assert(method == "textDocument/implementation")
		return {}
	end)
	keys(",cd")
	picker("library file.lua")
	assert(#vim.api.nvim_list_wins() >= 3, "Definitions lost native file preview")
	close_picker()
	keys(",bs")
	picker("server_outline")
	picker("Option<Shipment>")
	local outline = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
	local variable_row = assert(outline:match("[^\n]*shipment[^\n]*"))
	assert(variable_row:find("Option<Shipment>", 1, true), "Variable lost its server-provided type detail")
	local outline_row = assert(outline:match("[^\n]*server_outline[^\n]*"))
	assert(
		outline_row:find("(parcel) → Receipt", 1, true) and outline_row:find("ShippingClient", 1, true),
		"LSP detail or parent context missing"
	)
	assert(outline_row:find("+2", 1, true), "Untracked file did not show added line count")
	assert(not outline:match("%d+:%d+"), "Outline still displays row and column metadata")
	assert(
		vim.api.nvim_win_get_width(0) <= 100 and vim.api.nvim_win_get_height(0) <= 12,
		"Outline did not use the compact stacked layout"
	)
	vim.api.nvim_chan_send(vim.bo.channel, "server_outline")
	vim.wait(100)
	vim.api.nvim_chan_send(vim.bo.channel, "\r")
	wait(function()
		return vim.api.nvim_get_current_buf() == source_buf and vim.api.nvim_win_get_cursor(0)[1] == 2
	end, "Hidden coordinates broke symbol selection")
	keys("<C-o>")
	keys(",ws")
	picker("server_symbol")
	local workspace = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
	assert(
		workspace:find("ShippingClient", 1, true) and workspace:find("library file.lua", 1, true),
		"Workspace context lost scope or short path"
	)
	assert(workspace:find("+2", 1, true), "Staged file with spaces did not show added line count")
	assert(workspace:find("+1.2k", 1, true), "Large line counts were not abbreviated")
	vim.api.nvim_chan_send(vim.bo.channel, "\r")
	wait(function()
		return vim.api.nvim_buf_get_name(0) == target
	end, "Hidden workspace coordinates broke symbol selection")
	keys("<C-o>")
	command({
		"git",
		"-C",
		project,
		"-c",
		"user.name=Fixture",
		"-c",
		"user.email=fixture@example.invalid",
		"-c",
		"commit.gpgsign=false",
		"commit",
		"--only",
		"-qm",
		"test: baseline target",
		"--",
		"library file.lua",
	})
	write(target, { "function destination() end", "function another_destination() return true end" })
	command({ "git", "-C", project, "add", "--", "library file.lua" })
	write(target, { "function destination() end", "function another_destination() return false end" })
	keys(",ws")
	picker("server_symbol")
	local changed = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
	local changed_row = assert(changed:match("[^\n]*server_symbol[^\n]*"))
	assert(
		changed_row:find("+1", 1, true) and changed_row:find("−1", 1, true) and not changed_row:find("+2", 1, true),
		"Staged and unstaged edits were double-counted"
	)
	close_picker()
	vim.o.columns = 220
	keys(",ws")
	picker("createShipment")
	wait(function()
		local wide = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
		return wide:find("a/client.lua", 1, true) and wide:find("b/client.lua", 1, true)
	end, "Long signatures hid distinguishing workspace paths")
	close_picker()
	vim.o.columns = 160
	local search
	fzf.grep = function(opts)
		search = opts
	end
	keys(",cr")
	wait(function()
		return delayed ~= nil
	end, "References did not request LSP")
	assert(not search, "Slow LSP switched to text search")
	picker("library file.lua")
	assert(
		not table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n"):match("%d+:%d+"),
		"References still display row and column metadata"
	)
	vim.api.nvim_chan_send(vim.bo.channel, "\r")
	wait(function()
		return vim.api.nvim_buf_get_name(0) == target
	end, "Hidden reference coordinates broke selection")
	keys("<C-o>")
	keys(",cy")
	vim.wait(100)
	assert(not search and vim.api.nvim_get_current_buf() == source_buf, "Empty LSP switched source")
	assert(vim.tbl_contains(requests, "workspace/symbol"), "Workspace picker bypassed LSP")
	vim.lsp.get_client_by_id(transport):stop(true)
	wait(function()
		return #vim.lsp.get_clients({ bufnr = source_buf }) == 0
	end, "Fixture did not stop")
	print("Native LSP pickers preserve preview and slow/empty responses")

	keys(",cd")
	picker("destination")
	vim.api.nvim_chan_send(vim.bo.channel, "\r")
	wait(function()
		return vim.api.nvim_buf_get_name(0) == target
	end, "Tag selection lost destination")
	keys("<C-o>")
	assert(vim.api.nvim_get_current_buf() == source_buf, "Tag selection lost jump-back position")
	vim.api.nvim_win_set_cursor(0, { 2, 0 })
	keys(",cd")
	assert(
		search and search.search == "missing_symbol" and search.cwd == project,
		"Missing definition lost text fallback"
	)
	search = nil
	keys(",cr")
	assert(search and search.prompt:find("References · Text matches", 1, true), "References fallback missing")
	search = nil
	keys(",cy")
	assert(
		search and search.prompt:find("Implementations · Text matches", 1, true),
		"Implementations fallback missing"
	)
	print("No-LSP definitions use tags; references and implementations use labeled text search")

	vim.api.nvim_buf_set_lines(0, 0, -1, false, { "function saved_outline() end" })
	vim.cmd.write()
	wait(function()
		return #vim.fn.taglist("^saved_outline$") > 0
	end, "Save did not update tags")
	keys(",bs")
	picker("saved_outline")
	assert(
		not table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n"):find("another_destination", 1, true),
		"Buffer tags escaped current file"
	)
	close_picker()
	keys(",ws")
	picker("another_destination")
	close_picker()
	local other = temp .. "/other checkout"
	command({
		"git",
		"-C",
		project,
		"-c",
		"user.name=Fixture",
		"-c",
		"user.email=fixture@example.invalid",
		"-c",
		"commit.gpgsign=false",
		"commit",
		"--allow-empty",
		"-qm",
		"test: initialize fixture",
	})
	command({ "git", "-C", project, "worktree", "add", "--detach", "-q", other })
	write(other .. "/other.lua", { "function other_symbol() end" })
	vim.cmd.edit(vim.fn.fnameescape(other .. "/other.lua"))
	wait(function()
		return #vim.fn.taglist("^other_symbol$") > 0
	end, "Worktree did not generate tags")
	assert(vim.fn.tagfiles()[1] ~= index, "Checkouts shared tag cache")
	print("Native buffer/workspace tags and isolated background indexes passed")
end

local ok, err = xpcall(workflow, debug.traceback)
fzf.grep = grep
for _, id in ipairs(clients) do
	local client = vim.lsp.get_client_by_id(id)
	if client then
		client:stop(true)
	end
end
vim.wait(100)
vim.fn.delete(temp, "rf")
if not ok then
	io.stderr:write(err .. "\n")
	vim.cmd.cquit(1)
end
vim.cmd("qa!")
