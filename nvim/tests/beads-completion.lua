-- Isolated command/completion scenario: no plugins, services, tokens or settings files.
vim.opt.rtp:prepend(vim.fn.getcwd() .. "/nvim")
vim.o.hidden = true
local messages = {}
vim.notify = function(message)
	messages[#messages + 1] = message
end
local calls = { new = 0, list = 0, get = 0, verify = 0, tokens = 0, requests = 0 }
local graphs = {
	alpha = { items = { { id = "a-z" }, { id = "a-a" }, { id = "literal[1]" } }, edges = {} },
	beta = { items = { { id = "b-z" }, { id = "b-a" } }, edges = {} },
	zeta = { items = {}, edges = {} },
}
-- Replace only the persistence boundary; use real api.run, command registration,
-- project resolution, refresh application and document creation.
package.loaded["beads.store"] = {
	new = function(settings)
		calls.new = calls.new + 1
		local name = settings.test_name
		return {
			scope = name,
			client = { verify = function()
				calls.verify = calls.verify + 1
			end },
			list = function()
				calls.list = calls.list + 1
				return vim.deepcopy(graphs[name])
			end,
			get = function(_, id)
				calls.get = calls.get + 1
				return { id = id, revision = "1", title = "Explicit ID", status = "open" }
			end,
		}
	end,
}
local readfile = vim.fn.readfile
vim.fn.readfile = function(...)
	calls.tokens = calls.tokens + 1
	error("Unexpected file/token read")
end
vim.system = function()
	calls.requests = calls.requests + 1
	error("Unexpected process/HTTP request")
end
local beads = require("beads")
local function eq(actual, expected)
	assert(vim.deep_equal(actual, expected), vim.inspect(actual) .. " != " .. vim.inspect(expected))
end
local function complete(line, expected)
	eq(vim.fn.getcompletion(line, "cmdline"), expected)
end
local function listing(expected)
	vim.cmd("BeadsProjects")
	eq(messages[#messages], "Beads: " .. expected)
end
local function passive(fn)
	local before = vim.deepcopy(calls)
	local bufs, wins = vim.api.nvim_list_bufs(), vim.api.nvim_list_wins()
	local buf, win = vim.api.nvim_get_current_buf(), vim.api.nvim_get_current_win()
	fn()
	eq(calls, before)
	eq(vim.api.nvim_list_bufs(), bufs)
	eq(vim.api.nvim_list_wins(), wins)
	eq(vim.api.nvim_get_current_buf(), buf)
	eq(vim.api.nvim_get_current_win(), win)
end
local function ids(expected, prefix, filtered)
	for _, command in ipairs({ "BeadsOpen", "BeadsNew" }) do
		complete(command .. " ", expected)
		complete(command .. " " .. (prefix or "missing"), filtered or {})
	end
end
beads.setup()
passive(function()
	listing("No projects configured. Set vim.g.beads.projects or call require('beads').setup({ projects = ... }).")
	complete("Beads ", {})
	ids({})
end)
beads.setup({ projects = { beta = { test_name = "beta", token_file = "/never/read/secret" } } })
passive(function()
	listing("Configured projects (* current):\n* beta")
	complete("Beads ", { "beta" })
	complete("Beads b", { "beta" })
	ids({})
end)
beads.setup({ projects = { zeta = { test_name = "zeta" }, alpha = { test_name = "alpha" } } })
passive(function()
	listing("Configured projects (* current):\n  alpha\n* beta\n  zeta")
	complete("Beads ", { "alpha", "beta", "zeta" })
	complete("Beads a", { "alpha" })
	complete("Beads et", {})
	ids({})
end)
-- Populate both caches without an explorer (and without any Nui render).
beads.refresh("alpha")
vim.cmd("BeadsRefresh") -- implicit active remains beta after all passive operations
assert(calls.list == 2)
passive(function()
	ids({ "b-a", "b-z" }, "b-a", { "b-a" })
end)
beads.setup({ default_project = "alpha" })
passive(function()
	listing("Configured projects (* current):\n* alpha\n  beta\n  zeta")
	ids({ "a-a", "a-z", "literal[1]" }, "literal[", { "literal[1]" })
end)
-- Real draft command creates document context; a later global default must not win.
vim.cmd("BeadsNew uncached-parent")
local alpha_doc = vim.api.nvim_get_current_buf()
eq(vim.b.beads_parent, "uncached-parent")
beads.setup({ default_project = "beta" })
passive(function()
	listing("Configured projects (* current):\n* alpha\n  beta\n  zeta")
	ids({ "a-a", "a-z", "literal[1]" }, "a-", { "a-a", "a-z" })
end)
local ordinary = vim.api.nvim_create_buf(true, false)
vim.api.nvim_set_current_buf(ordinary)
passive(function()
	ids({ "b-a", "b-z" }, "b-", { "b-a", "b-z" })
end)
-- Exercise actual explorer command/buffer ownership, but suppress only Nui render.
-- Full rendering remains an external pinned-Nui acceptance gate.
local ui = require("beads.ui")
local renders = 0
ui.render = function()
	renders = renders + 1
end
vim.cmd("Beads alpha")
local alpha_tree = vim.api.nvim_get_current_buf()
assert(vim.api.nvim_buf_get_name(alpha_tree) == "beads-tree://alpha")
assert(renders > 0 and calls.list == 3)
beads.setup({ default_project = "beta" })
passive(function()
	listing("Configured projects (* current):\n* alpha\n  beta\n  zeta")
	ids({ "a-a", "a-z", "literal[1]" }, "a-z", { "a-z" })
end)
vim.api.nvim_set_current_buf(ordinary)
passive(function()
	listing("Configured projects (* current):\n  alpha\n* beta\n  zeta")
	ids({ "b-a", "b-z" })
end)
vim.api.nvim_set_current_buf(alpha_doc)
passive(function()
	ids({ "a-a", "a-z", "literal[1]" })
end)
-- Completion suggestions never constrain manually supplied IDs.
vim.cmd("BeadsOpen uncached-task")
eq(vim.b.beads_id, "uncached-task")
eq(vim.b.beads_project, "alpha")
assert(calls.get == 1 and calls.verify == 1)
vim.api.nvim_set_current_buf(ordinary)
beads.setup({ default_project = "zeta" })
passive(function()
	ids({})
	listing("Configured projects (* current):\n  alpha\n  beta\n* zeta")
end)
vim.cmd("BeadsRefresh")
assert(calls.list == 4)
passive(function()
	ids({})
end)
eq(calls, { new = 3, list = 4, get = 1, verify = 1, tokens = 0, requests = 0 })
-- Check the actual startup source ordering, not a fictional Lazy command loader.
-- Full disposable init.lua startup and keyboard Tab remain separate external gates.
local startup = table.concat(readfile("nvim/init.lua"), "\n")
local registration = assert(startup:find('require("beads").setup(vim.g.beads or {})', 1, true))
assert(registration < assert(startup:find('require("lazy").setup', 1, true)))
print("Beads isolated command/completion acceptance passed")
