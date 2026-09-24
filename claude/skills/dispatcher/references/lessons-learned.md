# Lessons Learned

Concrete incidents from the three production dispatchers this skill generalizes from. Each entry
names its source and the failure mode fast — read this before treating any dispatcher failure as
novel; it has very likely already happened to a sibling dispatcher.

## Unix-socket worktree-path length (infra-dispatcher)

`claude -w <name> --bg` can fail silently once the total worktree path pushes past roughly
108–136 bytes — the Unix domain socket `sun_path` limit the harness's own IPC relies on. The
launch call returns a plausible-looking session id, but no worktree is actually created, no logs
are written, and `claude logs <id>` reports "job not found" within seconds. This has bitten
`infra-dispatcher` specifically on **reviewer** dispatch: its reviewer session name/worktree slug
appends a `-review`/`-reviewer` suffix (`review_slug = f"{slug}-review"`,
`session_name = f"infra-{short}-{slug}-reviewer"`) onto a slug that was already close to the edge,
pushing the total path over the limit exactly where the builder's own (shorter) launch had
succeeded moments earlier.

**Fix:** keep every slug and session-name component short — roughly 15–20 characters each,
including any suffix a later stage (reviewer, review-slug) will append — and always verify a
launch actually created a real session by checking `claude agents --json` for it within a few
seconds, rather than trusting the id `start`/`claude -w --bg` returns. See `worker-protocol.md`
steps 1 and 7.

## `notify_when_idle` double-notification

A session can notify twice for the same idle transition: once via its own proactive
cross-session message, once via the harness's own idle notice. Dedupe by checking whether this
particular idle transition has already been processed for this item — do not treat the second
notification as a new, independent event requiring a fresh `check`.

## `notify_when_idle` is edge-triggered, not retroactive

Confirmed across bugfix-dispatcher, infra-dispatcher, and matrix-dispatcher's own peer-relay
subscription: subscribing after a session is already sitting idle does not fire. Subscription must
happen immediately after a *confirmed* launch (worker-protocol.md steps 7–8), never "whenever
convenient" or as a later cleanup step.

## A dispatched worker is independently addressable by anyone

A builder or reviewer session dispatched by this protocol is reachable by any other session with
`ListAgents`/`SendMessage` access — not exclusively by its own dispatcher. It can receive an
unrelated message mid-task from some other peer session entirely outside this protocol's control.
Don't assume an unexpected state change in a worker's transcript necessarily traces back to this
dispatcher's own prompt.

## Reviewer self-reports can be individually true but collectively misleading (bugfix-dispatcher, infra-dispatcher)

Two distinct, both-real failure modes, confirmed live in production:

- A reviewer reaches a valid verdict, writes findings, and never actually calls the
  side-effecting apply/merge step it was supposed to trigger.
- A reviewer calls that step, receives a "posted successfully" response, and never checks whether
  the thing it triggered (a CI run, an `atlantis apply`) actually succeeded.

