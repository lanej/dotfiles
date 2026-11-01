-- Use the checkout's schema offline, including when editing machine files
-- outside a Git workspace or through the installed Neovim symlink.
local source = assert(vim.uv.fs_realpath(debug.getinfo(1, "S").source:sub(2)))
local root = vim.fs.dirname(vim.fs.dirname(vim.fs.dirname(source)))
local schema = vim.uri_from_fname(vim.fs.joinpath(root, "config/schema.json"))
local config_home = vim.env.XDG_CONFIG_HOME or vim.fn.expand("~/.config")

local function literal_uri(path)
	-- Taplo matches associations against percent-decoded document URIs.
	return vim.fn.escape(vim.uri_decode(vim.uri_from_fname(path)), "\\.^$|?*+(){}[]")
end

local associations = {}
local function directory(path)
	associations["^" .. literal_uri(path) .. "/(?:sets/)?[^/]+\\.toml$"] = schema
end
directory(vim.fs.joinpath(root, "config"))
directory(vim.fs.joinpath(config_home, "dotfiles"))
if vim.env.DOTFILES_CONFIG then
	local machine = vim.fs.normalize(vim.fn.expand(vim.env.DOTFILES_CONFIG))
	associations["^" .. literal_uri(machine) .. "$"] = schema
	directory(vim.fs.joinpath(vim.fs.dirname(machine), "sets"))
end

return {
	cmd = { "taplo", "lsp", "stdio" },
	filetypes = { "toml" },
	root_dir = function(bufnr, on_dir)
		local path = vim.api.nvim_buf_get_name(bufnr)
		on_dir(vim.fs.root(path, { ".taplo.toml", "taplo.toml", ".git" }) or vim.fs.dirname(path))
	end,
	settings = {
		evenBetterToml = {
			schema = {
				enabled = true,
				associations = associations,
			},
		},
	},
}
