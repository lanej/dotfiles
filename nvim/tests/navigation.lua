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
vim.o.swapfile = false
vim.g.mapleader = ","
require("tag-index").setup()
vim.g.gutentags_cache_dir = temp .. "/cache"
vim.cmd("runtime plugin/gutentags.vim")
require("fzfconfig")
local fzf = require("fzf-lua")
local select = vim.ui.select
local register = fzf.register_ui_select
local grep, live = fzf.grep, fzf.fzf_live
local clients = {}
local transport

local function wait(predicate, message, timeout)
	assert(vim.wait(timeout or 5000, predicate, 10), message)
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
	write(project .. "/.gitignore", { "ignored.lua" })
	write(project .. "/ignored.lua", { "function ignored_symbol() end" })
	local target = project .. "/library file.lua"
	write(target, { "function destination() end" })
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

	-- Definition workflow: LSP, then a timed-out server with a usable tag,
	-- then text search; late replies cannot steal focus or move the cursor.
	local delayed
	transport = server(project, function(method, _, callback)
		assert(method == "textDocument/definition")
		if delayed then
			delayed = callback
			return "delayed"
		end
		return { location(source, 1) }
	end)
	keys(",cd")
	wait(function()
		return vim.api.nvim_win_get_cursor(0)[1] == 2
	end, "LSP definition did not win")
	keys("<C-o>")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 1, "LSP definition lost jump-back position")
	delayed = true
	keys(",cd")
	wait(function()
		return vim.api.nvim_buf_get_name(0) == target
	end, "Timed-out LSP did not fall back to tags")
	delayed(nil, { location(source, 1) })
	vim.wait(50)
	assert(vim.api.nvim_buf_get_name(0) == target, "Late definition moved the editor")
	keys("<C-o>")
	assert(vim.api.nvim_get_current_buf() == source_buf, "Tag jump lost return position")
	vim.lsp.get_client_by_id(transport):stop(true)
	wait(function()
		return #vim.lsp.get_clients({ bufnr = source_buf }) == 0
	end, "Fixture did not stop")
	local search
	fzf.grep = function(opts)
		search = opts
	end
	vim.api.nvim_win_set_cursor(0, { 2, 0 })
	keys(",cd")
	assert(
		search and search.search == "missing_symbol" and search.cwd == project,
		"Definition did not offer project text search"
	)
	print("Definition fallback workflow passed")

	-- Buffer symbols: LSP outline, then unsaved Tree-sitter definitions.
	local selected, title
	fzf.register_ui_select = function() end
	vim.ui.select = function(items, opts, choose)
		selected, title = items, opts.prompt
		choose(nil)
	end
	transport = server(project, function(method)
		assert(method == "textDocument/documentSymbol")
		return {
			{
				name = "server_outline",
				kind = 12,
				range = location(source).range,
				selectionRange = location(source).range,
			},
		}
	end)
	keys(",bs")
	wait(function()
		return title ~= nil
	end, "Buffer outline did not open")
	assert(
		title:find("LSP", 1, true) and selected[1].label:find("server_outline", 1, true),
		"Buffer symbols lost LSP names"
	)
	vim.lsp.get_client_by_id(transport):stop(true)
	wait(function()
		return #vim.lsp.get_clients({ bufnr = source_buf }) == 0
	end, "Outline fixture did not stop")
	vim.api.nvim_buf_set_lines(0, 0, -1, false, { "local function unsaved_outline() end", "unsaved_outline()" })
	title = nil
	keys(",bs")
	assert(title and title:find("Tree-sitter", 1, true), "Missing unsaved Tree-sitter outline")
	assert(selected[1].label:find("unsaved_outline", 1, true), "Outline omitted unsaved definition")
	assert(
		not table.concat(vim.fn.readfile(source), "\n"):find("unsaved_outline", 1, true),
		"Outline test unexpectedly saved file"
	)
	print("Buffer symbols workflow passed")
	vim.bo.modified = false

	-- Workspace symbols: query-aware LSP, then tags for a query the server
	-- cannot answer. The production content callback streams FzfLua entries.
	local reload, options
	fzf.fzf_live = function(contents, opts)
		reload, options = contents, opts
	end
	transport = server(project, function(method, params)
		assert(method == "workspace/symbol")
		if params.query == "server" then
			return { { name = "server_symbol", kind = 12, location = location(target) } }
		end
		return {}
	end)
	keys(",ws")
	local rows, complete = {}, false
	reload({ "server" })(function(row)
		if row then
			table.insert(rows, row)
		else
			complete = true
		end
	end)
	wait(function()
		return complete
	end, "Workspace LSP query did not complete")
	assert(rows[1] and rows[1]:find("[LSP] server_symbol", 1, true), "Workspace lost LSP result")
	rows, complete = {}, false
	reload({ "destination" })(function(row)
		if row then
			table.insert(rows, row)
		else
			complete = true
		end
	end)
	wait(function()
		return complete
	end, "Workspace tags fallback did not complete")
	assert(#rows == 1 and rows[1]:find("[Tags] destination", 1, true), "Workspace fallback lost query or tags")
	options.winopts.on_close()
	options.actions.default({ rows[1] })
	assert(vim.api.nvim_buf_get_name(0) == target, "Workspace selection did not jump")
	keys("<C-o>")
	print("Workspace symbols workflow passed")
	vim.lsp.get_client_by_id(transport):stop(true)
	wait(function()
		return #vim.lsp.get_clients({ bufnr = source_buf }) == 0
	end, "Workspace fixture did not stop")
	vim.api.nvim_buf_set_lines(0, 0, -1, false, { "destination()" })
	vim.api.nvim_win_set_cursor(0, { 1, 0 })
	transport = server(project, function(method, params)
		if method == "textDocument/references" then
			assert(params.context.includeDeclaration == false, "References included the declaration")
		else
			assert(method == "textDocument/implementation", "Implementation used the wrong LSP method")
		end
		return { location(target) }
	end)
	keys(",cr")
	wait(function()
		return vim.api.nvim_buf_get_name(0) == target
	end, "References did not use LSP")
	keys("<C-o>")
	keys(",cy")
	wait(function()
		return vim.api.nvim_buf_get_name(0) == target
	end, "Implementations did not use LSP")
	keys("<C-o>")
	vim.lsp.get_client_by_id(transport):stop(true)
	wait(function()
		return #vim.lsp.get_clients({ bufnr = source_buf }) == 0
	end, "Reference fixture did not stop")
	search = nil
	keys(",cr")
	assert(search and search.prompt:find("References · Text matches", 1, true), "References fallback was not labeled")
	search = nil
	keys(",cy")
	assert(
		search and search.prompt:find("Implementations · Text matches", 1, true),
		"Implementations fallback was not labeled"
	)
	print("References and implementations fallback workflow passed")

	-- Saving updates the same cached index; a second checkout uses another.
	vim.api.nvim_buf_set_lines(0, 0, -1, false, { "function saved_outline() end" })
	vim.cmd.write()
	wait(function()
		return #vim.fn.taglist("^saved_outline$") > 0
	end, "Saved file did not update tags")
	vim.bo.filetype = "navigation_fixture"
	title = nil
	keys(",bs")
	assert(title and title:find("Tags (saved)", 1, true), "Buffer symbols did not fall back to saved tags")
	assert(#selected == 1 and selected[1].label:find("saved_outline", 1, true), "Buffer tags escaped current file")
	local other = temp .. "/other checkout"
	command({
		"git",
		"-C",
		project,
		"-c",
		"user.name=Navigation Fixture",
		"-c",
		"user.email=fixture@example.invalid",
		"-c",
		"commit.gpgsign=false",
		"commit",
		"--allow-empty",
		"-qm",
		"test: initialize disposable navigation fixture",
	})
	command({ "git", "-C", project, "worktree", "add", "--detach", "-q", other })
	write(other .. "/other.lua", { "function other_symbol() end" })
	vim.cmd.edit(vim.fn.fnameescape(other .. "/other.lua"))
	wait(function()
		return #vim.fn.taglist("^other_symbol$") > 0
	end, "Worktree marker did not generate tags")
	assert(vim.fn.tagfiles()[1] ~= index, "Checkouts shared a tag cache")
	print("Background index workflow passed")

	-- Exercise the real FzfLua streaming boundary and terminal selection too.
	write(other .. "/caller.lua", { "other_symbol()" })
	vim.cmd.edit(vim.fn.fnameescape(other .. "/caller.lua"))
	fzf.fzf_live = live
	keys(",ws")
	wait(function()
		return vim.bo.buftype == "terminal"
			and table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n"):find("[Tags] other_symbol", 1, true)
	end, "Real workspace picker did not display streamed tag entries")
	vim.api.nvim_chan_send(vim.bo.channel, "other_symbol")
	vim.wait(400)
	vim.api.nvim_chan_send(vim.bo.channel, "\r")
	wait(function()
		return vim.bo.buftype ~= "terminal"
	end, "Real workspace picker did not accept selection")
	assert(vim.api.nvim_buf_get_name(0) == other .. "/other.lua", "Real workspace picker lost destination")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 1, "Real workspace picker lost destination row")
	print("Real FzfLua workspace picker passed")
	keys("<C-o>")
	assert(vim.api.nvim_buf_get_name(0) == other .. "/caller.lua", "Workspace jump lost its return position")
	fzf.grep = grep
	keys(",cr")
	wait(function()
		return vim.bo.buftype == "terminal"
			and table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n"):find("other_symbol", 1, true)
	end, "Real text fallback did not search project files")
	vim.api.nvim_chan_send(vim.bo.channel, "other.lua")
	vim.wait(400)
	vim.api.nvim_chan_send(vim.bo.channel, "\r")
	wait(function()
		return vim.bo.buftype ~= "terminal"
	end, "Real text fallback did not accept selection")
	assert(vim.api.nvim_buf_get_name(0) == other .. "/other.lua", "Text fallback selected the wrong file")
	print("Real FzfLua text fallback passed")
end

local ok, err = xpcall(workflow, debug.traceback)
vim.ui.select = select
fzf.register_ui_select, fzf.grep, fzf.fzf_live = register, grep, live
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
