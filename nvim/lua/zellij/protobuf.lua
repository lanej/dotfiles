local ffi = require("ffi")
local schema = require("zellij.schema")
local M = { messages = schema.messages, enums = schema.enums }
local uint64 = ffi.typeof("uint64_t")
local MAX64 = ffi.cast("uint64_t", ffi.new("int64_t", -1))
local MAX32 = uint64(4294967295)
local floating = ffi.typeof("union { float value; uint8_t bytes[4]; }")

local metadata = {}

local function resolve(collection, name)
	return assert(collection[name] or collection["client_server_contract." .. name], "Unknown protobuf type: " .. name)
end

function M.enum(name)
	return resolve(schema.enums, name)
end

local function descriptor(name)
	if not metadata[name] then
		local definition = resolve(schema.messages, name)
		local by_tag, by_name = {}, {}
		for _, field in ipairs(definition.fields) do
			by_tag[field.tag], by_name[field.name] = field, field
		end
		metadata[name] = { definition = definition, by_tag = by_tag, by_name = by_name }
	end
	return metadata[name]
end

local function integer64(value)
	if type(value) == "number" then
		assert(
			value == math.floor(value) and value >= 0 and value <= 9007199254740991,
			"Use a decimal string for a 64-bit integer outside Lua's exact range"
		)
		value = string.format("%.0f", value)
	end
	assert(type(value) == "string" and value:match("^%d+$"), "Invalid unsigned 64-bit integer")
	local number = uint64(0)
	for digit in value:gmatch("%d") do
		digit = tonumber(digit)
		assert(number <= (MAX64 - digit) / uint64(10), "64-bit integer out of range")
		number = number * 10 + digit
	end
	return number
end

local function decimal(value)
	return tostring(value):gsub("ULL$", ""):gsub("LL$", "")
end

