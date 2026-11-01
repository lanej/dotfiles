-- Exercise the configured Taplo server through Neovim's native LSP client.
local root = vim.fn.getcwd()
vim.opt.rtp:append(root .. "/nvim")
local temporary = vim.fn.tempname() .. " (TOML editing)"
vim.fn.mkdir(temporary .. "/real-config", "p")
local config_home = temporary .. "/linked-config"
assert(vim.uv.fs_symlink(assert(vim.uv.fs_realpath(temporary .. "/real-config")), config_home))
vim.env.XDG_CONFIG_HOME = config_home
vim.env.XDG_CACHE_HOME = temporary .. "/cache"
vim.env.XDG_STATE_HOME = temporary .. "/state"
vim.env.XDG_DATA_HOME = temporary .. "/data"
vim.env.DOTFILES_CONFIG = nil
vim.env.TAPLO_CONFIG = nil
local client_id

local function workflow()
	local machine = config_home .. "/dotfiles/config.toml"
	vim.fn.mkdir(vim.fs.dirname(machine), "p")
	vim.fn.writefile({
		'sets = ["easypost"]',
		"[codex]",
		'github_enabled = "false"',
		"[zellij]",
		'source = "invalid"',
		"typo = true",
	}, machine)
	local config = dofile(root .. "/nvim/lua/lspconfig-spec.lua").opts.servers.taplo
	-- The checkout's local schema works without network catalogs or user state.
	config.settings.evenBetterToml.schema.catalogs = {}
	vim.lsp.config("taplo", config)
	vim.lsp.enable("taplo")
	vim.cmd("filetype on")
	vim.cmd.edit(vim.fn.fnameescape(assert(vim.uv.fs_realpath(machine))))
	local buffer = vim.api.nvim_get_current_buf()
	assert(vim.bo[buffer].filetype == "toml", "Machine configuration did not receive TOML filetype")
	assert(vim.wait(15000, function()
		local clients = vim.lsp.get_clients({ bufnr = buffer, name = "taplo" })
		if #clients == 1 and clients[1].initialized then
			client_id = clients[1].id
			return true
		end
	end), "Configured Taplo did not attach to the machine configuration outside the checkout")

	local function error_lines()
		local lines = {}
		for _, diagnostic in ipairs(vim.diagnostic.get(buffer, { severity = vim.diagnostic.severity.ERROR })) do
			lines[diagnostic.lnum] = true
		end
		return lines
	end
	assert(
		vim.wait(15000, function()
			local lines = error_lines()
			return lines[2] and lines[4] and lines[5]
		end),
		"Missing inline type, enum, or unknown-property diagnostics: " .. vim.inspect(vim.diagnostic.get(buffer))
	)
	local client = assert(vim.lsp.get_client_by_id(client_id))
	local params = {
		textDocument = { uri = vim.uri_from_bufnr(buffer) },
		position = { line = 4, character = 10 },
	}
	local completion = assert(client:request_sync("textDocument/completion", params, 5000, buffer))
	assert(not completion.err, vim.inspect(completion.err))
	local labels = {}
	for _, item in ipairs(completion.result.items or completion.result) do
		labels[item.label:gsub('"', "")] = true
	end
	assert(
		labels.patched and labels.release and labels.main,
		"Runtime source completions missing: " .. vim.inspect(completion)
	)
	params.position.character = 2
	local hover = assert(client:request_sync("textDocument/hover", params, 5000, buffer))
	assert(
		vim.inspect(hover.result):find("Runtime source", 1, true),
		"Missing field documentation: " .. vim.inspect(hover)
	)

	vim.api.nvim_buf_set_lines(buffer, 0, -1, false, {
		'sets = ["easypost"]',
		"[codex]",
		"github_enabled = false",
		"[zellij]",
		'source = "main"',
	})
	assert(vim.wait(10000, function()
		return next(error_lines()) == nil
	end), "Inline diagnostics did not clear after repairing the configuration")
	vim.cmd("silent write")
	local runtime = vim.system({
		"python3",
		root .. "/scripts/dotfiles-config.py",
		"--config",
		machine,
		"--format",
		"json",
	}, { text = true }):wait()
	assert(runtime.code == 0, runtime.stderr)
	local resolved = vim.json.decode(runtime.stdout)
	assert(resolved.settings["zellij.source"] == "main" and resolved.settings["codex.github_enabled"] == false)
end

local ok, error = xpcall(workflow, debug.traceback)
if client_id then
	local client = vim.lsp.get_client_by_id(client_id)
	if client then
		client:stop(true)
	end
end
vim.fn.delete(temporary, "rf")
if not ok then
	io.stderr:write(error .. "\n")
	vim.cmd.cquit(1)
else
	print("PASS: TOML editing supplies inline diagnostics, source completion, documentation, and runtime-valid repairs.")
	vim.cmd("qa!")
end
