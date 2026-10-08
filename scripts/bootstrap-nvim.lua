-- Run after the real init.lua; wait for every installer before exiting headless.
local function install()
	require("lazy").install({ wait = true, show = false, lockfile = true })
	for name, plugin in pairs(require("lazy.core.config").plugins) do
		assert(plugin._.installed, "Neovim plugin missing: " .. name)
		assert(not require("lazy.core.plugin").has_errors(plugin), "Neovim plugin installation failed: " .. name)
	end

	require("treesitter")
	local languages = require("treesitter-parsers")
	local finished, success = require("nvim-treesitter").install(languages, { max_jobs = 4 }):pwait(300000)
	assert(finished and success, "Treesitter installation failed or timed out: " .. tostring(success))
	for _, language in ipairs(languages) do
		assert(vim.treesitter.language.add(language), "Treesitter parser unavailable: " .. language)
	end

	local registry = require("mason-registry")
	local refreshed, refresh_ok = false, false
	registry.refresh(function(ok)
		refreshed, refresh_ok = true, ok
	end)
	assert(vim.wait(60000, function()
		return refreshed
	end) and refresh_ok, "Mason registry refresh failed")
	local mappings = require("mason-lspconfig.mappings").get_mason_map().lspconfig_to_package
	local packages = {}
	for _, server in ipairs(require("mason-lspconfig.settings").current.ensure_installed) do
		local name, version = require("mason-core.package").Parse(server)
		assert(mappings[name], "Mason server unavailable: " .. name)
		local package = registry.get_package(mappings[name])
		packages[#packages + 1] = package
		if not package:is_installed() and not package:is_installing() then
			package:install({ version = version })
		end
	end
	assert(
		vim.wait(600000, function()
			for _, package in ipairs(packages) do
				if package:is_installing() then
					return false
				end
			end
			return true
		end),
		"Mason language-server installation timed out"
	)
	for _, package in ipairs(packages) do
		assert(package:is_installed(), "Mason language-server installation failed: " .. package.name)
	end
	assert(#vim.g.dotfiles_bootstrap_errors == 0, table.concat(vim.g.dotfiles_bootstrap_errors, "\n"))
	print(("Neovim ready: %d Treesitter parsers and %d language servers installed."):format(#languages, #packages))
end

local ok, error = xpcall(install, debug.traceback)
if not ok then
	io.stderr:write("Neovim bootstrap failed: " .. error .. "\n")
	vim.cmd("cquit 1")
else
	vim.cmd("qa")
end