local function varint(value)
	local parts = {}
	value = uint64(value)
	repeat
		local byte = tonumber(value % 128)
		value = value / uint64(128)
		parts[#parts + 1] = string.char(byte + (value ~= 0 and 128 or 0))
	until value == 0
	return table.concat(parts)
end

local function read_varint(bytes, position)
	local value, multiplier = uint64(0), uint64(1)
	for index = 1, 10 do
		local byte = bytes:byte(position)
		assert(byte and (index < 10 or byte <= 1), "Invalid or truncated protobuf varint")
		value = value + (byte % 128) * multiplier
		position = position + 1
		if byte < 128 then
			return value, position
		end
		multiplier = multiplier * 128
	end
	error("Invalid protobuf varint")
end

local function blob(bytes, position)
	local size
	size, position = read_varint(bytes, position)
	assert(size <= #bytes - position + 1, "Truncated protobuf field")
	size = tonumber(size)
	return bytes:sub(position, position + size - 1), position + size
end

local function wire_type(field)
	if field.kind == "message" or field.kind == "string" or field.kind == "bytes" then
		return 2
	end
	return field.kind == "float" and 5 or 0
end

local function scalar_encode(field, value)
	local kind = field.kind
	if kind == "string" or kind == "bytes" or kind == "message" then
		local body = kind == "message" and M.encode(field.ref, value) or value
		assert(type(body) == "string", "Expected protobuf string or bytes")
		return varint(#body) .. body
	elseif kind == "float" then
		assert(type(value) == "number", "Expected protobuf floating-point number")
		local data = floating()
		data.value = value
		local bytes = ffi.string(data.bytes, 4)
		return ffi.abi("le") and bytes or bytes:reverse()
	elseif kind == "bool" then
		assert(type(value) == "boolean", "Expected protobuf boolean")
		value = value and 1 or 0
	elseif kind == "enum" then
		value = type(value) == "string" and assert(M.enum(field.ref)[value], "Unknown enum value") or value
		assert(
			type(value) == "number" and value == math.floor(value) and value >= -2147483648 and value <= 2147483647,
			"Enum value out of range"
		)
		value = ffi.cast("uint64_t", ffi.new("int64_t", value))
	elseif kind == "uint64" then
		value = integer64(value)
	else
		local signed = kind == "int32"
		assert(kind == "int32" or kind == "uint32", "Unsupported protobuf scalar: " .. kind)
		assert(
			type(value) == "number"
				and value == math.floor(value)
				and value >= (signed and -2147483648 or 0)
				and value <= (signed and 2147483647 or 4294967295),
			"32-bit integer out of range"
		)
		value = ffi.cast("uint64_t", ffi.new("int64_t", value))
	end
	return varint(value)
end

local function scalar_decode(field, bytes, position, existing)
	local kind = field.kind
	if kind == "string" or kind == "bytes" or kind == "message" then
		local body, next_position = blob(bytes, position)
		return kind == "message" and M.decode(field.ref, body, existing) or body, next_position
	elseif kind == "float" then
		assert(position + 3 <= #bytes, "Truncated protobuf field")
		local body, data = bytes:sub(position, position + 3), floating()
		ffi.copy(data.bytes, ffi.abi("le") and body or body:reverse(), 4)
		return tonumber(data.value), position + 4
	end
	local value
	value, position = read_varint(bytes, position)
	if kind == "bool" then
		value = value ~= 0
	elseif kind == "uint64" then
		value = decimal(value)
	elseif kind == "int32" or kind == "enum" then
		value = tonumber(ffi.cast("int32_t", value))
	else
		value = tonumber(ffi.cast("uint32_t", value))
	end
	return value, position
end

local function default(field)
	if field.kind == "message" then
		return {}
	end
	if field.kind == "string" or field.kind == "bytes" then
		return ""
	end
	if field.kind == "bool" then
		return false
	end
	return field.kind:find("64", 1, true) and "0" or 0
end

function M.encode(name, message)
	local meta, parts, oneofs = descriptor(name), {}, {}
	for key in pairs(message) do
		assert(meta.by_name[key], "Unknown protobuf field: " .. key)
	end
	for _, field in ipairs(meta.definition.fields) do
		local value = message[field.name]
		if value ~= nil then
			if field.oneof then
				assert(not oneofs[field.oneof], "Multiple values for protobuf oneof " .. field.oneof)
				oneofs[field.oneof] = true
			end
			local tag = varint(field.tag * 8 + wire_type(field))
			if field.kind == "message" and descriptor(field.ref).definition.map_entry then
				local entry = descriptor(field.ref).definition.fields
				local keys = {}
				for key in pairs(value) do
					keys[#keys + 1] = key
				end
				table.sort(keys, function(a, b)
					return tostring(a) < tostring(b)
				end)
				for _, key in ipairs(keys) do
					local map_key = key
					if entry[1].kind == "bool" and type(key) == "string" then
						assert(key == "true" or key == "false", "Invalid protobuf boolean map key")
						map_key = key == "true"
					elseif entry[1].kind ~= "string" and not entry[1].kind:find("64", 1, true) then
						map_key = tonumber(key)
					end
					parts[#parts + 1] = tag .. scalar_encode(field, { key = map_key, value = value[key] })
				end
			elseif field.repeated then
				local repeated = {}
				for _, item in ipairs(value) do
					repeated[#repeated + 1] = (field.packed and "" or tag) .. scalar_encode(field, item)
				end
				local body = table.concat(repeated)
				if #body > 0 then
					parts[#parts + 1] = field.packed and (varint(field.tag * 8 + 2) .. varint(#body) .. body) or body
				end
			else
				local body = scalar_encode(field, value)
				if
					field.kind == "message"
					or field.oneof
					or meta.definition.map_entry
					or body ~= scalar_encode(field, default(field))
				then
					parts[#parts + 1] = tag .. body
				end
			end
		end
	end
	return table.concat(parts)
end

function M.decode(name, bytes, existing)
	local meta, result, position, oneofs = descriptor(name), existing or {}, 1, {}
	for _, field in ipairs(meta.definition.fields) do
		if field.oneof and result[field.name] ~= nil then
			oneofs[field.oneof] = field.name
		end
	end
	while position <= #bytes do
		local key
		key, position = read_varint(bytes, position)
		assert(key <= MAX32 and key >= 8, "Invalid protobuf field")
		key = tonumber(key)
		local tag, wire = math.floor(key / 8), key % 8
		local field = meta.by_tag[tag]
		if not field then
			if wire == 0 then
				_, position = read_varint(bytes, position)
			elseif wire == 2 then
				_, position = blob(bytes, position)
			elseif wire == 1 or wire == 5 then
				position = position + (wire == 1 and 8 or 4)
			else
				error("Unsupported protobuf wire type")
			end
			assert(position <= #bytes + 1, "Truncated protobuf field")
		elseif wire == 2 and field.repeated and wire_type(field) ~= 2 then
			local packed
			packed, position = blob(bytes, position)
			local index = 1
			result[field.name] = result[field.name] or {}
			while index <= #packed do
				local value
				value, index = scalar_decode(field, packed, index)
				table.insert(result[field.name], value)
			end
		else
			assert(wire == wire_type(field), "Unexpected protobuf wire type")
			local value
			value, position = scalar_decode(field, bytes, position, not field.repeated and result[field.name] or nil)
			if field.kind == "message" and descriptor(field.ref).definition.map_entry then
				local entry = descriptor(field.ref).definition.fields
				local map_key = value.key
				if map_key == nil then
					map_key = default(entry[1])
				end
				local map_value = value.value
				if map_value == nil then
					map_value = default(entry[2])
				end
				result[field.name] = result[field.name] or {}
				result[field.name][tostring(map_key)] = map_value
			elseif field.repeated then
				result[field.name] = result[field.name] or {}
				table.insert(result[field.name], value)
			else
				if field.oneof then
					if oneofs[field.oneof] then
						result[oneofs[field.oneof]] = nil
					end
					oneofs[field.oneof] = field.name
				end
				result[field.name] = value
			end
		end
	end
	return result
end

function M.frame(message)
	local size = #message
	assert(size <= 4 * 1024 * 1024, "Zellij IPC frame exceeds limit")
	return string.char(
		size % 256,
		math.floor(size / 256) % 256,
		math.floor(size / 65536) % 256,
		math.floor(size / 16777216) % 256
	) .. message
end

function M.frame_size(bytes)
	local a, b, c, d = bytes:byte(1, 4)
	local size = a + b * 256 + c * 65536 + d * 16777216
	assert(size <= 4 * 1024 * 1024, "Zellij IPC frame exceeds limit")
	return size
end

return M
