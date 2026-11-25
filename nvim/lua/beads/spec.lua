local source = debug.getinfo(1, "S").source:sub(2)

return {
	name = "beads",
	dir = vim.fn.fnamemodify(source, ":p:h:h:h"),
	main = "beads",
	cmd = {
		"Beads",
		"BeadsProjects",
		"BeadsOpen",
		"BeadsNew",
		"BeadsRefresh",
		"BeadsStatus",
		"BeadsRelationships",
		"BeadsRecover",
		"BeadsReload",
	},
	dependencies = { "MunifTanjim/nui.nvim" },
	opts = function()
		return vim.g.beads or {}
	end,
}
