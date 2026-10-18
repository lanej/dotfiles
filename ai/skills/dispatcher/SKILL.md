---
name: dispatcher
description: Generic protocol for a resident work-dispatcher session attached to a repo — receives change requests via cross-session messages, builds each in an isolated background worker session, independently verifies the result, and merges, opens a PR, or applies per a per-repo config. Generalizes recover-on-start, per-resource locking, a global WIP ceiling, launch verification, edge-triggered idle subscription, a mechanical merge/apply bar, and safe cleanup, as proven in bugfix-dispatcher, infra-dispatcher, and matrix-dispatcher. Use when attaching an autonomous work-dispatcher to a repo receiving change requests via cross-session messages, or standing up a new domain-specific dispatcher. Don't use for a one-off task with no recurring request stream, a repo that doesn't want autonomous merges/PRs/applies, or to modify bugfix-dispatcher, infra-dispatcher, or matrix-dispatcher themselves — those are independent, already-in-production skills.
---

# Dispatcher

Generic protocol for a resident dispatcher session: a long-running Claude Code session, attached
to one repo, that receives change requests over cross-session messages, builds each one in an
isolated real background session, independently re-verifies the result, and closes it out
(merge/PR/apply) per that repo's own config. This skill is a template distilled from three
production dispatchers — read `references/worker-protocol.md` for full step-by-step detail before
acting on anything below; this file is the navigator, not the procedure.

## Before first use in a new repo

1. Read `references/config-schema.md` in full — it defines every field the per-repo config file
   must set (`allowedOrigin`, `verifyCommand`, `finishMode`, `trackingMode`, `wipCeiling`,
   `reviewerMode`, `notifyState`) and gives one complete worked example.
2. Confirm the config file exists at the adopting repo's `.claude/dispatcher.config.json` (or the
   path this dispatcher instance was told to use). If missing or malformed, stop — see Error
   Handling below.
3. Confirm `scripts/dispatcher-worker` exists and is executable in the adopting repo. This skill
   does not ship that script — each dispatcher instance owns its own `dispatcher-worker`
   implementing the `recover|start|check|verify|finish|unlock|gc` subcommands this protocol calls.
4. Launch the resident session with `scripts/dispatcher-launch launch`, run from inside the
   adopting repo — it pins non-interactive cross-session delivery (`crossSessionInbound: "accept"`)
   and backgrounds the session (`--bg`) so it stays addressable without a human keeping a terminal
   open. Without `crossSessionInbound: "accept"`, an inbound report from a session in a different
   permission-mode class is held for manual terminal approval and can silently expire. Use
   `scripts/dispatcher-launch attach|logs|status` to inspect or reattach to it later.

## On start, before waiting for anything: recover

1. Run `scripts/dispatcher-worker recover`. A previous instance of this dispatcher may have died
   mid-item, leaving in-flight work behind.
2. For each entry it reports, classify as `resumable` (the worker session is still alive —
   re-subscribe with `notify_when_idle: true` and rejoin the per-report protocol at the matching
   step), `orphaned_cleaned` (worker gone too; `recover` already released the lock and removed
   state — nothing further required), or `none` (proceed normally).
3. Once recovery is handled, just wait — incoming cross-session messages deliver into a normal
   turn automatically. There is no polling loop to run.

## Per-report protocol (high level — full detail in references/worker-protocol.md)

Read `references/worker-protocol.md` before executing this list on a real report; it expands every
step below with the exact commands, decision trees, and failure handling. Read
`references/lessons-learned.md` before handling any failure, retry, or edge case not obviously
covered here — several of these steps exist specifically because of an incident documented there.

For each incoming report, in order:

1. **Generate a slug** — one timestamp+description identifier reused everywhere (report filename,
   worktree name, session name) for the rest of the item's lifecycle.
2. **Pre-dispatch sanity check** — grep the target repo for the report's own cited files/paths
   before dispatching anything; catches a mislabeled-repo or wrong-target request cheaply.
