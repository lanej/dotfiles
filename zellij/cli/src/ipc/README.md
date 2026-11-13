# Native Zellij Action client

`Client::request(action, query)` sends a generated `contract::action::ActionType` directly to a resolved Unix socket and returns the original `ServerToClientMsg`. Supply a terminal ID when the action needs pane context and a shared absolute deadline for the operation. Queries wait for `Log`, `LogError`, or `Exit`; mutations can also complete with `UnblockInputThread`. `output` extracts text or reports the server's error. Each request owns its connection; failed or uncertain requests are never replayed. Frames are limited to 4 MiB.

`Client::pipe(CliPipeAction)` sends one explicit payload and collects output for its routing ID until the matching pipe-release message. An empty `pipe_id` gets a unique routing ID. `PipeResponse` retains the output and original completion (including exit code); `into_output` reports nonzero exits or server errors. Aggregate output is limited to 4 MiB. It does not read stdin, send an EOF payload, or replay requests; socket loss before release leaves the outcome unknown.

Socket discovery and capability policy belong to callers. Automatic titles resolve `zellij-context title-context` once when installing the shell hooks, then pass the resulting JSON in `ZELLIJ_TITLE_CONTEXT`. The helper checks the session index and socket incarnation before reading panes and before renaming. A replaced server invalidates the cached context; start a new shell or source the title hook again. Existing automatic-title records retain their identity and title format.

Session discovery uses the pinned runtime's `directories` 6 platform paths and `contract_version_1` namespace directly, including the socket-directory hash used for an overridden ZELLIJ_SOCKET_DIR. It launches no runtime subprocess; each operation still resolves the session name through the read-only index and checks the owned Unix socket's identity.

`contract.rs` is the complete, unmodified prost-generated contract from the runtime revision in `scripts/install-zellij`: [upstream source](https://github.com/lanej/zellij/tree/aa0d5678823b323c9848920b4102a91bc453d31f/zellij-utils/assets/prost_ipc). It uses the runtime's prost 0.12 series. Refresh or verify it with `python3 scripts/sync-zellij-contract.py` or its `--check` option; compilation needs no protobuf compiler or runtime source checkout.

The Lua codec and contract generation live in [zellij-client.nvim](https://github.com/lanej/zellij-client.nvim). Neovim consumes a pinned library revision; this repository retains session discovery and navigation policy.
