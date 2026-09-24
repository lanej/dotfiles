# Worker Protocol

Full per-item detail for the numbered list in `SKILL.md`'s "Per-report protocol" section. Read
`lessons-learned.md` before handling any failure this document doesn't explicitly resolve, and
`config-schema.md` for the exact per-repo config fields referenced below (`allowedOrigin`,
`verifyCommand`, `finishMode`, `wipCeiling`, `reviewerMode`, `notifyState`).

## 1. Generate a slug

Compute `slug = <YYYYMMDD-HHMMSS>-<short-kebab-description>` once, up front, for the whole item
(e.g. `20260921-141502-worktree-path-bug`). Reuse this exact string everywhere below — report
filename, worktree name, session name — so nothing is re-derived, and a re-report of "the same"
thing never collides (fresh timestamp each time). Keep the description component short: a later
suffix (a reviewer's `-review`/`-reviewer` tag) gets appended to this same slug, and total
worktree-path length is a real constraint — see `lessons-learned.md`'s Unix-socket-path entry.

## 2. Pre-dispatch sanity check

Before calling `start`, grep the target repo for file paths, symbol names, or commands the report
itself cites. A request can describe paths from a different, out-of-scope repo while mislabeling
which repo is the actual target — this check is cheap and has caught real misrouted requests (see
`lessons-learned.md`). If the cited paths/symbols don't exist in the target repo, do not dispatch;
reply that the request appears to target a different repo and ask for confirmation, or route it to
the correct dispatcher if one is known.

## 3. Validate scope + lock

```
scripts/dispatcher-worker start <slug> <prompt-file>
```

The resource is always the current working directory's git repo root — this generic script has no
other repo-specific notion of "resource" to key a lock on, so there is no separate resource
argument. Run it from within the target repo (or point `DISPATCHER_CONFIG` at that repo's config if
invoking from elsewhere).

This is the hard security boundary, enforced in the script itself, not by narration: it checks the
repo's origin (`git remote get-url origin`) against `allowedOrigin` and exits non-zero, nothing
created, if it doesn't match — including a repo with no `origin` remote at all, refused
unconditionally rather than treated as vacuously matching. It also acquires a **per-resource lock**
— one builder→reviewer lifecycle per resource at a time. This is a correctness/serialization
mechanism, not a cost control: without it, two concurrent agents could open conflicting PRs or race
a merge on the same resource.

A single `start` invocation performs three checks in this exact order: `allowedOrigin` first, then
the global WIP ceiling (step 4 below), then the per-resource lock — confirmed live: a second `start`
on a repo already at its `wipCeiling` returns `AT_CAPACITY`, not `BUSY`, even when that repo's own
lock was never contended. Steps 3 and 4 are presented as two conceptual concerns for the
dispatcher's own reasoning, not two separate commands or a guarantee that a lock attempt always
happens first.

- Scope failure (allowlist mismatch) → reply that the resource is out of scope. Stop. Do not
  proceed to any other step.
- `BUSY` exit (another item already holds this resource's lock) → wait roughly 30 seconds and
  retry `start` again (a second attempt), rather than failing the report outright.

## 4. Check the global WIP ceiling

Distinct from the per-resource lock above. The **global WIP ceiling** (`wipCeiling` in config) caps
total concurrent in-flight items across *all* locked resources combined — it exists to bound total
agent fan-out and cost, not to serialize any one resource. A dispatcher tracking work across many
repos/resources can have every individual resource lock free while still being at global capacity.

`scripts/dispatcher-worker start` enforces this itself and exits with a distinct `AT_CAPACITY`
code (mirroring matrix-dispatcher's exit `7`) when the ceiling is hit. This refusal is transient
and target-agnostic — it says nothing about whether this particular resource/request is
trustworthy, unlike an `allowedOrigin` scope refusal, which is permanent for that combination.
Never retry an `AT_CAPACITY` refusal with different arguments hoping something sticks; wait for
another item to finish and retry the identical dispatch once capacity frees up.

## 5. Write the builder's prompt to a temp file

Never inline a multi-line report into command argv — quotes, backticks, and newlines in a raw bug
report or feature request are a shell-quoting hazard. Write it to a real temp file first. At
minimum the prompt should instruct the builder to: work autonomously; commit a record of the
request itself as its first commit; reproduce/scope the change with a test before building
(bugs: a failing repro test, confirmed red; features: a demonstration test that fails until built);
build the change; verify locally; reply with a one-line summary and stop without pushing, merging,
opening a PR, or applying — the dispatcher handles that after independent verification. Include an
explicit "if you cannot proceed, stop and reply starting with the literal token `UNABLE_TO_BUILD:`
(or `UNABLE_TO_REPRODUCE:` for a bug), followed by exactly what you tried" instruction — see step
10 below for why this exact literal-prefix convention matters.

## 6. Launch

`start` (step 3) launches the builder via:

```
claude -w <slug> --bg -n <session-name> --permission-mode bypassPermissions <prompt-file>
```

`bypassPermissions` is required for genuine autonomy; the resource-scope lock from step 3 is what
makes this safe, not narration in the builder's prompt.

## 7. Immediately verify the launch actually succeeded

Do not trust the id `start` returns. Within a few seconds of launch, confirm the session actually
exists:

```
claude agents --json
```

Filter for the session name/id just launched. If it is absent, treat the launch as failed — see
`lessons-learned.md`'s Unix-socket-path entry for the most common real cause and its fix (shorten
the slug/session-name components, re-launch with a new short name; do not blindly retry the
identical long name).

## 8. Subscribe immediately

```
SendMessage({ to: "<session-name>", notify_when_idle: true })
```

This must happen right after a *confirmed* launch (step 7), not later. `notify_when_idle` is
edge-triggered on a transition into idle — subscribing after a session is already sitting idle does
not fire retroactively.

## 9. On notification, confirm real completion

```
scripts/dispatcher-worker check <id>
```

Returns one of `working`, `blocked`, or `done`.

- `working` — the notification fired but the session isn't actually idle yet, or fired for an
  unrelated reason. Re-subscribe with `notify_when_idle` and wait again. Do not proceed.
- `blocked` — the worker is stuck asking a question or otherwise needs human input. **This is not
  a failure and not the fallback path — it is the interactive design's actual purpose case.** Do
  not stop or remove this session. Escalate to the user (plain-text reply plus the notification
  mechanism from `config-schema.md`'s `notifyState`). Leave the lock held. Stop processing this
  item until the escalation resolves.
- `done` — genuinely finished. Proceed to step 10.

A session can also notify twice for the same idle transition (its own proactive cross-session
message, plus the harness's own notice) — dedupe by checking whether this idle transition was
already processed; do not treat a second notification as new work.

A dispatched worker session is independently addressable by anyone with `ListAgents`/`SendMessage`
access, not exclusively by its dispatcher — it can receive an unrelated message mid-task from some
other peer session. Account for this when interpreting an unexpected state change.

## 10. Check for an unable-to-build/reproduce signal before verifying

Read the builder's final assistant message. Check whether it *begins with* the literal token
`UNABLE_TO_BUILD:` or `UNABLE_TO_REPRODUCE:` — not merely contains it, since the prompt template
itself may echo that string.

If it does not begin with the token: proceed normally to step 11.

If it does: before trusting the claim, confirm no real change was attempted (the diff against the
base branch, excluding the request-record file committed in step 5's template, should be empty).
If the diff is non-empty despite the claim, do not trust it — fall through to the normal step
11–13 path instead. If the diff is genuinely empty: skip verify and review entirely, stop (not
remove) the session so it stays attachable, release the lock, and go to closeout with an
`indeterminate` outcome.

## 11. Independently re-verify

```
scripts/dispatcher-worker verify <id>
```

This re-runs the resource's actual `verifyCommand` and inspects the real diff — it does not read
anything the builder *said*. Treat its structured output (suite pass/fail, whether a real test was
added, which paths were touched) as the only source of truth for the decision bar in step 13. The
builder's own conversational claims of "tests pass" are informational at most, never trusted
programmatically.

## 12. Dispatch a reviewer

Two options, chosen per `reviewerMode` in config:

- **`subagent`** (lighter default) — a same-process code-reviewer subagent reviewing the diff in
  the builder's own worktree. Cheaper, appropriate for low-stakes repos.
- **`separate-session`** — a fully separate, freshly-dispatched reviewer session with zero
  visibility into the builder's own reasoning or conversation, reading only the diff, the request
  record, and the verify/static-analysis output cold. Appropriate for higher-stakes repos (e.g.
  infrastructure) where an independent read matters more than review latency/cost.

Either way, the reviewer's prompt must explicitly forbid it from taking any side-effecting action
(merge, apply, push to the target branch) on its own — its job ends at a verdict, and, for a
`separate-session` reviewer that config designates as allowed to trigger the finish step directly
(mirroring infra-dispatcher's `apply`), that action happens through the same worker script the
dispatcher itself would call, never an ad hoc command the reviewer invents.

## 13. Decide via the merge/apply bar

All criteria required, no partial credit — mirror bugfix-dispatcher's exact structure:

1. The resource's real test/check suite passes (`verify`'s output, not the builder's claim).
2. A real test was actually added — a genuine repro/demonstration test per the resource's own
   test-file convention, not just any file with "test" in its name.
3. No risky paths were touched (CI config, `.env*`, Dockerfiles, or whatever `config-schema.md`'s
   resource-specific risky-path list defines).
4. The reviewer's verdict is a clean approval — not a conditional or partial one.

There is no separate, looser bar for a feature request versus a bug fix, and no partial credit for
3 of 4 criteria. Anything short of all four routes to the non-clean closeout path (PR instead of
merge, hold instead of apply) per `finishMode`.

## 14. Independently check real state after any completion claim

After *any* claim of completion — from the builder or from the reviewer — independently check the
actual resulting state before trusting it. Two real, distinct failure modes to check for
explicitly (see `lessons-learned.md` for the incidents that established this):

- A reviewer reaches a valid verdict, writes findings, but never actually calls the side-effecting
  apply/merge step it was supposed to trigger — check that the mutating action was actually
  invoked, not just that a verdict was written.
- A reviewer calls that step, gets a "success" response, but never checks whether the thing it
  triggered (a CI run, an apply) actually succeeded — check the triggered action's own real
  outcome (CI status, apply result), not just the API call's return code.

## 15. Repeat-failure escalation cap

Track failure signature (not just failure count) across attempts on the same item. On the second
occurrence of an *identical* recurring failure signature, one more attempt is allowed; on the
third occurrence of that same signature, stop retrying and escalate to the user as a policy
question instead — a recurring identical failure class usually needs a different recovery strategy
than a blind retry (see `lessons-learned.md`'s CI-flakiness entry), and repeatedly re-patching the
same failure without escalating hides a systemic problem from the person who can actually decide
how to handle it.

## 16. Closeout sequence, in exact order

1. **Finish** — merge, open a PR, or apply, per `finishMode` in config (`custom` uses
   `finishCommand`). For a PR, have `pull-request-writer` write the description to a file first
   and pass it: `scripts/dispatcher-worker finish <id> pr <file>`. This is the only step that mutates the target branch/environment.
2. **Unlock** — `scripts/dispatcher-worker unlock <id>`, always, regardless of outcome.
3. **Immediate session cleanup** (not deferred to a later batch pass):
   - **PR path** (opened but not yet merged/applied) → `claude stop <id>`. Never `rm` — the
     session must stay attachable until the change resolves.
   - **Merge path** (pushed/applied successfully) → `claude rm <id>` immediately, right after the
     successful push/apply.
   - **Periodic idle-heartbeat sweep** — run `scripts/dispatcher-worker gc` on a recurring
     schedule (not a "clean up later" one-off task) to check every tracked-but-idle session and
     `claude rm` any whose worktree commits are already fully contained in the target branch
     (`git merge-base --is-ancestor <worktree-head> <target-branch>`).
   - **Never force past `claude rm`'s own unpushed-commit refusal.** It lists the offending SHAs
     and requires an explicit `--discard-unpushed <sha>@<sha>` flag to proceed. Investigate why
     those commits are unpushed before ever using that flag — never use it automatically or as a
     default unblock step.
4. **Reply** to the original requester with the outcome, stated plainly (merged/PR
   opened/rejected-out-of-scope/indeterminate, with next steps if any).
5. **Notify** the user, but only on a non-clean outcome (PR opened, rejected, indeterminate, a
   `blocked` escalation, an unresolved repeat-failure escalation, or any finish-step warning). A
   clean auto-merge/apply is silent — no notification.

Emit one status line at each real state transition throughout this whole protocol (dispatch,
verify-result, review-dispatch, review-verdict, closeout, CI-result) rather than saving everything
for a single final message — a resident dispatcher with no attached terminal watcher needs these
breadcrumbs for anyone inspecting it mid-flight.
