vim.opt.rtp:prepend(vim.fn.getcwd() .. "/nvim")
local api = require("beads.api")
local store = require("beads.store").new(vim.json.decode(vim.env.BEADS_TEST_SETTINGS))
local document = require("beads.document")
local done, failure
api.run(function()
	local root = { marker = "<!-- acceptance -->" }
	local fields = {
		title = "Native parent",
		description = "## Problem\nNative API compatibility",
		acceptance_criteria = "One child",
	}
	store:save(root, fields, document.render(fields, root.marker))
	assert(root.base.id and root.base.revision)
	local child = { parent = root.base.id, marker = "<!-- acceptance -->" }
	fields = { title = "Native child", description = "## Outcome\nEditable", acceptance_criteria = "Round trip" }
	store:save(child, fields, document.render(fields, child.marker))
	assert(store:edges({ child.base.id })[1].depends_on_id == root.base.id)
	local before = vim.deepcopy(child.base)
	fields.title = "Native child edited"
	store:save(child, fields, document.render(fields, child.marker))
	assert(store:get(child.base.id).title == fields.title)
	local stale = { base = before }
	local ok = pcall(store.save, store, stale, fields, {})
	assert(not ok, "Stale save must fail")
	local graph = store:list()
	assert(#graph.items == 2 and #graph.edges == 1)
	print("Native Beads mapping, atomic parent and revision checks passed")
end, function(err)
	failure, done = err, true
end)
assert(
	vim.wait(50000, function()
		return done
	end, 10),
	"Native API check timed out"
)
if failure then
	error(api.message(failure))
end
-- Exercise the public editor write path on claimed work; the runtime must reject its old brief.
local accepted
local child_id
local doc_done, doc_error
api.run(function()
	local graph = store:list()
	for _, item in ipairs(graph.items) do
		if item.title == "Native child edited" then
			child_id = item.id
		end
	end
	local before = store:get(assert(child_id))
	store.client:call("updateIssue", {
		path = { id = child_id },
		body = {
			actor = "pi:native-test",
			expected_version = before.revision,
			patch = {
				assignee = "pi:native-test",
				status = "in_progress",
				metadata = { merge = { ["pi.attempt"] = "native-test", unrelated = { preserved = true } } },
			},
		},
	})
	accepted = store:get(child_id)
end, function(err)
	doc_error, doc_done = err, true
end)
assert(vim.wait(15000, function()
	return doc_done
end, 10))
if doc_error then
	error(api.message(doc_error))
end
require("beads").setup({ projects = { native = vim.json.decode(vim.env.BEADS_TEST_SETTINGS) } })
vim.cmd("BeadsOpen " .. child_id)
assert(vim.wait(10000, function()
	return vim.b.beads_id == child_id
end, 10))
local buf = vim.api.nvim_get_current_buf()
vim.api.nvim_buf_set_lines(buf, 0, 1, false, { "# Claimed brief edited in Neovim" })
vim.cmd.write()
assert(vim.wait(15000, function()
	return not vim.b[buf].beads_saving
end, 10))
assert(not vim.b[buf].beads_error, vim.b[buf].beads_error)
assert(not vim.bo[buf].modified)
local verify_done, verify_error
api.run(function()
	local current = store:get(child_id)
	assert(current.assignee == accepted.assignee and current.metadata["pi.attempt"] == "native-test")
	assert(current.metadata.unrelated.preserved)
	assert(current.revision ~= accepted.revision and current.title ~= accepted.title)
	vim.fn.writefile(
		{ vim.json.encode({ accepted = accepted, revision = accepted.revision, attempt = "native-test" }) },
		vim.env.BEADS_TEST_RESULT
	)
end, function(err)
	verify_error, verify_done = err, true
end)
assert(vim.wait(10000, function()
	return verify_done
end, 10))
if verify_error then
	error(api.message(verify_error))
end
print("Native claimed-task editor save preserved ownership and changed the accepted revision")
