local M = {}
local source = vim.fn.resolve(debug.getinfo(1, "S").source:sub(2))
local generated = vim.env.DOTFILES_THEME_DIR or (vim.fn.fnamemodify(source, ":h:h:h") .. "/design-system/generated")

function M.lualine()
	return dofile(generated .. "/lualine.lua")
end

function M.colors()
	return dofile(generated .. "/neovim.lua").roles
end

function M.apply()
	local theme = dofile(generated .. "/neovim.lua")
	for name, style in pairs(theme.highlights) do
		vim.api.nvim_set_hl(0, name, style)
	end
	for index, color in ipairs(theme.ansi) do
		vim.g["terminal_color_" .. (index - 1)] = color
	end
	-- WHY: Lualine caches its native theme independently of highlight groups.
	if package.loaded["lualine"] then
		require("lualine").setup({ options = { theme = M.lualine() } })
	end
end

function M.setup()
	local pending = false
	vim.api.nvim_create_autocmd("User", {
		group = vim.api.nvim_create_augroup("DotfilesTheme", { clear = true }),
		pattern = { "LazyLoad", "VeryLazy" },
		callback = function()
			if pending then
				return
			end
			pending = true
			vim.schedule(function()
				pending = false
				if vim.g.colors_name == "dotfiles" then
					M.apply()
				end
			end)
		end,
	})
	vim.cmd.colorscheme("dotfiles")
end

return M
