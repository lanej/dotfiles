local contract = require("beads.generated")
local M = {}
local requests = {}
vim.api.nvim_create_autocmd("VimLeavePre", {
	callback = function()
		for path, process in pairs(requests) do
			if process ~= true then
				pcall(process.kill, process, 15)
			end
			vim.uv.fs_unlink(path)
		end
	end,
})

-- Yielding keeps HTTP off the editor thread while the caller owns one save transaction.
function M.run(fn, done)
	local thread = coroutine.create(function()
		local ok, value = pcall(fn)
		if ok then
			done(nil, value)
		else
			done(value)
		end
	end)
	local ok, err = coroutine.resume(thread)
	if not ok then
		done(err)
	end
end

local function await(start)
	local thread = coroutine.running()
	assert(thread, "Beads requests require an asynchronous operation")
	start(function(...)
		local args = { ... }
		vim.schedule(function()
			local ok, err = coroutine.resume(thread, unpack(args))
			if not ok then
				vim.notify(tostring(err), vim.log.levels.ERROR)
			end
		end)
	end)
	return coroutine.yield()
end

local function fail(message, status)
	error({ message = message, status = status }, 0)
end

function M.message(err)
	return type(err) == "table" and err.message or tostring(err)
end

-- Validate the generated structural contract locally; semantic constraints (including
-- regex/format rules and workspace policy) remain authoritative on the server.
local function validate(value, schema, label)
	if schema == true then
		return
	end
	if schema["$ref"] then
		return validate(value, contract.schemas[schema["$ref"]], label)
	end
	if value == vim.NIL and schema.nullable then
		return
	end
	local kind = schema.type
	local valid = kind == nil
		or (kind == "object" and type(value) == "table" and not vim.islist(value))
		or (kind == "array" and type(value) == "table" and vim.islist(value))
		or (kind == "integer" and type(value) == "number" and value % 1 == 0)
		or (kind == "number" and type(value) == "number")
		or kind == type(value)
	if not valid then
		fail(label .. " must be " .. tostring(kind))
	end
	if schema.enum and not vim.tbl_contains(schema.enum, value) then
		fail(label .. " is outside the API vocabulary")
	end
	if kind == "object" then
		for _, key in ipairs(schema.required or {}) do
			if value[key] == nil then
				fail(label .. "." .. key .. " is required")
			end
		end
		for key, item in pairs(value) do
			local child = (schema.properties or {})[key]
			if child then
				validate(item, child, label .. "." .. key)
			elseif schema.additionalProperties == false then
				fail(label .. ": unknown field " .. key)
			elseif type(schema.additionalProperties) == "table" then
				validate(item, schema.additionalProperties, label .. "." .. key)
			end
		end
	elseif kind == "array" then
		if schema.minItems and #value < schema.minItems or schema.maxItems and #value > schema.maxItems then
			fail(label .. " has an invalid item count")
		end
		for _, item in ipairs(value) do
			validate(item, schema.items, label .. "[]")
		end
	elseif kind == "string" then
		if schema.minLength and #value < schema.minLength or schema.maxLength and #value > schema.maxLength then
			fail(label .. " has an invalid length")
		end
	elseif kind == "number" or kind == "integer" then
		if schema.minimum and value < schema.minimum or schema.maximum and value > schema.maximum then
			fail(label .. " is outside its numeric bounds")
		end
	end
end

local function encode(value)
	return (tostring(value):gsub("[^%w%-._~]", function(char)
		return string.format("%%%02X", string.byte(char))
	end))
end

local function quote(value)
	return '"' .. value:gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n"):gsub("\r", "\\r") .. '"'
end

