-- Running servers show only their colored language glyph.
local M = require("lualine.component"):extend()
local devicons = require("nvim-web-devicons")
local state = require("lsp-status-state")

local server_filetypes = {
	bashls = "sh",
	bqls = "sql",
	dockerls = "dockerfile",
	docker_compose_language_service = "yaml",
	eslint = "javascript",
	tsserver = "typescript",
	ts_ls = "typescript",
	vtsls = "typescript",
}

function M:init(options)
	M.super.init(self, options)
	self.language_highlights = {}
	self.boot_highlight = self:create_hl({ fg = "#ebcb8b" }, "boot")
	self.error_highlight = self:create_hl({ fg = "#bf616a" }, "error")
end

function M:update_status()
	local result, processed = {}, {}
	local function append(client, failed)
		if not processed[client.name] and not vim.list_contains(self.options.ignore_lsp or {}, client.name) then
			local filetypes = client.config.filetypes or {}
			local ft = server_filetypes[client.name] or filetypes[1] or vim.bo.filetype
			if not server_filetypes[client.name] and vim.list_contains(filetypes, vim.bo.filetype) then
				ft = vim.bo.filetype
			end
			-- Compound filetypes such as sql.bigquery share their base language icon.
			local icon, color = devicons.get_icon_color_by_filetype(ft:match("^[^.]+"), { default = true })
			if not self.language_highlights[color] then
				self.language_highlights[color] = self:create_hl({ fg = color }, "language_" .. ft)
			end
			local item = self:format_hl(self.language_highlights[color]) .. icon
			if failed then
				item = item .. " " .. self:format_hl(self.error_highlight) .. "󰅚"
			elseif not client.initialized then
				item = item .. " " .. self:format_hl(self.boot_highlight) .. "󰔟"
			end
			result[#result + 1] = item .. self:get_default_hl()
			processed[client.name] = true
		end
	end
	local buf = vim.api.nvim_get_current_buf()
	for _, client in ipairs(vim.lsp.get_clients({ bufnr = buf, _uninitialized = true })) do
		append(client, state.failed(client))
	end
	for _, client in pairs(state.for_buffer(buf)) do
		append(client, true)
	end

	return table.concat(result, "  ")
end

return M
