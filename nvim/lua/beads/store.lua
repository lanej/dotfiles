local api = require("beads.api")
local document = require("beads.document")
local M = {}

local function write_receipt(path, value)
	vim.fn.mkdir(vim.fs.dirname(path), "p", "0700")
	local temp = path .. "." .. document.token()
	local fd = assert(vim.uv.fs_open(temp, "wx", 384))
	local bytes = vim.json.encode(value)
	local written, err = vim.uv.fs_write(fd, bytes, 0)
	if written ~= #bytes then
		vim.uv.fs_close(fd)
		vim.uv.fs_unlink(temp)
		error(err or "Could not persist the entire Beads recovery receipt")
	end
	assert(vim.uv.fs_fsync(fd))
	vim.uv.fs_close(fd)
	assert(vim.uv.fs_rename(temp, path))
end

function M.new(settings)
	local store = { client = api.new(settings), settings = settings }
	store.receipts = settings.state_dir or vim.fn.stdpath("state") .. "/beads"
	store.scope = vim.fn.sha256(store.client.origin .. "\n" .. settings.project_id)

	function store:get(id)
		local task = self.client:call("getIssue", { path = { id = id } })
		assert(
			task.id == id and type(task.revision) == "string" and task.revision ~= "",
			"Beads returned an unexpected identity or revision"
		)
		return task
	end

	function store:edges(ids)
		if #ids == 0 then
			return {}
		end
		local result = self.client:call("listDependencies", { query = { issue_id = ids } })
		assert(#result.missing == 0, "Beads graph changed while reading relationships; refresh")
		return result.items
	end

	function store:list()
		self.client:verify()
		local items, cursor, cursors, seen = {}, nil, {}, {}
		repeat
			local page = self.client:call("listIssues", { query = { all = true, limit = 1000, cursor = cursor } })
			for _, task in ipairs(page.items) do
				assert(not seen[task.id], "Beads graph changed while paging; refresh")
				seen[task.id] = true
				items[#items + 1] = task
			end
			cursor = page.has_more and page.next_cursor or nil
			assert(
				not page.has_more or type(cursor) == "string" and cursor ~= "" and not cursors[cursor],
				"Beads returned incomplete pagination"
			)
			if cursor then
				cursors[cursor] = true
			end
		until not cursor
		local edges = {}
		for offset = 1, #items, 100 do
			local ids = {}
			for index = offset, math.min(offset + 99, #items) do
				ids[#ids + 1] = items[index].id
			end
			vim.list_extend(edges, self:edges(ids))
		end
		return { items = items, edges = edges }
	end

	function store:pending()
		local result = {}
		for _, path in ipairs(vim.fn.glob(self.receipts .. "/" .. self.scope .. "-*.json", false, true)) do
			local ok, receipt = pcall(vim.json.decode, table.concat(vim.fn.readfile(path), "\n"))
			assert(ok, "Unreadable Beads recovery receipt: " .. path)
			if receipt.project_id == settings.project_id and receipt.origin == self.client.origin then
				result[#result + 1] = { path = path, receipt = receipt }
			end
		end
		return result
	end

	function store:reconcile(doc)
		local receipt = assert(doc.pending, "No pending creation")
		self.client:verify()
		local current = self:get(receipt.target)
		assert(
			(current.metadata or {})["nvim.create"] == receipt.token,
			"Pending task has a different creation marker; inspect manually"
		)
		local parent
		for _, edge in ipairs(self:edges({ current.id })) do
			if edge.type == "parent-child" then
				assert(not parent, "Pending task has multiple parents; inspect manually")
				parent = edge.depends_on_id
			end
		end
		assert(parent == receipt.parent, "Pending task's parent changed; inspect manually")
		assert(
			document.same(current, receipt.fields),
			"Pending task was edited remotely; compare it with the retained draft before recovery"
		)
		doc.base = current
		doc.pending = nil
		assert(vim.uv.fs_unlink(doc.receipt_path))
		return current
	end

	function store:save(doc, fields, lines)
		self.client:verify()
		if doc.pending then
			return self:reconcile(doc), doc.pending_fields or fields
		end
		if doc.base then
			local before = doc.base
			local result = self.client:call("updateIssue", {
				path = { id = before.id },
				body = {
					actor = settings.actor or "nvim",
					expected_version = before.revision,
					expected_status = assert(before.status),
					expected_assignee = before.assignee or "",
					force_close_policy = false,
					force_assignee_transfer = false,
					patch = fields,
				},
			})
			assert(
				type(result.revision) == "string" and result.revision ~= "",
				"Beads did not confirm the saved revision"
			)
			doc.base = vim.tbl_extend("force", before, fields, { revision = result.revision })
			return doc.base, fields
		end
		local prefix = settings.prefix
		if not prefix then
			prefix = self.client:call("getSetting", { path = { key = "issue_prefix" } }).value
		end
		assert(
			type(prefix) == "string" and prefix:match("^[%w_%-]+$") and #prefix < 100,
			"Configure the Beads workspace prefix before creating tasks"
		)
		local token = document.token()
		local receipt = {
			origin = self.client.origin,
			project_id = settings.project_id,
			target = prefix .. "-" .. token,
			token = token,
			fields = fields,
			parent = doc.parent,
			lines = lines,
			marker = doc.marker,
		}
		doc.receipt_path = self.receipts .. "/" .. self.scope .. "-" .. token .. ".json"
		write_receipt(doc.receipt_path, receipt)
		doc.pending, doc.pending_fields = receipt, fields
		local items = {
			{
				kind = "create",
				create = vim.tbl_extend("force", fields, {
					key = "draft",
					id = receipt.target,
					issue_type = "task",
					ephemeral = false,
					no_history = false,
					metadata = { ["nvim.create"] = token },
				}),
			},
		}
		if doc.parent then
			items[#items + 1] = {
				kind = "dep_add",
				dep_add = { source = { key = "draft" }, target = { id = doc.parent }, type = "parent-child" },
			}
		end
		local ok, result = pcall(self.client.call, self.client, "applyBatch", {
			body = {
				actor = settings.actor or "nvim",
				items = items,
				force_id_prefix = false,
				skip_per_edge_cycle_check = false,
			},
		})
		if not ok then
			-- These statuses contractually refuse the entire batch before committing.
			if type(result) == "table" and vim.tbl_contains({ 400, 401, 403, 404, 409, 422 }, result.status) then
				assert(vim.uv.fs_unlink(doc.receipt_path))
				doc.pending = nil
			end
			error(result, 0)
		end
		assert(
			result.keys.draft == receipt.target,
			"Beads did not confirm the intended identity; reconcile pending creation"
		)
		return self:reconcile(doc), fields
	end
	return store
end

return M