3. **Validate scope + lock** via `scripts/dispatcher-worker start` — enforces `allowedOrigin` and
   acquires the per-resource lock. A scope failure means stop and reply out-of-scope; a `BUSY` exit
   means wait and retry, not failure.
4. **Check the global WIP ceiling** — a separate, config-driven cap (`wipCeiling`) on total
   concurrent in-flight items across all locked resources, distinct from the per-resource lock. The
   same `start` call checks this before attempting the lock, so an `AT_CAPACITY` refusal can occur
   even when step 3's lock was never contended — don't assume `BUSY` and `AT_CAPACITY` map cleanly
   onto this list's step order.
5. **Create the tracking issue** (`trackingMode: "issue"`, the default) — the dispatcher itself
   opens a real tracking issue in the resource's own issue tracker before the builder is dispatched;
   no local record file is written. Skipped under `trackingMode: "file"`, where the builder commits
   its own record file as its first commit instead.
6. **Write the builder's prompt to a temp file** — never inline a multi-line report into argv.
   References the tracking issue (or the record-file convention, under `trackingMode: "file"`).
7. **Launch** the builder via `claude -w <slug> --bg -n <session-name> --permission-mode
   bypassPermissions <prompt-file>`.
8. **Immediately verify the launch actually succeeded** against `claude agents --json` — never
   trust the returned id blindly.
9. **Subscribe** with `notify_when_idle: true` immediately after confirmed launch — edge-triggered,
   not retroactive.
10. **On notification, check** working/blocked/done. `blocked` is not a failure — it is the
    interactive design's actual purpose; escalate and leave the lock held.
11. **Check for an "unable to build/reproduce" signal** in the builder's final message before
    trusting it enough to run `verify`.
12. **Independently verify** — re-derive ground truth (real diff, real test run, real static
    check) directly; never trust the builder's self-report.
13. **Dispatch a reviewer** — a same-process code-reviewer subagent (lighter default) or a fully
    separate blind reviewer session with zero visibility into the builder's reasoning (higher-stakes
    repos), per `reviewerMode`.
14. **Decide** via an explicit, mechanical merge/apply bar — all criteria required, no partial
    credit.
15. **Independently check real state after any completion claim** from builder or reviewer —
    a valid verdict that never calls the apply/merge step, an apply/merge call that "succeeds"
    without the triggered action actually resolving, and (under `trackingMode: "issue"`) a merge
    whose commit trailer didn't actually auto-close the tracking issue, are all real, distinct
    failure modes.
16. **Cap repeat failures on the same signature at 2 attempts** — a third occurrence of an
    identical failure class is escalated to the user as a policy question, not re-patched again.
17. **Close out in order**: finish (merge/PR/apply per `finishMode`) → unlock → immediate session
    cleanup → reply to the original requester → notify the user only on non-clean outcomes.

Emit one status line at each real state transition (dispatch, verify-result, review-dispatch,
review-verdict, closeout, CI-result) — not only a single message at the end.

## Error Handling

- **Config file missing or malformed** — stop before dispatching anything; do not guess defaults
  for `allowedOrigin` or `finishMode`. Read `references/config-schema.md`, fix or create the file,
  and re-run.
- **Worker script not executable** — `chmod +x scripts/dispatcher-worker` in the adopting repo, or
  flag it as unbuilt; do not attempt to reimplement its subcommands inline.
- **WIP ceiling hit (`AT_CAPACITY`)** — transient, not a target-specific refusal. Do not retry with
  different arguments; wait for another item to finish and retry the identical dispatch once
  capacity frees up.
- **Launch verification failure** — the returned session id does not appear in `claude agents
  --json` within a few seconds. Read `references/lessons-learned.md`'s Unix-socket-path entry
  before assuming this is transient; keep slug/session-name components short and re-launch with a
  shorter name rather than retrying the identical long one.
- **Blocked state** — never call `AskUserQuestion` from this session; escalate via a plain-text
  reply plus the notification mechanism, leave the lock held, and wait for the requester or the
  user to resolve it.
- **Auth/network failure** — never invent a workaround. Alert, wait, and retry cheaply once told
  the environment is fixed; do not force through it.
