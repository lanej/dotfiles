-- Run the lifecycle through Neovim's real client and installed Lualine renderer:
-- nvim --headless -u NONE -i NONE -n -l nvim/tests/lsp-status.lua
vim.opt.rtp:append(vim.fn.getcwd() .. "/nvim")
local plugins = vim.fn.stdpath("data") .. "/lazy/"
vim.opt.rtp:append(plugins .. "lualine.nvim")
vim.opt.rtp:append(plugins .. "nvim-web-devicons")
vim.lsp.log.set_level("off")
require("lualine").setup({
	sections = {
		lualine_a = {},
		lualine_b = {},
		lualine_c = {},
		lualine_x = {
			{
				require("lsp-status"),
				icon = "",
				ignore_lsp = { "copilot", "GitHub Copilot", "null-ls" },
			},
		},
		lualine_y = {},
		lualine_z = {},
	},
})
local function workflow()
	vim.o.columns = 150
	vim.bo.filetype = "sql.bigquery"
	local buf = vim.api.nvim_get_current_buf()
	vim.api.nvim_buf_set_name(buf, vim.fn.tempname() .. ".bqsql")
	local transport, initialize
	local function server(dispatchers)
		transport = dispatchers
		local closing = false
		return {
			request = function(method, _, callback)
				if method == "initialize" then
					initialize = callback
				else
					callback(nil, {})
				end
				return true, 1
			end,
			notify = function()
				return true
			end,
			is_closing = function()
				return closing
			end,
			terminate = function()
				closing = true
				dispatchers.on_exit(0, 9)
			end,
		}
	end
	local lifecycle = require("lsp-status-state")
	local config = {
		name = "bqls",
		cmd = lifecycle.wrap_cmd(server),
		filetypes = { "sql.bigquery" },
		root_dir = vim.fs.dirname(vim.api.nvim_buf_get_name(buf)),
	}
	local icon, color = require("nvim-web-devicons").get_icon_color_by_filetype("sql")
	local function rendered()
		return vim.api.nvim_eval_statusline(require("lualine").statusline(true), {
			maxwidth = 150,
			highlights = true,
		})
	end
	local function glyph_color(glyph)
		local result = rendered()
		local byte = assert(result.str:find(glyph, 1, true)) - 1
		local group
		for _, highlight in ipairs(result.highlights) do
			if highlight.start <= byte then
				group = highlight.group
			end
		end
		return vim.api.nvim_get_hl(0, { name = group, link = false }).fg
	end

	local missing = vim.tbl_extend("force", config, {
		cmd = lifecycle.wrap_cmd({ vim.fn.tempname() .. "-missing-lsp" }),
	})
	assert(not vim.lsp.start(missing), "Missing executable unexpectedly started")
	assert(rendered().str:find(icon .. " 󰅚", 1, true), "Launch failure is missing its error glyph")
	local id = assert(vim.lsp.start(config))
	assert(rendered().str:find(icon .. " 󰔟", 1, true), "Booting server is missing its glyph pair")
	assert(glyph_color("󰔟") == tonumber("ebcb8b", 16), "Boot glyph is not yellow")
	initialize(nil, { capabilities = {} })
	assert(rendered().str:match("^%s*" .. icon .. "%s*$"), "Running server has extra text or status")
	assert(glyph_color(icon) == tonumber(color:sub(2), 16), "Language glyph lost its Webdevicons color")
	transport.on_error(vim.lsp.rpc.client_errors.INVALID_SERVER_MESSAGE, "fixture RPC error")
	assert(rendered().str:find(icon .. " 󰅚", 1, true), "RPC failure is missing its error glyph")
	assert(glyph_color("󰅚") == tonumber("bf616a", 16), "Error glyph is not red")
	transport.on_exit(1, 0)
	assert(
		vim.wait(1000, function()
			return not vim.lsp.get_client_by_id(id)
		end),
		"Exited client was not removed"
	)
	assert(rendered().str:find(icon .. " 󰅚", 1, true), "Crash indicator disappeared with the client")
	vim.cmd.enew()
	assert(not rendered().str:find("󰅚", 1, true), "Crash indicator leaked to another buffer")
	vim.cmd.buffer(buf)
	assert(rendered().str:find("󰅚", 1, true), "Crash indicator was lost on buffer switch")

	id = assert(vim.lsp.start(config))
	initialize(nil, { capabilities = {} })
	assert(rendered().str:match("^%s*" .. icon .. "%s*$"), "Restart did not clear the failure")
	vim.lsp.get_client_by_id(id):stop(true)
	assert(
		vim.wait(1000, function()
			return not vim.lsp.get_client_by_id(id)
		end),
		"Stopped client was not removed"
	)
	assert(rendered().str:match("^%s*$"), "Intentional stop was marked as an error")
end

local ok, err = xpcall(workflow, debug.traceback)
if not ok then
	io.stderr:write(err .. "\n")
	vim.cmd.cquit(1)
else
	io.stdout:write("LSP statusline: colored boot, running, error and restart workflow passed\n")
	vim.cmd("qa!")
end
