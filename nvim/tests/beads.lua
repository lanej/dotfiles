vim.opt.rtp:prepend(vim.fn.getcwd() .. "/nvim")
vim.opt.rtp:append(assert(vim.env.NVIM_TEST_NUI, "Set NVIM_TEST_NUI to the locked nui.nvim checkout"))
vim.o.hidden = true
require("dotfiles-theme").setup()
local settings = vim.json.decode(vim.env.BEADS_TEST_SETTINGS)
local beads = require("beads")
local messages = {}
vim.notify = function(message)
	messages[#messages + 1] = message
end
beads.setup({ projects = { trial = settings } })
local function wait(predicate, label)
	assert(vim.wait(8000, predicate, 10), (label or "Timed out") .. "\n" .. table.concat(messages, "\n"))
end
local function control(body)
	local result = vim.system({
		"curl",
		"--disable",
		"-sS",
		"--header",
		"Bd-Project-Id: " .. settings.project_id,
		"--header",
		"Content-Type: application/json",
		"--data-binary",
		"@-",
		settings.url .. "/control",
	}, { stdin = vim.json.encode(body or vim.empty_dict()), text = true }):wait()
	assert(result.code == 0)
	return vim.json.decode(result.stdout)
end
local function save(buf)
	vim.api.nvim_set_current_buf(buf)
	vim.cmd.write()
	wait(function()
		return not vim.b[buf].beads_saving
	end, "Save did not settle")
end
local function title(buf, text)
	vim.api.nvim_buf_set_lines(buf, 0, 1, false, { "# " .. text })
end
local function open(id)
	vim.cmd("BeadsOpen " .. id)
	wait(function()
		return vim.b.beads_id == id
	end, "Task did not open")
	return vim.api.nvim_get_current_buf()
end

vim.cmd("Beads trial")
local tree_buf, tree_win = vim.api.nvim_get_current_buf(), vim.api.nvim_get_current_win()
local function tree_lines()
	return table.concat(vim.api.nvim_buf_get_lines(tree_buf, 0, -1, false), "\n")
end
wait(function()
	return tree_lines():find("Parent")
end, "Tree did not load")
assert(not tree_lines():find("Child"), "Children should start collapsed")
local function node(id)
	vim.api.nvim_set_current_win(tree_win)
	for index, line in ipairs(vim.api.nvim_buf_get_lines(tree_buf, 0, -1, false)) do
		if line:find(id, 1, true) then
			vim.api.nvim_win_set_cursor(tree_win, { index, 0 })
			return
		end
	end
	error("Missing tree node " .. id)
end
local function key(keys)
	vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes(keys, true, false, true), "xt", false)
end
node("Parent")
key("l")
assert(tree_lines():find("Child"), "Expand must reveal child")
key("j")
vim.cmd("doautocmd CursorMoved")
assert(vim.b[tree_buf].beads_selection == "trial-child", "Selection did not follow the keyboard")
key("h")
assert(vim.b[tree_buf].beads_selection == "trial-root", "Parent navigation lost identity")
control({ list_fail = true })
vim.cmd.BeadsRefresh()
wait(function()
	return tree_lines():find("stale")
end, "Refresh failure is invisible")
assert(tree_lines():find("Child"), "Refresh failure discarded the retained tree")
control({ list_fail = false })
key("r")
wait(function()
	return not tree_lines():find("stale")
end)
-- Check the actual Nui-rendered spans and selection, rather than source color declarations.
local colors = require("dotfiles-theme").colors()
assert(
	vim.api.nvim_get_hl(0, { name = "BeadsBlocked", link = false }).fg == tonumber(colors["status.error"]:sub(2), 16)
)
assert(vim.api.nvim_get_hl(0, { name = "BeadsProgress", link = false }).bold)
assert(vim.wo[tree_win].cursorline and vim.wo[tree_win].winfixwidth)
local spans =
	vim.api.nvim_buf_get_extmarks(tree_buf, vim.api.nvim_get_namespaces()["beads-sidebar"], 0, -1, { details = true })
local semantic
for _, span in ipairs(spans) do
	if span[4].hl_group == "BeadsProgress" then
		semantic = true
	end
