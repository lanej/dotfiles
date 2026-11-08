local M = {}
local source = vim.fn.resolve(debug.getinfo(1, "S").source:sub(2))
local generated = vim.env.DOTFILES_THEME_DIR or (vim.fn.fnamemodify(source, ":h:h:h") .. "/design-system/generated")
local applied_signs, applied_branch

function M.lualine()
	return dofile(generated .. "/lualine.lua")
end

function M.colors()
	return dofile(generated .. "/neovim.lua").roles
end

function M.tokens()
	return dofile(generated .. "/neovim.lua").tokens
end

function M.components()
	return dofile(generated .. "/neovim.lua").components
end

function M.signs(layer, components)
	local signs = {}
	local prefix = "git." .. layer .. "."
	for name, style in pairs(components or M.components()) do
		if name:sub(1, #prefix) == prefix then
			local glyph = style.symbol
			if vim.fn.strdisplaywidth(glyph) > 2 then
				error("Git gutter symbol exceeds two cells: " .. name)
			end
			signs[name:sub(#prefix + 1)] = { text = glyph }
		end
	end
	return signs
end

function M.lualine_options()
	local separators = dofile(generated .. "/neovim.lua").separators
	return { theme = M.lualine(), component_separators = separators.component, section_separators = separators.section }
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
		require("lualine").setup({ options = M.lualine_options() })
	end
	if package.loaded["gitsigns"] then
		local signs = { signs = M.signs("hunk", theme.components), signs_staged = M.signs("staged_hunk", theme.components) }
		if not vim.deep_equal(signs, applied_signs) then
			require("gitsigns").setup(signs)
			require("gitsigns").refresh()
			applied_signs = signs
		end
	end
	if package.loaded["git-branch-signs"] then
		local branch = M.signs("branch_hunk", theme.components)
		if not vim.deep_equal(branch, applied_branch) then
			for _, buf in ipairs(vim.api.nvim_list_bufs()) do
				require("git-branch-signs").refresh(buf)
			end
			applied_branch = branch
		end
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