Confirmed live example (infra-dispatcher, PR #125): a sandboxed `apply` invocation crashed *after*
posting a findings comment to the PR; a blind retry would have duplicated it. The apply script now
refuses a second invocation on the same slug for exactly this reason.

Confirmed live example (bugfix-dispatcher, 2026-09-10): a merge-path fix was reported "done" off a
clean local `verify` alone, while its own new regression test was failing on the target branch's
post-merge CI the entire time — a local pass is not proof of a CI pass once a repo has ever shown
local/CI divergence.

**Fix:** always independently check the real resulting state after any completion claim — from a
builder or a reviewer — per worker-protocol.md step 14. Never treat a verdict or an API "success"
response as proof the underlying mutation actually happened and actually worked.

## CI/runner flakiness needs a different recovery than a blind retry (bugfix-dispatcher)

Some failure classes cannot be fixed by retrying the same action — e.g. an apply-only retry cannot
fix a "provider not cached" error; only a fresh plan-then-apply resolves it. Confirmed live
(bugfix-dispatcher, 2026-09-10): a job-level "pre-existing failure" classification is only a
job-granularity signal, not proof the *specific* failing tests are unchanged — a "fix" for an
apparently pre-existing failure landed, still showed the same job-level "pre-existing"
classification on the next run, and turned out not to have fixed anything. An *identical, stable*
failure set recurring across multiple runs (including after a supposed fix) is closer to a real,
deterministic, environment-specific defect than to random flakiness — don't over-conclude "harmless
flakiness" just because two runs of an identical commit produced different failing-test sets
either; that's evidence of instability, not evidence any given failure is safe to ignore.

**Fix:** the repeat-failure escalation cap in worker-protocol.md step 15 — a third occurrence of an
identical failure signature is a policy question for the user, not something to keep silently
re-patching.

## Shared-mutation-target ordering gotcha

One broken or unmerged sibling change in a shared root/target can block, or falsely implicate, an
unrelated apply/merge triggered by this dispatcher's own change — even when this change's own diff
is completely correct in isolation. Before triggering any mutating action (merge, apply), check
whether anything else in the same shared scope (a shared Terraform root, a shared branch) is
already broken, not just whether this item's own diff is clean.

## Cross-repo scope-mismatch in relayed requests (infra-dispatcher)

A relayed request can cite file paths from a different, out-of-scope repo while mislabeling which
repo is the actual target. Confirmed live: this exact grep-before-dispatch check (worker-protocol.md
step 2) caught two real mislabeled-repo requests in a single day. Cheap to run, worth running on
every incoming item, not just ones that look suspicious.

## Never call `AskUserQuestion` from a headless dispatcher (infra-dispatcher)

A resident dispatcher session runs headless, with no attached human to answer a blocking
`AskUserQuestion` prompt. Confirmed live: a pending `AskUserQuestion` call cannot be resolved by
`SendMessage` (a message sent to a session with one pending is never processed — it neither answers
the question nor even gets read), and the only way out short of a manual kill/restart is `claude
attach`, which itself risks waking a stopped session unexpectedly (see the attaching note below).
Escalate any decision that's genuinely the user's call via a plain-text reply plus the notification
mechanism instead — never via `AskUserQuestion`.

## Never force through an auth/network failure

An SSH agent that's lost its identities, an expired token, or a DNS/network failure should never be
worked around by inventing a substitute credential path or a creative bypass. Alert, wait, and
retry cheaply once told the environment has actually been fixed.

## `claude attach <id>` on a stopped session resumes it, not just views it

Confirmed empirically across bugfix-dispatcher and infra-dispatcher: attaching to a `stop`ped
session wakes/resumes it rather than opening a read-only view. If the person attaching detaches
without re-`stop`ping it, it keeps running with `bypassPermissions` in the background. Always
mention this caveat when directing anyone to go inspect a stopped builder/reviewer session.

## `recover` reporting "none" doesn't mean there's nothing to resume (jira-dispatcher, 2026-09-21)

Confirmed live: a previous session died after a builder finished and a PR was opened, but before
`finish` was ever called — losing the state-file entry `recover` depends on. `recover` correctly
reported no in-flight state; a real, actionable orphaned PR (green CI, unreviewed) sat open on
GitHub the whole time regardless. A second, unrelated orphaned PR (a bootstrap smoke test) was also
found this way.

**Fix:** `recover`'s "none" is a claim about this script's own state directory, not about actual
repo/GitHub state. On dispatcher start, also independently cross-check: any open PR on a branch
matching this repo's dispatcher naming convention, any worktree under `.claude/worktrees/` not
accounted for by `recover`'s output. Treat a found discrepancy as a normal item to resume via
worker-protocol.md steps 11–16 — independently re-verify, dispatch review, apply the merge bar
(including its CI/infra-self-fix carve-out) — without asking the user first; the same verification
machinery that establishes trust in a live item is sufficient to establish trust in a recovered one.
Reserve escalation for what the bar genuinely can't resolve mechanically (no way to independently
confirm what step a recovered item reached, or a real policy question left after applying the bar
and its carve-outs) — not for ambiguity the protocol's own tools already know how to settle.

An interactively-attached dispatcher session (a human is present and can answer) is not an
exemption from this — the point isn't that no one's available to ask, it's that asking is the wrong
default when the protocol already has a mechanical answer. Default to resolving via the existing
verification/review machinery first; reach for `AskUserQuestion` only for what's left after that
machinery is exhausted.

Cleanup after a recovered item's merge can look like it hit the same gap: `claude rm <name>` (using
the session's display *name*, e.g. a slug) can report no matching job even for a genuinely-exited
session. **Corrected after further testing (same day):** this was a misuse, not a real gap —
`claude rm`/`claude stop`/`claude agents` all key on the short *id* (e.g. `8d3ea16b`), not the
display name, and a fully-exited session only shows up in `claude agents --json` with `--all` (the
default view omits completed/exited jobs). `claude agents --json --all`, filtered for the name, then
`claude rm <id>` on the id it returns, worked cleanly on two already-worktree-deleted sessions,
including correctly reporting the (already-gone) worktree path. Always resolve name → id via
`--all` before concluding a session is untrackable; only fall back to manual `git worktree unlock` +
`remove --force` + `branch -D` if `claude rm <id>` (the *right* id) itself still fails.

## Per-resource lock contention is a real, load-bearing serialization, not a bug

One builder→reviewer lifecycle per resource at a time (worker-protocol.md step 3) is intentional —
it prevents two concurrent agents from racing a merge or opening conflicting PRs on the same
resource. In practice, roughly two concurrent lifecycles across two independent resources is the
natural achievable ceiling before manual juggling gets painful. Never try to fight a single
resource's lock for three or more concurrent lifecycles — that pressure means the request stream
for that resource needs to be queued or throttled upstream, not that the lock should be loosened.