end
assert(semantic, "Active-task icon has no semantic color")
local initial_width = vim.api.nvim_win_get_width(tree_win)
vim.api.nvim_win_set_width(tree_win, 26)
vim.cmd("doautocmd WinResized")
assert(not tree_lines():find("A task title that expands with the pane", 1, true))
vim.api.nvim_win_set_width(tree_win, 52)
vim.cmd("doautocmd WinResized")
assert(
	tree_lines():find("A task title that expands with the pane", 1, true),
	"Enlarging the tree did not restore its titles"
)
vim.api.nvim_win_set_width(tree_win, initial_width)
vim.cmd("doautocmd WinResized")
vim.cmd.colorscheme("default")
assert(vim.api.nvim_get_hl(0, { name = "BeadsBlocked", link = false }).fg, "Colorscheme reload removed Beads colors")
vim.cmd.colorscheme("dotfiles")
local child = open("trial-child")
assert(vim.bo[child].buftype == "acwrite" and vim.bo[child].filetype == "markdown")
assert(vim.wo.linebreak and vim.wo.breakindent, "Briefs should wrap at word boundaries")
vim.cmd.enew()
assert(not vim.wo.linebreak and not vim.wo.breakindent, "Task appearance leaked into an ordinary buffer")
assert(open("trial-child") == child)
local first_name = vim.api.nvim_buf_get_name(child)
vim.cmd.tabnew()
assert(open("trial-child") == child, "Task opening must reuse the buffer across tabs")
vim.cmd.tabclose()
vim.api.nvim_set_current_buf(child)
local marker = vim.api.nvim_buf_get_lines(child, 0, -1, false)[3]
local lines = {
	"# Child edited",
	"## Problem",
	"Existing arbitrary headings",
	"```markdown",
	"## Acceptance criteria",
	"```",
	"",
	marker,
	"- [ ] Native task fields",
}
vim.api.nvim_buf_set_lines(child, 0, -1, false, lines)
save(child)
assert(not vim.b[child].beads_error, table.concat(messages, "\n"))
assert(not vim.bo[child].modified and vim.api.nvim_buf_get_name(child) == first_name)
local snapshot = control()
local remote = snapshot.tasks["trial-child"]
assert(remote.description == table.concat(lines, "\n", 2, 7))
assert(remote.acceptance_criteria == "- [ ] Native task fields")
assert(remote.assignee == "pi:owner-attempt" and remote.metadata["pi.attempt"] == "owner-attempt")
assert(remote.metadata.arbitrary.keep[2] == true)
-- Server revision changes must not be silently adopted by refresh or save.
control({ edit = "trial-child" })
title(child, "Local conflicting edit")
local dirty = vim.api.nvim_buf_get_lines(child, 0, -1, false)
local focus = vim.api.nvim_get_current_win()
vim.cmd.BeadsRefresh()
vim.wait(100)
assert(vim.api.nvim_get_current_win() == focus)
assert(vim.deep_equal(vim.api.nvim_buf_get_lines(child, 0, -1, false), dirty))
save(child)
assert(
	vim.b[child].beads_error and vim.b[child].beads_error:find("409") and vim.bo[child].modified,
	"Stale save must fail and retain local edits"
)
assert(control().tasks["trial-child"].title == "Remote edit")
-- Relations navigate independently from nesting.
local relationship
vim.ui.select = function(items, _, callback)
	for _, item in ipairs(items) do
		if item.id == "trial-blocker" then
			relationship = item
			callback(item)
			return
		end
	end
	callback(items[1])
end
vim.cmd.BeadsRelationships()
wait(function()
	return relationship ~= nil and vim.b.beads_id == "trial-blocker"
end)
assert(relationship.label:find("blocks"))
local blocker = vim.api.nvim_get_current_buf()
control({ mode = "delay" })
title(blocker, "Submitted title")
vim.cmd.write()
vim.defer_fn(function()
	title(blocker, "Newer local title")
end, 40)
wait(function()
	return not vim.b[blocker].beads_saving
end)
assert(vim.bo[blocker].modified and control().tasks["trial-blocker"].title == "Submitted title")
save(blocker)
assert(not vim.bo[blocker].modified and control().tasks["trial-blocker"].title == "Newer local title")
-- Explicit child creation binds one identity; repeated writes update it.
vim.cmd("BeadsNew trial-root")
local draft = vim.api.nvim_get_current_buf()
assert(not vim.b[draft].beads_id and vim.bo[draft].modified)
title(draft, "Created child")
save(draft)
assert(not vim.b[draft].beads_error, table.concat(messages, "\n"))
local created = vim.b[draft].beads_id
assert(created and not vim.bo[draft].modified)
save(draft)
assert(control().creates == 1)
local parent_found
for _, edge in ipairs(control().edges) do
	if edge.issue_id == created and edge.type == "parent-child" then
		parent_found = edge.depends_on_id
	end