function M.new(settings)
	assert(type(settings) == "table", "Configure Beads projects before opening the explorer")
	local origin = assert(settings.url, "A Beads service URL is required"):gsub("/$", "")
	local scheme, host = origin:match("^(https?)://([^/]+)$")
	assert(scheme and not host:find("[@?#%s]"), "Beads URL must be an HTTP(S) origin without credentials")
	if scheme == "http" then
		assert(
			host:match("^127%.0%.0%.1:?%d*$") or host:match("^localhost:?%d*$") or host:match("^%[::1%]:?%d*$"),
			"Non-loopback Beads services require HTTPS"
		)
	end
	assert(
		type(settings.project_id) == "string" and settings.project_id:match("^[%x%-]+$") and #settings.project_id == 36,
		"A project UUID is required"
	)
	for _, key in ipairs({ "token_file", "state_dir" }) do
		assert(
			settings[key] == nil or type(settings[key]) == "string" and settings[key]:sub(1, 1) == "/",
			"Use an absolute Beads " .. key .. " path"
		)
	end
	local client = { settings = vim.deepcopy(settings), origin = origin }

	function client:call(name, args)
		local operation = assert(contract.operations[name], "Unknown generated Beads operation")
		args = args or {}
		local path, query = operation.path, {}
		for _, param in ipairs(operation.params) do
			local value = (args[param.location] or {})[param.name]
			if value == nil and param.required then
				fail("Missing " .. param.location .. " parameter: " .. param.name)
			end
			if value ~= nil then
				validate(value, param.schema, param.name)
				if param.location == "path" then
					path = path:gsub("{" .. param.name .. "}", function()
						return encode(value)
					end)
				elseif param.location == "query" then
					local values = type(value) == "table" and value or { value }
					if param.explode == false then
						query[#query + 1] = encode(param.name) .. "=" .. encode(table.concat(values, ","))
					else
						for _, item in ipairs(values) do
							query[#query + 1] = encode(param.name) .. "=" .. encode(item)
						end
					end
				end
			end
		end
		if operation.body then
			validate(args.body, operation.body, "request")
		end
		local headers = { "Content-Type: application/json", "Bd-Project-Id: " .. self.settings.project_id }
		if self.settings.token_file then
			local token = table.concat(vim.fn.readfile(self.settings.token_file), "\n"):gsub("%s+$", "")
			assert(token ~= "" and not token:find("[%c]"), "Invalid Beads token file")
			headers[#headers + 1] = "Authorization: Bearer " .. token
		end
		local config = vim.fn.tempname()
		local fd = assert(vim.uv.fs_open(config, "wx", 384))
		local lines = {}
		for _, header in ipairs(headers) do
			lines[#lines + 1] = "header = " .. quote(header)
		end
		assert(vim.uv.fs_write(fd, table.concat(lines, "\n"), 0))
		vim.uv.fs_close(fd)
		local command = {
			"curl",
			"--disable",
			"--silent",
			"--show-error",
			"--proto",
			"=http,https",
			"--connect-timeout",
			"2",
			"--max-time",
			"10",
			"--max-filesize",
			"8388608",
			"--config",
			config,
			"--request",
			operation.method,
			"--write-out",
			"\n%{http_code}",
		}
		local body = args.body and vim.json.encode(args.body) or nil
		if body then
			vim.list_extend(command, { "--data-binary", "@-" })
		end
		command[#command + 1] = self.origin .. path .. (#query > 0 and "?" .. table.concat(query, "&") or "")
		requests[config] = true
		local result = await(function(done)
			local ok, process = pcall(vim.system, command, { text = true, stdin = body, timeout = 12000 }, done)
			if ok then
				requests[config] = process
			end
			if not ok then
				done({ code = -1, stdout = "" })
			end
		end)
		vim.uv.fs_unlink(config)
		requests[config] = nil
		if result.code ~= 0 then
			fail("Beads transport failed; the server outcome may be unknown")
		end
		local raw, status = result.stdout:match("^(.*)\n(%d%d%d)$")
		status = tonumber(status)
		local ok, data = pcall(vim.json.decode, raw or "")
		if not status or status < 200 or status >= 300 then
			fail(
				"Beads HTTP "
					.. tostring(status)
					.. (ok and type(data) == "table" and ": " .. tostring(data.code or "error") or ""),
				status
			)
		end
		if not ok then
			fail("Beads returned malformed JSON; the server outcome may be unknown")
		end
		validate(data, operation.response, "response")
		return data
	end

	function client:verify()
		local context = self:call("getContext")
		assert(
			context.project_id == self.settings.project_id
				and context.backend == "dolt"
				and context.dolt_mode == "server",
			"Beads project/backend differs from configuration"
		)
		local capabilities = {
			"project.enforce",
			"issues.list",
			"issues.get",
			"issues.update",
			"issues.batchApply",
			"issues.close",
			"issues.reopen",
			"dependencies.list",
		}
		if not self.settings.prefix then
			capabilities[#capabilities + 1] = "config.get"
		end
		for _, capability in ipairs(capabilities) do
			assert(vim.tbl_contains(context.capabilities or {}, capability), "Missing Beads capability: " .. capability)
		end
	end
	return client
end

return M
