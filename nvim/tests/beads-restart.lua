vim.opt.rtp:prepend(vim.fn.getcwd() .. "/nvim")
local settings = vim.json.decode(vim.env.BEADS_TEST_SETTINGS)
local messages = {}
vim.notify = function(message)
	messages[#messages + 1] = message
end
require("beads").setup({ projects = { trial = settings } })
local function control()
	local response = vim.system({
		"curl",
		"--disable",
		"-sS",
		"--header",
		"Bd-Project-Id: " .. settings.project_id,
		"--data",
		"{}",
		settings.url .. "/control",
	}, { text = true }):wait()
	assert(response.code == 0)
	return vim.json.decode(response.stdout)
end
local creates = control().creates
for _, name in ipairs({
	"Pending lost-missing",
	"Pending lost-mismatch",
	"Pending lost-remote",
	"Pending lost-unavailable",
	"Restart actual",
}) do
	local found
	vim.ui.select = function(items, _, callback)
		for _, item in ipairs(items) do
			if item.receipt.fields.title == name then
				found = true
				callback(item)
				return
			end
		end
	end
	vim.cmd.BeadsRecover()
	assert(found, "Missing durable receipt " .. name)
	local buf = vim.api.nvim_get_current_buf()
	local text = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
	vim.cmd.write()
	assert(vim.wait(6000, function()
		return not vim.b[buf].beads_saving
	end, 10))
	assert(control().creates == creates, "Restart replayed an uncertain create")
	assert(vim.deep_equal(text, vim.api.nvim_buf_get_lines(buf, 0, -1, false)))
	if name == "Restart actual" then
		assert(vim.b[buf].beads_id and not vim.bo[buf].modified, table.concat(messages, "\n"))
	else
		assert(vim.bo[buf].modified and vim.b[buf].beads_error and not vim.b[buf].beads_id)
	end
end
print("Beads recovery survived a new Neovim process without duplicate creation or stale overwrite")
