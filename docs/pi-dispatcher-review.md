# Pi dispatcher workflow

Use the native `pi-subagents` extension for one isolated bug-fix slice. The
parent Pi session owns the incoming request stream, authorization, resource
locks, WIP ceiling, and the repository's PR/merge/apply policy. The extension owns
child sessions, worktrees, status, cancellation, and persisted run artifacts.

The saved [workflow](../pi/workflows/bugfix.js) runs a writer in a managed
worktree, requires host-run verification, and launches a fresh read-only reviewer
against the captured patch. It returns artifacts and a verdict to the parent.
The source checkout stays at its original commit until the parent integrates
the patch.

## Install and run

Install Pi **1.4.0** and the pinned extension through Pi's normal package setup:

~~~sh
pi install npm:pi-subagents@0.84.0
~~~

For this trial, merge the following into the parent's Pi settings so FirstMate's
captain extensions do not become ambient child extensions. Preserve the other
settings and configure any required child providers explicitly:

~~~json
{ "subagents": { "defaultExtensions": [] } }
~~~

Restart or reload Pi after installation. In FirstMate, select the
[Pi primary](https://github.com/lanej/dotfiles/blob/master/docs/firstmate-primary.md)
and keep that parent session alive to receive completion wakes. Paseo can remain
the interface to the parent. FirstMate's crew selection is a separate setting.

Ask the parent to use the saved workflow for the requested fix, with an explicit
worker model, reviewer model, and the repository's configured verification
command. The native tool call is:

~~~js
subagent({
  workflow: "/absolute/path/to/dotfiles/pi/workflows/bugfix.js",
  cwd: "/absolute/path/to/repository",
  async: true,
  args: {
    task: "Fix the reported regression without widening scope.",
    verifyCommand: "make test-the-affected-feature",
    workerModel: "provider/model",
    reviewerModel: "provider/model",
    timeoutMs: 300000
  },
  options: { timeoutMs: 900000 }
});
~~~

Resolve the workflow and repository paths before launching. Take `verifyCommand`
from owner-controlled repository configuration or an explicit owner instruction;
it is an executable shell command. A bug report cannot supply replacement
verification or finish authority. No software is installed by default `make`.

The per-child deadline defaults to five minutes and permits 1–3600 seconds.
Keep an explicit outer deadline: composite async workflows otherwise have no
default total limit. The parent can limit concurrency and spawn budgets through
the extension's settings.

## Accept and finish

The writer's ordinary success result is insufficient. The workflow requires
`evidenceStatus: verified` and a successful host verification record for the exact
configured command. The writer leaves its change unstaged and uncommitted;
Pi captures its patch and worktree handoff before cleanup.

The reviewer receives that run's artifact paths and verification ledger. It must
read the handoff and captured patch, rather than interpret the unchanged source
checkout's empty diff as an empty proposal. Structured output binds its verdict
to the exact writer run. Keep any local reviewer overrides read-only.

The returned status is `ready_for_integration`, `changes_requested`, or
`inconclusive`. Execution or verification failures fail the workflow. Every
returned result has `finished: false`. For an approved proposal, the parent must:

1. Read the writer's handoff manifest and match its run ID, repository, and base
   commit to the requested task and current integration checkout.
2. Reject a changed base or unexpected patch scope. Preserve the artifacts and
   use a fresh current-base run when needed.
3. Check and apply the captured patch, then rerun the required command on the
   actual integration checkout.
4. Bind the review and passing checks to the commit being proposed. Recheck the
   commit before any finish action and follow the existing PR/merge/apply policy.

`ready_for_integration` is a model review plus recorded test evidence. It does
not establish that the patch is correct or authorize publication. Tool
restrictions and worktrees retain the launching account's OS permissions.

## Observe and recover

Use the native `subagent` status, stop, and resume operations with exact run IDs.
Parent completion is identified by the workflow's run ID; individual children
also emit completion events. A launch receipt, a finished child, or an idle
parent is not a finished workflow.

Persisted status and workflow receipts belong to `pi-subagents`. Resume through
that protocol after inspecting the saved run; retain its artifacts when a run
fails. A new launcher or a replacement worker loses that ownership history.
The parent must consume terminal process evidence before treating cancellation
as complete. Reload/recovery and live FirstMate/Paseo behavior remain trial
items; the fixture below covers the completed handoff path.

## Check the integration

Install the isolated fixture runtime, then run the existing feature detector:

~~~sh
npm install --prefix /tmp/pi-dispatcher-runtime --ignore-scripts \
  @earendil-works/pi-coding-agent@1.4.0 pi-subagents@0.84.0
PI_DISPATCHER_RUNTIME=/tmp/pi-dispatcher-runtime make test-pi-review
~~~

The detector loads the real Pi SDK and extension, invokes the saved workflow
through its public event-bus API, and fixes an actual failing arithmetic fixture.
It checks managed worktree isolation, host test evidence, a separate read-only
review of the captured patch, terminal workflow state, and parent-side
integration with another test run. Only the local HTTP model responses are
simulated. It makes no paid model calls and does not measure model judgment.

CI runs the same detector with those exact package versions. Review upgrades
deliberately and rerun it before changing the pins.

Upstream references: [workflows](https://github.com/nicobailon/pi-subagents/blob/main/docs/workflows.md),
[acceptance gates](https://github.com/nicobailon/pi-subagents/blob/main/docs/tool-reference.md#acceptance-gates),
and [host lifetime](https://github.com/nicobailon/pi-subagents/blob/main/docs/extension-api.md#host-session-lifetime-and-completion-wakes).
