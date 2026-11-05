# Firstmate through Paseo and GitHub

Use one ordinary Paseo conversation for intake, steering, and status. Firstmate owns the queue, task assignment, supervision, recovery, and delivery policy. An assigned Pi worker implements its task, receives GitHub feedback directly, revises and verifies, and replies in the same discussion. [Issue #134](https://github.com/lanej/dotfiles/issues/134) owns the requirements and design diagrams.

This replaces the resident Claude bugfix dispatcher and generic dispatcher. There is no separate model agent relaying each review comment.

## Setup

Add `firstmate-mobile` to the machine's existing `sets` array in `~/.config/dotfiles/config.toml`. Keep the native OS set and any work sets such as `easypost`.

```sh
make plan
make install
```

The opt-in set installs Pi 1.4.0 and the official Paseo 0.15.1 CLI, uses the existing Firstmate installer, and configures a dedicated **Firstmate** provider extending Paseo's native Pi provider. Existing providers, credentials, pairing, and machine choices are preserved. Configuration alone is available through `make firstmate-mobile-config FIRSTMATE_HOME=/path/to/firstmate`; it requires an initialized Firstmate home and Node. Default `make` retains its configuration-only behavior, and `make base` remains the dependency-light native baseline.

Use the existing Paseo app/daemon and private connection. Open one conversation in the selected Firstmate home with the **Firstmate** provider, and return to that conversation for further work. Paseo owns its process and persisted session reference; the configured command is `firstmate rpc`. It forwards Paseo's RPC/session arguments unchanged and explicitly selects Zellij for direct crew. The captain runs only in Paseo. A background crew session has a home-derived name, or an explicit `FM_ZELLIJ_SESSION`; reconnects reuse it. A private native client supplies the viewport required by Zellij 0.46 for new background tabs; it creates no Paseo terminal. Terminal captain preferences and crew harness choices remain available for other workflows.

The launch supplies Firstmate's tracked watcher, turn-end guard, and supervision branch explicitly to Pi. Existing upstream session-start diagnostics still apply: a successful launch alone does not establish working supervision. The launch guard rejects a second mobile process and refuses a home already owned by a live captain. Reconcile any existing terminal captain and resume the persisted Paseo conversation. On macOS, `caffeinate` inhibits idle sleep while the Pi process runs; keep the Mac powered and its lid open for supervision.

Paseo 0.15.1 discovers models and MCP capabilities with a bare `firstmate rpc --mode rpc` invocation. The wrapper runs that metadata probe as an ephemeral Pi session with only Pi's built-in MCP and llama.cpp extensions enabled, so refreshing models can coexist with the captain without claiming Firstmate ownership or creating a crew viewport. Cloud models and `models.json` configuration remain discoverable; custom extensions that register providers are outside this metadata probe's supported inventory. Conversation launches include Paseo's integration extension or a saved session and retain the single-captain guard. Revalidate this distinction when upgrading Paseo's Pi launch protocol.

If the private crew client exits, the launcher reattaches to the same existing session; a missing session ends the captain with a recovery error. A small parent holds the launch lease until its Pi child exits, including if the outer launcher is forcibly killed. Reconcile that surviving captain before restarting; a wrapper crash can interrupt its private viewport and requires operator recovery.

## Existing peers on remote boats

`config/peers.json` registers `dev` and `dev2` through their existing SSH aliases. Authenticate each boat once from a local terminal:

```sh
firstmate peer connect dev
firstmate peer connect dev2
```

Each command installs the small peer helper and keeps one foreground SSH channel running. Keep those connections open while using peers. The channel uses a private local socket, disables ControlMaster on every SSH hop, and uses the existing 1Password/Duo authentication. Polling reuses the connection; a failed connection never initiates another login automatically. Reconnect a lost channel explicitly, then reconcile pending requests. Mobile chat does not need Paseo terminals.

```sh
firstmate peer list
firstmate peer send 'dev/tmux:$0:%1' 'What is the current outcome?' question-1
firstmate peer status question-1
```

Use an exact address returned by `list`; displayed titles and partial agent IDs are insufficient. Discovery uses Paseo's authenticated agent API and SSH inventory of tmux and Zellij. The helper uses the installed official Paseo CLI's client; API/version errors are reported and keep requests durable. Terminal submission currently supports a single foreground Claude, Codex, or Pi process in a tmux pane with a stable, empty supported prompt. Background agents, ambiguous endpoints, permission dialogs, and unrecognized prompt layouts stay unavailable or queued. Zellij peers are inventoried but reported unsupported until their live process identity can be verified; this does not affect Firstmate's managed local Zellij crew.

The captain has `firstmate_peer_list`, `firstmate_peer_send`, `firstmate_peer_status`, and `firstmate_peer_ack` tools. Messages have stable IDs and durable local/remote records under `state/peers/` and `~/.local/share/firstmate-peer/requests/`. They never adopt, restart, terminate, or clean up an existing peer, task, or worktree. Reusing an ID with different intent is refused.

Supported busy peers queue messages. Terminal identity and foreground input ownership are checked again immediately before submission. A failed or interrupted write becomes `unknown`; it is never blindly resent. Paseo uncertainty is reconciled against the exact request in its persisted timeline. States distinguish `queued`, `submitted`, `replied`, `failed`, and `unknown`; `submitted` confirms the transport operation, not successful task completion.

Each message includes reply instructions. Terminal peers record an answer with the helper's `reply <request-id> --file <reply-file>` command. Paseo peers can also use the request-specific opening and closing response markers in their final answer; the closing marker confirms a complete answer even while the peer continues other work. Replies and errors wake the same captain chat asynchronously; the captain acknowledges the exact result after reporting it so reconnects do not repeat historical outcomes. Unacknowledged results remain available after interruption. Peer text is external input and does not expand task scope or delivery authority.

The generated `config/github-feedback.json` is private to that Firstmate home:

```json
{"owner":"lanej","pollSeconds":30}
```

Set `owner` deliberately: that login's feedback is task direction. Other authors supply review input within the assigned scope. Agent replies are recognized by locally recorded reply intent and a GitHub marker, so using the same login for human and agent comments does not discard human feedback. Existing local configuration is preserved during setup.

GitHub authentication uses `GH_TOKEN`, `GITHUB_TOKEN`, or the existing HTTPS git credential helper. The bridge never prompts for credentials, invokes `gh`, or writes tokens into Paseo configuration. Grant access to the intended repositories, issues, PR discussions/reviews, and checks. Authentication or observation failures retain pending work and surface an error in the owning Pi conversation.

For work, keep `easypost` selected. The Pi launch imports the existing `~/.config/bedrock/env` when a Bedrock token is not already inherited. Sonnet uses Pi's `amazon-bedrock` provider and Bedrock Runtime directly. Sol can use the existing local Bedrock router, which forwards the Responses API to Mantle in its configured region; select `bedrock-router/openai.gpt-6.1-sol`, shown as “GPT-6.1 Sol (Bedrock router),” rather than a Converse inference-profile variant. Pi's `amazon-bedrock` provider does not inherit Codex's router configuration. Verify the actual selected provider with a small live task before adoption. Missing/expired credentials must be repaired through the existing work credential setup.

On a machine already running the router at `127.0.0.1:18081`, merge its Sol entry into Pi's mutable model registry with `node firstmate/github-feedback.mjs configure-pi-router` and apply `make pi-config`. These preserve other providers and the selected default, use the existing work token through environment interpolation, and refuse a conflicting saved router provider. Once the captain is idle, reload/resume the same existing Firstmate agent in Paseo so it loads the header extension, then refresh its models and select the router entry. Model refresh uses a separate metadata process and cannot reload extensions in a running captain. The header extension supplies the persisted Pi session ID using the router's `Session-Id` field, preserving region affinity on resume. This configuration changes no AWS retention policy or credentials.

## Tracking tasks

In the same Firstmate chat, ask “show my tasks” for a compact board or “show task `<id>`” for its full record and current observations. `/tasks` displays the board directly as an expandable chat row without a model turn, `/tasks all` expands the retained rows, and `/tasks <id>` inspects an exact local task. The captain has `firstmate_task_board` and `firstmate_task_show` tools and includes the durable native task ID when accepting work and reporting updates or outcomes. Existing native supervision continues to bring worker results and decisions back to this conversation.

The board shows work waiting on you, active tasks with their current reconciled states, queued or deferred work with its blockers, and recently completed outcomes. It reads Firstmate's existing `fm-bearings-snapshot.sh` projection and `fm-tasks-axi.sh` wrapper; it creates no separate task database or supervisor. A running worker may also have an open decision, so counts describe displayed rows rather than distinct total tasks. Unknown state, missing inventory, truncated rows, and unqueried PR/check status remain visible. Registered secondmate observations disclose their freshness, provenance, age, unavailable-state reason, and any conflict with other evidence. Deferred captain holds stay distinct from actionable decisions even in the expanded view. Peer messages remain in their own request journal.

The desktop CLI uses the same read paths:

```sh
firstmate tasks
firstmate tasks --all --json
firstmate tasks show mobile-smoke-20261104
```

`--all` reveals all rows available in the native snapshot, whose upstream collection can still have limits. Exact local task detail covers the active backlog and retained Done rows; older archived records require the native archive. Secondmate tasks display their home-qualified IDs and belong to that operational home; their observations cannot attach to a same-named local task. A persisted conversation resumes against fresh task records rather than reconstructing state from chat history.

## Intake and ownership

Give Firstmate work through Paseo, or explicitly queue an existing GitHub object:

```sh
firstmate github intake https://github.com/owner/repository/issues/123
```

Intake uses Firstmate's existing tasks-axi wrapper and a stable URL-derived task ID; repeated intake keeps the same task. It queues work and leaves dispatch to Firstmate. For tracked implementation work, Firstmate selects a Pi worker through its existing spawn/profile policy, preserving other crew preferences. Follow the normal project registration, scope, review, and delivery rules. Link a resulting PR through existing task/backlog records or `bin/fm-contributions.sh enroll <task> <PR URL>` in the Firstmate home.

The bridge reads the canonical contribution projection from `fm-fleet-snapshot.sh` and `fm-contributions.sh`; labels, repository-wide issue discovery, and session-name searches do not establish ownership. Multiple recorded owners or unavailable/non-Pi owners require Firstmate reconciliation before direct delivery. Task records remain authoritative for generation, branch, and worktree.

The worker extension records its persisted session under `data/<task>/github-session.json`, tied to the current native task generation and worktree. An existing generation requires resuming that exact session. A different live process cannot claim it. Keep the owner and worktree through review waits; opening a PR does not complete the task.

## Feedback and recovery

The primary extension polls tracked issue/PR comments, formal reviews, inline comments/thread resolution, PR revision/check/status changes, and issue/PR state. REST observations reuse ETags within the live runtime. It checks the PR head again after observation and retries later if it changed. Polling is deterministic and does not request a model turn unless work or recovery needs attention. A failed object's observation does not prevent unrelated tasks from receiving feedback.

Pending observations and their cursor are saved together under `state/github-feedback/`. Delivery uses Firstmate's own idempotent steering-inbox writer. The owning Pi extension consumes GitHub records from its existing `state/<task>.inbox/` and queues a follow-up through Pi's extension API. No second process competes for Paseo's RPC stdin. Ordinary Firstmate steering records retain their existing handling.

The worker reads the current thread, revision, and checks, makes scoped changes, and runs the project's verification. `firstmate_github_reply` posts in the source conversation or inline thread; a retry searches for the exact recorded reply before posting. `firstmate_github_done` records a concise outcome in the existing task status file and moves that event into the inbox's native `handled/` directory. Its `needsFirstmate` flag opens a keyed decision for scope, priority, blockers, or delivery authority. Finishing an event does not finish the task. Firstmate reconciles answers with its existing outstanding-decision records across GitHub and Paseo.

Delivery is at least once across interrupted turns. Pending inbox records are presented again after a session resumes, and reply retries are idempotent. The worker must inspect existing GitHub/branch results before repeating work. The bridge does not promise exactly-once arbitrary model or git operations.

If a Pi worker exits, feedback stays in its inbox and Firstmate receives the recorded session reference for recovery. Reconcile surviving workers, then resume through Firstmate's supported lifecycle or explicitly reassign the task. Do not create another worker merely because its endpoint is unavailable. The owner record remains available after process exit.

The primary owns the poller and must hold Firstmate's native session lock; a lock-refused session cannot poll or route work. While its host process is stopped there are no polls. Paseo's supported session recovery resumes the primary, whose first eligible poll catches up. A phone disconnect does not stop the host process or workers. Native Firstmate locks serialize pollers and owner registration; the lease process releases its lock when its parent pipe closes.

```sh
# Inspect/catch up using the same deterministic adapter (outside another active poll).
firstmate github poll
# Reinstall the provider configuration after deliberately changing the selected home.
firstmate github configure-paseo
```

Approval satisfies the applicable review requirement. Firstmate must separately confirm delivery authority and revalidate the actual current head and required checks before merging. Neither the bridge nor its worker tools has an automatic merge path. A changed revision or failing check invalidates prior readiness under the project's existing policy.

## Retiring the dispatcher

The old launcher, workers, skills, and their standalone launch detector are removed. Setup removes only obsolete bin symlinks targeting those exact files in this checkout; normal shared-agent synchronization prunes retired skill links. Existing dispatcher sessions, worktrees, locks, and unlanded changes are preserved. Finish or explicitly retire old work before moving it into Firstmate; do not run both owners against the same task.

## Verification and adoption

```sh
npm install --prefix /tmp/firstmate-github-runtime --ignore-scripts \
  @earendil-works/pi-coding-agent@1.4.0 @getpaseo/server@0.15.1 \
  @getpaseo/cli@0.15.1 tasks-axi@0.2.6
FIRSTMATE_TEST_RUNTIME=/tmp/firstmate-github-runtime \
  FIRSTMATE_SOURCE=/path/to/firstmate make test-firstmate-github
FIRSTMATE_TEST_RUNTIME=/tmp/firstmate-github-runtime \
  FIRSTMATE_SOURCE=/path/to/firstmate make test-firstmate-peers
```

The GitHub workflow uses the actual installer, Firstmate ownership projection/inbox library, Paseo's native Pi RPC runtime, and real Pi processes. It queues an issue, resumes the same primary and worker, catches up review left during downtime, edits and tests a fixture repository, publishes its isolated branch to a local bare remote, replies inline, and returns an outcome without merging on approval. HTTP model responses and GitHub are controlled fixtures; this case seeds task metadata and primary ownership and disables unrelated upstream primary extensions. Workers load the bridge through the installed global Pi configuration.

The separate mobile chat case uses native dispatch, Treehouse leases, a real Zellij worker pane, and the upstream Pi watcher. A bounded worker fixture reads a repository token and records completion; the watcher returns it to the same chat without a user prompt. Task tracking reads native queued, blocked, captain-held, future-dated, and completed records; the expanded board preserves deferred placement, `/tasks` needs no model call, and reconnect retains exact task detail. Renderer examples challenge unavailable and cached secondmate observations and foreign tasks sharing a local ID. The unverified worker fixture's historical completion event remains distinct from reconciled current state and landed work. The detector resumes the persisted conversation, verifies the existing crew process survives, kills and recovers the private viewport, and verifies that a surviving Pi prevents another captain even after outer-wrapper loss. Model responses and the worker harness are controlled; the native lifecycle and RPC processes are real.

The peer workflow uses a real tmux terminal and the official authenticated Paseo agent API through controlled SSH connections. It exercises busy queues, verified npm launchers, both supported Codex composer layouts, completed replies during later independent work, lost receipts, durable reconciliation, and acknowledgment across captain reconnects. A displaced input cursor must remain queued across repeated observations. Live SSH authentication and remote harness compatibility require separate acceptance.

The native scripts are measured against Firstmate commit `21180385d1cb782941df13ed91ba7c44f0d76351`. Use an updated checkout with compatible contribution, steering-inbox, and Pi supervision contracts. Changes to those contracts need deliberate revalidation.

Keep this opt-in until a live Bedrock/Pi/Paseo/GitHub smoke run proves upstream watcher/guard/branch loading, task completion reaching the primary without another prompt, actual phone disconnect/reconnect, and notifications. Fixture success does not establish those live properties. Issue #134 remains open for that adoption evidence.
