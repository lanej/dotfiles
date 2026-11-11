# Zellij Lua client

`require("zellij")` provides asynchronous native actions over the pinned Zellij runtime’s Unix socket. `pane-navigation.lua` owns editor navigation policy; the client has no dependency on Navigator or its focus rules.

```lua
local client, err = require("zellij").connect()
assert(client, err)

local cancel = client:request({ list_tabs = { output_json = true } }, {
    expect_output = true,
    timeout_ms = 2000,
}, function(error, output, response)
    if error then
        vim.notify(error, vim.log.levels.WARN)
        return
    end
    local tabs = vim.json.decode(output)
    -- Use tabs here. response contains the decoded server message.
end)

-- cancel() cancels this request; client:close() cancels all requests and closes the client.
```

`connect()` resolves and validates the current session once through `zellij-context socket`. `new({path, device, inode})` accepts an already resolved identity. Each request owns its socket and timer, and its callback runs on Neovim’s main loop. Requests accept generated `Action` tables; options include `terminal_id`, `client_id`, `expect_output`, and `timeout_ms`. Set `expect_output` for queries so a generic input acknowledgement cannot replace their response. The runtime chooses the last active client for CLI actions; passing `client_id` does not override a live last active client. Callers that act on focus must establish their own ownership conditions. Timeout, cancellation, and disconnect errors do not establish whether an action ran; requests are never replayed automatically.

## Protobuf API

`require("zellij.protobuf")` exposes every message and enum from the pinned runtime’s five protobuf files, including application-control and pane-mirror messages. It uses Neovim’s built-in LuaJIT FFI and requires no installed Lua package.

```lua
local pb = require("zellij.protobuf")
local Direction = pb.enum("Direction")
local bytes = pb.encode("ClientToServerMsg", {
    action = {
        is_cli_client = true,
        action = { move_focus = { direction = Direction.DIRECTION_LEFT } },
    },
})
local message = pb.decode("ClientToServerMsg", bytes)
```

Message and enum names accept either their fully qualified protobuf names or names relative to `client_server_contract`. Lua tables use original protobuf field names. Enum inputs accept names or numbers, and decoding returns numbers. Byte fields use binary Lua strings. Unsigned 64-bit integers decode as decimal strings; encoding also accepts numbers within Lua’s exact integer range. Maps decode with string keys. Absent scalar fields remain absent, and unknown wire fields are skipped. Nested messages, oneofs, packed and unpacked repeated fields, and maps retain protobuf semantics. `messages` and `enums` expose generated descriptors; `frame(bytes)` and `frame_size(header)` implement Zellij’s bounded four-byte IPC framing.

Run `uv run scripts/generate-zellij-lua.py` from the repository root after updating the pinned runtime. Generation compiles all five original schema files and produces the full Lua schema plus reference messages using Python’s protobuf implementation. `make test-zellij-navigation` checks regeneration, reference compatibility, reusable client behavior through real Unix sockets, and the live navigation integration. The schema is generated; edit the generator rather than `schema.lua`.