end
assert(parent_found == "trial-root")
-- Malformed documents are retained and never written.
local writes = control().writes
vim.api.nvim_buf_set_lines(draft, 0, -1, false, { "Invalid title" })
save(draft)
assert(vim.bo[draft].modified and vim.b[draft].beads_error and control().writes == writes)
-- Reload requires an explicit discard and obtains a new authoritative base.
vim.cmd.BeadsReload()
assert(vim.bo[draft].modified, "Reload without bang discarded edits")
vim.cmd("BeadsReload!")
wait(function()
	return not vim.bo[draft].modified
end)
assert(vim.api.nvim_buf_get_lines(draft, 0, 1, false)[1] == "# Created child")
local previous_revision = vim.b[draft].beads_revision
vim.cmd("BeadsStatus closed")
wait(function()
	return vim.b[draft].beads_revision ~= previous_revision
end)
wait(function()
	return control().tasks[created].status == "closed"
end)
previous_revision = vim.b[draft].beads_revision
vim.cmd("BeadsStatus open")
wait(function()
	return vim.b[draft].beads_revision ~= previous_revision
end)
wait(function()
	return control().tasks[created].status == "open"
end)
-- A configured foreign project must fail before creating or updating tasks.
local count = control().creates
beads.setup({
	projects = { foreign = vim.tbl_extend("force", settings, { project_id = "22222222-2222-4222-8222-222222222222" }) },
})
vim.cmd("Beads foreign")
local foreign = vim.api.nvim_get_current_buf()
vim.wait(100)
assert(
	control().creates == count
		and not table.concat(vim.api.nvim_buf_get_lines(foreign, 0, -1, false), "\n"):find("trial%-root")
)
vim.api.nvim_set_current_buf(draft)
-- Lost outcomes reconcile, and ambiguous evidence never causes another create.
for _, mode in ipairs({ "lost", "lost-missing", "lost-mismatch", "lost-remote", "lost-unavailable" }) do
	vim.cmd("BeadsNew trial-root")
	local pending = vim.api.nvim_get_current_buf()
	title(pending, "Pending " .. mode)
	control({ mode = mode })
	save(pending)
	assert(vim.b[pending].beads_pending and vim.bo[pending].modified)
	local creates = control().creates
	save(pending)
	assert(control().creates == creates, "Uncertain creation was replayed")
	if mode == "lost" then
		assert(vim.b[pending].beads_id and not vim.bo[pending].modified)
	else
		assert(vim.b[pending].beads_pending and vim.bo[pending].modified and vim.b[pending].beads_error)
	end
end
-- Recovery after document disposal uses the durable submitted snapshot.
vim.cmd("BeadsNew trial-root")
local pending = vim.api.nvim_get_current_buf()
title(pending, "Restart recovery")
control({ mode = "lost" })
save(pending)
local creates = control().creates
vim.cmd.bwipeout({ bang = true })
vim.ui.select = function(items, _, callback)
	for _, item in ipairs(items) do
		if item.receipt.fields.title == "Restart recovery" then
			callback(item)
			return
		end
	end
	error("Recovery receipt missing")
end
vim.cmd.BeadsRecover()
local recovered = vim.api.nvim_get_current_buf()
assert(vim.bo[recovered].modified and not vim.b[recovered].beads_id)
save(recovered)
assert(vim.b[recovered].beads_id and not vim.bo[recovered].modified and control().creates == creates)
-- Closing the explorer neither commits nor removes dirty document buffers.
vim.api.nvim_set_current_win(tree_win)
vim.api.nvim_win_close(tree_win, false)
assert(vim.api.nvim_buf_is_valid(child) and vim.bo[child].modified)
assert(vim.deep_equal(vim.api.nvim_buf_get_lines(child, 0, -1, false), dirty))
vim.cmd("BeadsNew trial-root")
local restart = vim.api.nvim_get_current_buf()
title(restart, "Restart actual")
control({ mode = "lost" })
save(restart)
assert(vim.b[restart].beads_pending)
print("Beads editor acceptance passed")
