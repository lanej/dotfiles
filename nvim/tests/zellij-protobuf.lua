local root = vim.env.DOTFILES_TEST_ROOT
vim.opt.rtp:prepend(root .. "/nvim")
local wire = require("zellij.protobuf")
local fixtures = vim.json.decode(table.concat(vim.fn.readfile(root .. "/nvim/tests/zellij-protobuf.json"), "\n"))
local function values(value)
	if type(value) ~= "table" then
		return value
	end
	if value["$bytes"] then
		return value["$bytes"]:gsub("..", function(hex)
			return string.char(tonumber(hex, 16))
		end)
	end
	for key, item in pairs(value) do
		value[key] = values(item)
	end
	return value
end
for _, fixture in ipairs(fixtures) do
	fixture.value = values(fixture.value)
	local bytes = fixture.hex:gsub("..", function(hex)
		return string.char(tonumber(hex, 16))
	end)
	local expected = fixture.encode_hex
			and fixture.encode_hex:gsub("..", function(hex)
				return string.char(tonumber(hex, 16))
			end)
		or bytes
	assert(wire.encode(fixture.type, fixture.value) == expected, "Lua encoding differs from protobuf: " .. fixture.type)
	assert(
		vim.deep_equal(wire.decode(fixture.type, bytes), fixture.value),
		"Lua decoding differs from protobuf: " .. fixture.type
	)
	local unknown = string.char(248, 255, 255, 255, 15, 1)
	assert(
		vim.deep_equal(wire.decode(fixture.type, bytes .. unknown), fixture.value),
		"Unknown fields changed a known message"
	)
end
assert(
	wire.encode("MoveFocusAction", { direction = "DIRECTION_RIGHT" })
		== wire.encode("MoveFocusAction", { direction = wire.enum("Direction").DIRECTION_RIGHT })
)
assert(
	not pcall(wire.encode, "ApplyFloatingSwapLayoutByTabIdAction", { id = "18446744073709551616" }),
	"uint64 overflow accepted"
)
assert(
	not pcall(wire.encode, "ApplyFloatingSwapLayoutByTabIdAction", { id = 18446744073709551615 }),
	"Imprecise Lua number accepted"
)
local large = string.rep("x", 100000)
local framed = wire.frame(large)
assert(wire.frame_size(framed) == #large and framed:sub(5) == large)
assert(not pcall(wire.frame_size, string.char(0, 0, 128, 0)), "Oversized frame accepted")
assert(not pcall(wire.decode, "ServerToClientMsg", string.char(42, 5, 10)), "Truncated message accepted")
print("PASS: Full Zellij protobuf API matches independent reference messages and bounds frame sizes")
