vim.opt.rtp:prepend(vim.fn.getcwd() .. "/nvim")
vim.opt.rtp:append(assert(vim.env.NVIM_TEST_NUI))
vim.opt.rtp:append(assert(vim.env.NVIM_TEST_MARKVIEW))
vim.o.hidden = true
require("dotfiles-theme").setup()
-- Use the same settings as the editor, rather than a test-only renderer profile.
require("markview").setup(require("markview-config"))
vim.cmd("runtime plugin/markview.lua")
local settings = vim.json.decode(vim.env.BEADS_TEST_SETTINGS)
require("beads").setup({ projects = { trial = settings } })
vim.cmd("BeadsOpen trial-child")
assert(vim.wait(5000, function()
	return vim.b.beads_id == "trial-child"
end, 10))
local buf = vim.api.nvim_get_current_buf()
local raw = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
local fields = require("beads.document").parse(raw, raw[3])
assert(raw[4] == "## Acceptance criteria")
assert(
	vim.wait(5000, function()
		return require("markview.state").buf_attached(buf)
	end, 10),
	"Markview did not attach to the editable task"
)
vim.cmd("Markview render")
local ns = assert(vim.api.nvim_get_namespaces()["markview/markdown"])
assert(#vim.api.nvim_buf_get_extmarks(buf, ns, 0, -1, {}) > 0, "Markview did not render the actual Markdown headings")
assert(vim.deep_equal(raw, vim.api.nvim_buf_get_lines(buf, 0, -1, false)), "Rendering changed authored text")
local context =
	vim.api.nvim_buf_get_extmarks(buf, vim.api.nvim_get_namespaces()["beads-context"], 0, -1, { details = true })
for _, mark in ipairs(context) do
	assert(not mark[4].hl_group, "Beads is still overriding Markdown heading styling")
end
vim.api.nvim_buf_set_lines(buf, 0, 1, false, { "# Markview-rendered task" })
vim.cmd.write()
assert(vim.wait(5000, function()
	return not vim.b[buf].beads_saving
end, 10))
assert(not vim.b[buf].beads_error, vim.b[buf].beads_error)
assert(not vim.bo[buf].modified)
local api = require("beads.api")
local completed, failure
api.run(function()
	local store = require("beads.store").new(settings)
	store.client:verify()
	local remote = store:get("trial-child")
	assert(remote.title == "Markview-rendered task")
	assert(remote.description == fields.description and remote.acceptance_criteria == fields.acceptance_criteria)
end, function(err)
	failure, completed = err, true
end)
assert(vim.wait(5000, function()
	return completed
end, 10))
if failure then
	error(api.message(failure))
end
print("Markview rendered the normal task Markdown without changing persistence fields")
