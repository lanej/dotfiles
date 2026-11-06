-- A short-lived, account-specific snapshot; GitHub still owns review state.
local M = { ttl = 300 }

local function path(login, scope)
	if type(login) ~= "string" or not login:match("^[%w-]+$") then
		return nil
	end
	local suffix = scope and scope ~= "all" and "--" .. vim.fn.sha256(scope):sub(1, 20) or ""
	return vim.fn.stdpath("cache") .. "/pr-reviews/" .. login .. suffix .. ".json"
end

local function valid(record, login, scope)
	if
		type(record) ~= "table"
		or record.version ~= 1
		or record.login ~= login
		or record.scope ~= scope
		or type(record.fetchedAt) ~= "number"
		or type(record.prs) ~= "table"
		or type(record.errors) ~= "table"
	then
		return false
	end
	for _, pr in ipairs(record.prs) do
		if
			type(pr) ~= "table"
			or type(pr.id) ~= "string"
			or type(pr.number) ~= "number"
			or type(pr.title) ~= "string"
			or type(pr.body) ~= "string"
			or type(pr.url) ~= "string"
			or type(pr.headRefOid) ~= "string"
			or type(pr.createdAt) ~= "string"
			or not pr.createdAt:match("^%d+%-%d+%-%d+T%d+:%d+:%d+Z$")
			or type(pr.repository) ~= "table"
			or type(pr.repository.nameWithOwner) ~= "string"
			or (scope ~= "all" and pr.repository.nameWithOwner:lower() ~= scope)
			or (pr.author ~= vim.NIL and (type(pr.author) ~= "table" or type(pr.author.login) ~= "string"))
			or type(pr.sources) ~= "table"
			or type(pr.checks) ~= "table"
			or not vim.tbl_contains({ "passing", "pending", "failed", "missing", "unknown" }, pr.check_status)
		then
			return false
		end
		for _, source in ipairs(pr.sources) do
			if type(source) ~= "string" then
				return false
			end
		end
		for _, check in ipairs(pr.checks) do
			if
				type(check) ~= "table"
				or type(check.name or check.context) ~= "string"
				or type(check.state or check.status) ~= "string"
			then
				return false
			end
		end
	end
	for _, err in ipairs(record.errors) do
		if type(err) ~= "string" then
			return false
		end
	end
	return true
end

function M.read(login, scope)
	scope = scope or "all"
	local filename = path(login, scope)
	if not filename or vim.fn.filereadable(filename) ~= 1 then
		return
	end
	local ok, record = pcall(function()
		return vim.json.decode(table.concat(vim.fn.readfile(filename), "\n"))
	end)
	if ok and type(record) == "table" then
		record.scope = record.scope or "all"
	end
	return ok and valid(record, login, scope) and record or nil
end

function M.write(record)
	local filename = path(record.login, record.scope)
	if not filename then
		return "Invalid cache account"
	end
	local temporary = filename .. "." .. vim.fn.getpid() .. ".tmp"
	local ok, err = pcall(function()
		vim.fn.mkdir(vim.fs.dirname(filename), "p", 448)
		vim.fn.writefile({ vim.json.encode(record) }, temporary)
		assert(vim.fn.setfperm(temporary, "rw-------") == 1, "Cannot protect cache file")
		assert(vim.uv.fs_rename(temporary, filename))
	end)
	if not ok then
		vim.fn.delete(temporary)
		return tostring(err)
	end
end

function M.fresh(record, now)
	return record and now >= record.fetchedAt and now - record.fetchedAt < M.ttl
end

return M
