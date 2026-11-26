local spec, root, lockfile = unpack(arg)
vim.o.loadplugins = true
vim.opt.runtimepath:prepend(root .. "/lazy.nvim")
require("lazy").setup({
	spec = { dofile(spec) },
	root = root,
	lockfile = lockfile,
	install = { missing = false },
	change_detection = { enabled = false },
	headless = { process = false, colors = false },
	pkg = { enabled = false },
})
local plugin = require("lazy.core.config").plugins.copydesk
local action = plugin._.installed and "restore" or "install"
require("lazy")[action]({ plugins = { "copydesk" }, wait = true, show = false, lockfile = true })
assert(not require("lazy.core.plugin").has_errors(plugin), "Lazy could not install the locked Copydesk revision")
vim.cmd("qa")
