# Config Schema

Every dispatcher instance reads a small per-repo config file — recommended path
`.claude/dispatcher.config.json` in the adopting repo — before handling its first item. Read this
file in full before onboarding a new repo; `scripts/dispatcher-worker start` enforces
`allowedOrigin` itself, but every other field below shapes decisions this protocol makes, so a
missing or wrong value produces a wrong decision, not just a script error.

## Fields

### `allowedOrigin` (required, string — regex or exact match)

The hard security boundary. The resource's git origin URL must match this pattern or
`scripts/dispatcher-worker start` refuses, exits non-zero, and creates nothing. Enforced in the
script itself, not by narration in this skill or in any prompt a dispatched worker receives —
mirrors both bugfix-dispatcher's `easypost-sandbox` org allowlist and infra-dispatcher's exact
two-repo allowlist. Prefer an exact origin match or a narrow org-scoped regex over a broad wildcard
— this is the one field where being permissive defeats the entire point of the boundary.

### `verifyCommand` (required, string)

The shell command that runs this repo's real test suite and/or static checks. Invoked by
`scripts/dispatcher-worker verify` — never by reading the builder's own conversational claim of
"tests pass." Should exit non-zero on any real failure and be runnable from a clean worktree with
no interactive prompts.

### `finishMode` (required, one of `"merge"` | `"pr"` | `"custom"`)

The pluggable apply/finish mechanism, selected per the merge/apply-bar decision in
`worker-protocol.md` step 13:

- `"merge"` — a clean pass pushes directly to the target branch (mirrors bugfix-dispatcher's
  merge path).
- `"pr"` — a clean pass still only opens a PR; nothing auto-merges without an explicit human
  action (mirrors infra-dispatcher's `bootstrap-gha` repo, where nothing can complete without the
  user).
- `"custom"` — delegates to `finishCommand` (see below) for a resource with its own apply
  mechanism (e.g. a `terraform apply`/`atlantis apply` comment, a deploy trigger).

### `finishCommand` (required only when `finishMode` is `"custom"`, string)

The exact command `scripts/dispatcher-worker finish` runs for the custom apply path. Must be
idempotent-safe against a re-invocation on the same slug (mirrors infra-dispatcher's `apply`
script, which refuses a second invocation on the same slug rather than risk duplicating a
side-effecting action — see `lessons-learned.md`).

### `wipCeiling` (optional, integer, default `3`)

The global WIP ceiling — the maximum number of concurrent in-flight items across *all* locked
resources this dispatcher instance tracks, independent of and in addition to the per-resource lock
(see `worker-protocol.md` step 4). `scripts/dispatcher-worker start` exits with a distinct
`AT_CAPACITY` code when this is hit; that refusal is transient and must never be retried with
different arguments, only re-attempted later once capacity frees up.

### `reviewerMode` (optional, one of `"subagent"` | `"separate-session"`, default `"subagent"`)

Selects which review shape `worker-protocol.md` step 12 dispatches:

- `"subagent"` — a same-process code-reviewer subagent, cheaper, appropriate for low-stakes repos.
- `"separate-session"` — a fully separate, freshly-dispatched reviewer session with zero visibility
  into the builder's own reasoning (mirrors infra-dispatcher's reviewer design). Use for
  higher-stakes repos where an independent read matters more than review latency/cost.

### `targetBranch` (optional, string, default `"main"`)

The branch `finish merge` pushes to and `gc` compares worktree commits against
(`git merge-base --is-ancestor`) when deciding whether a session's work is already landed.

### `installCommand` (optional, string, no default — skipped entirely if absent)

A best-effort post-merge install step (e.g. refreshing a compiled binary or launcher script that a
plain `git push` doesn't refresh). Runs from the **primary checkout**, synced forward first via
`git fetch && git merge --ff-only`, never from the worker's own worktree — a worktree is deleted
immediately after a successful merge, and any install artifact that captures its own invocation
directory (a launcher script using its build tool's "current directory" function, for instance)
would be left pointing at a now-deleted path. Only falls back to running from the worktree if the
primary-checkout sync itself fails. A failure here is a warning, never a reason to fail `finish`
itself.

### `reportPathPrefix` (optional, string, default `"bugs/"`)

The path prefix under which each item's request-record file (written in `worker-protocol.md` step
5's prompt template) lives. Excluded from `verify`'s diff/`testTouched`/risky-path computation, so
committing the request record itself never counts as "a real code change" or "a real test."

### `notifyState` (required, string)

A distinct `@claude-state` tmux value this dispatcher instance sets when firing a non-clean-outcome
notification (`worker-protocol.md` step 16.5) — e.g. `bugfix-alert`, `infra-alert`. Must be unique
per dispatcher instance so multiple dispatchers' bell notifications stay distinguishable from each
other and from the generic idle-bell state. Used in the notification pattern:

```bash
tmux set-option -w -t "$TMUX_PANE" @claude-state <notifyState> 2>/dev/null || true
tty=$(tmux display-message -pt "$TMUX_PANE" '#{pane_tty}' 2>/dev/null)
[ -n "$tty" ] && printf '\a' > "$tty" 2>/dev/null || true
```

## Worked example

```json
{
  "allowedOrigin": "^git@github\\.com:easypost-sandbox/widget\\.git$",
  "verifyCommand": "just test",
  "finishMode": "merge",
  "targetBranch": "main",
  "installCommand": "just install",
  "reportPathPrefix": "bugs/",
  "wipCeiling": 3,
  "reviewerMode": "subagent",
  "notifyState": "widget-dispatcher-alert"
}
```

This example matches a `bugfix-dispatcher`-shaped setup: one exact `easypost-sandbox`-org repo over
SSH, a `just test` verify command, direct merge to `main` on a clean pass, a best-effort `just
install` refresh from the primary checkout after merge, request records under `bugs/`, a global cap
of 3 concurrent items across all tracked repos, a lightweight subagent reviewer, and a
dispatcher-specific tmux alert state distinct from any other dispatcher instance's own
`notifyState`.
