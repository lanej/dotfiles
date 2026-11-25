vim.opt.rtp:prepend(vim.fn.getcwd() .. "/nvim")
vim.opt.rtp:prepend(vim.env.NVIM_TEST_NUI)
local settings = vim.json.decode(vim.env.BEADS_TEST_SETTINGS)
local state = vim.env.HOME .. "/.local/state/beads-service"
local messages = {}
vim.notify = function(message)
	messages[#messages + 1] = message
end
local function reported(text)
	return vim.wait(3000, function()
		return (messages[#messages] or ""):find(text, 1, true)
	end)
end

require("beads").setup()
vim.cmd.Beads()
assert(reported("No local Beads endpoint"), vim.inspect(messages))
vim.fn.mkdir(state, "p")
local endpoint = { url = settings.url, ready = true, workspace = state .. "/workspace", database = "different" }
vim.fn.writefile({ vim.json.encode(endpoint) }, state .. "/endpoint.json")
vim.cmd.Beads()
assert(reported("Beads context differs"), vim.inspect(messages))
assert(vim.fn.bufnr("beads-tree://different") == -1)

endpoint.database = "trial"
vim.fn.writefile({ vim.json.encode(endpoint) }, state .. "/endpoint.json")
vim.cmd.Beads()
assert(
	vim.wait(3000, function()
		return vim.b.beads_selection ~= nil
	end),
	vim.inspect(messages)
)
assert(vim.api.nvim_buf_get_name(0) == "beads-tree://trial")
vim.cmd("BeadsOpen trial-child")
assert(
	vim.wait(3000, function()
		return vim.b.beads_id == "trial-child"
	end),
	vim.inspect(messages)
)
print("Beads discovered the local project and opened a task with its project pin")
