# Pi dispatcher review

Run one independent reviewer on an existing builder's committed checkout:

```sh
~/.files/ai/skills/dispatcher/scripts/dispatcher-worker review-pi <builder-id> \
  --model <provider/model> --timeout 300
```

Run this from the dispatcher's repository with its usual
`.claude/dispatcher.config.json`. The command resolves the builder's actual
checkout, confirms it belongs to that Git repository, and reviews the diff
from the merge base of `origin/<targetBranch>` to its current `HEAD`.
It uses the existing local remote-tracking ref; fetch that base before invoking
the reviewer when freshness matters. The checkout must be clean and the change
committed. Diffs larger than 256 KiB are refused explicitly.

The endpoint is opt-in at the independent review step. Existing Claude builders,
reviewer modes, verification commands, and finish operations retain their current
behavior. The dispatcher still runs `verify`, considers the review, and decides
whether to call `finish`; this endpoint cannot publish or finish the change.

For a checkout outside an existing dispatcher lifecycle:

```sh
~/.files/bin/pi-review --cwd /absolute/path/to/checkout --base origin/main \
  --model <provider/model> --timeout 300
```

## Runtime and result

Install the Node package **@earendil-works/pi-coding-agent@1.4.0** and configure
the chosen provider normally. The worker uses Pi's exported `RpcClient`, so Pi
owns RPC framing, authentication, and model compatibility. There is no build
step or additional npm dependency. The model argument is required. `--pi-bin`
selects the installed package's CLI executable, including an npm symlink; it
does not accept a shell command or standalone binary. An unsupported Pi version
fails before review. The shared dispatcher retains its existing Python helpers;
the review worker and its fixture tests run in Node.

Each invocation writes a new owner-only directory under
`~/.local/state/pi-reviews/<session-id>/`, or the new outside-checkout directory
given by `--output-dir`. The single JSON object on stdout identifies:

- The concrete cwd, base, merge base, and reviewed commit.
- The requested model and the provider/model Pi actually selected.
- The exact session ID, session file, result file, and diagnostic log.
- `status` and, for a completed review, `verdict` and `reviewFile`.

`status: reviewed` requires prompt acceptance, `agent_settled` without abort,
a normally completed assistant message, and a valid review response. An
`agent_end` event or idle process alone is insufficient. The checkout is checked
again before the result is accepted; a changed checkout makes the result fail.

**Exit zero means a review was received, not approval.** The verdict is
`approve`, `changes_requested`, or `inconclusive`. It remains a model judgment;
the dispatcher must inspect the findings and independently verify the patch.
The reviewer cannot run tests and must disclose missing evidence.

A failed startup, provider failure, malformed review, or stale checkout records
`failed` and exits 1 once the result directory exists. Invalid arguments or an
unavailable result directory exit 2 before starting Pi. The time budget includes setup and review; expiry records
`timed_out` and exits 124. SIGINT/SIGTERM records `cancelled` and exits 130.
Shutdown first requests an abort, then terminates the child process group if it
does not exit. Cleanup may take up to three additional seconds. A hard-killed
host can leave a nonterminal result; never interpret it as a completed review.

The recorded `pid` identifies a detached Node supervisor. It runs `RpcClient`
and its Pi subprocess in one owned process group, so cleanup can stop remaining
descendants even if the supervisor or Pi exits first. Diagnostics are captured
in `stderr.log`.

## Tool and instruction boundary

The reviewer exposes only `read`, `grep`, `find`, and `ls`. It disables automatic
extensions, MCP servers, skills, prompt templates, themes, and context-file
loading, and declines project configuration trust. It loads the shared
`ai/agents/code-reviewer.md` and Builder architecture/construction references
directly from this checkout, then asks the reviewer to read applicable project
instructions as evidence. It does not copy a second instruction catalog.

This is restricted tool exposure, **not an operating-system sandbox**. The Pi
process and read tools retain the launching account's access; the working
directory does not confine reads. User-level provider configuration and auth
remain in use, including any credential commands configured there. Use an
appropriately restricted account or environment when those boundaries matter.

## Verification

`make test-pi-review` exercises the actual dispatcher and review entrypoints with
Pi's installed `RpcClient` and a simulated Pi CLI. Pi 1.4.0 must be installed for
both forms of the check. `node scripts/test-pi-review.mjs --native` runs that
same review workflow through Pi 1.4.0 with a local HTTP fixture model. CI runs
the native form without paid API calls or provider credentials. It checks the
review result, selected tools, shared instructions, concrete checkout/session,
disabled project extension, and preservation of builder state and source files.
The fixture establishes integration behavior, not model review quality.

The implementation follows Pi's versioned
[RPC protocol](https://github.com/earendil-works/pi/blob/v1.4.0/packages/coding-agent/docs/rpc.md),
[event lifecycle](https://github.com/earendil-works/pi/blob/v1.4.0/packages/coding-agent/docs/json.md),
and [CLI options](https://github.com/earendil-works/pi/blob/v1.4.0/packages/coding-agent/docs/cli.md).
