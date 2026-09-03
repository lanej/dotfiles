---
name: bugfix-dispatcher
description: Operating protocol for a session designated as Josh's bug-fix dispatcher — receives bug reports via SendMessage from other Claude Code sessions, fixes them in a real attachable claude background session scoped to Josh's easypost-sandbox repos, independently re-verifies, and auto-merges or opens a PR. Invoke once in a session started specifically to act as the dispatcher (e.g. `claude -n bugfix-dispatcher`).
---

# Bug Fix Dispatcher

You are acting as Josh's resident bug-fix dispatcher. Other Claude Code sessions `SendMessage` you bug reports (see the `report-tool-bug` skill for their side of this). For each one, you fix it in an isolated, real, attachable `claude` background session, independently verify the fix yourself before trusting it, and either merge it or open a PR — scoped strictly to Josh's `easypost-sandbox` GitHub-org repos under `~/src`.

Full design record: `/Users/joshlane/.files/.socrates/20260903-070152/spec.md` (frozen v4) and `/Users/joshlane/.files/.socrates/20260903-070152/plan.md`.

**Once you invoke this skill, just wait.** Incoming `<cross-session-message>` bug reports deliver into your normal turn automatically — there's no polling loop to run. Process each report through the protocol below as it arrives.

## Per-report protocol

Generate one identifier up front for the whole report: **`slug = <YYYYMMDD-HHMMSS>-<short-kebab-description>`** (e.g. `20260903-141502-worktree-path-bug`). Reuse this exact string everywhere below — bug-report filename, worktree name, session name — so nothing has to be re-derived, and re-reports of "the same" bug never collide (fresh timestamp each time).

### 1. Validate scope + lock

```
bin/bugfix-worker start <repo> <slug> <prompt-file>
```

This is the hard security boundary — enforced in the script itself, not here. It checks the repo's origin against the `easypost-sandbox` org and exits non-zero (nothing created) if it doesn't match, and acquires a per-repo lock (fails with a "BUSY" exit if a fix is already in flight for that repo — treat this as "wait and retry shortly," not a failure).

If it exits non-zero for the allowlist reason: reply to the caller that the repo is out of scope. Stop. Do not proceed to any other step.

If it exits with BUSY: wait ~30s and retry `start` again (a second `mkdir` attempt) rather than failing the report outright.

### 2. Write the fixer's prompt to a temp file first

Before calling `start`, write the prompt content to a temp file — **never inline it into command argv** (multi-line bug reports containing quotes/backticks are a shell-quoting hazard). Template:

```markdown
This is an automated bug-fix task from the bugfix-dispatcher. Work autonomously — do not wait for further input unless you are genuinely stuck and need a decision only a human can make.

## Step 1 — commit the bug report

Write a file at exactly `bugs/<slug>.md` with this content, then commit it (this is the first commit of your work):

---
# <bug title>

**Reported by:** <caller session name/id>
**Reported at:** <ISO timestamp>

## Expected

<expected behavior, from the report>

## Actual

<actual behavior, from the report>

## Repro / context

<repro steps and any error output from the report>
---

Commit message: `docs: record bug report for <slug>`

## Step 2 — reproduce

Write a failing test that reproduces the bug described above. Confirm it actually fails before proceeding (do not skip this — a test that was never confirmed red proves nothing).

## Step 3 — fix

Fix the underlying bug. Prefer the root-cause fix over a workaround.

## Step 4 — verify

Confirm your new test now passes, and run the repo's full existing test suite to confirm nothing else broke.

## Step 5 — done

Reply with a one-line summary of what you fixed and stop. Do not push, merge, or open a PR yourself — the dispatcher handles that after independently verifying your work.
```

Fill in `<slug>`, the bug title, and the report's expected/actual/repro content literally — you (the dispatcher) compute `bugs/<slug>.md`'s exact filename, don't leave it for the fixer to invent, so step 5 below can reference it reliably.

### 3. Launch, then subscribe before it can go idle

`start` (step 1) already launches the fixer via `claude -w <slug> --bg -n bugfix-<repo>-<slug> --permission-mode bypassPermissions` and prints its `<id>`. Immediately — before it has any chance to go idle — subscribe:

```
SendMessage({ to: "bugfix-<repo>-<slug>", notify_when_idle: true })
```

This must happen right after launch, not later: `notify_when_idle` is edge-triggered on a transition into idle, confirmed empirically — subscribing after a session is already sitting idle does not fire retroactively.

### 4. On notification, confirm real completion before doing anything else

```
bin/bugfix-worker check <id>
```

Returns one of `{"result":"working"}`, `{"result":"blocked"}`, or `{"result":"done"}`.

- **`working`**: the notification fired but the session isn't actually idle yet (or fired for an unrelated reason) — re-subscribe with `notify_when_idle` and wait again. Do not proceed.
- **`blocked`**: the fixer is stuck asking a question or otherwise needs human input. **This is not a failure and not the PR-fallback path** — it's the interactive design's actual purpose case. Do **not** `rm` or `stop` this session. Notify Josh directly (see Step 8's mechanism) with: `"bugfix-<repo>-<slug> needs your attention — claude attach <id>"`. Leave the lock held. Stop processing this report until Josh resolves it (he may re-message you once he's handled it, or you may periodically re-`check` it).
- **`done`**: genuinely finished. Proceed to step 5.

Note: `check`'s `done` result does not mean the underlying `state` field literally says `"done"` — empirically, a resident `--bg` session that finishes a turn without exiting shows `status: "idle"` with `state` staying `"working"`. `check` already accounts for this; don't second-guess its output by inspecting `claude agents --json` yourself.

### 5. Independently re-verify — never trust the fixer's self-report

```
bin/bugfix-worker verify <id>
```

Returns `{"cwd", "suitePass", "testTouched", "riskyPaths", "logFile"}`. This re-runs the repo's actual test command and checks the real diff — it does not read anything the fixer *said*. Treat `suitePass`/`testTouched`/`riskyPaths` as the only source of truth for the merge bar; the fixer's own conversational claims of "tests pass" are informational at most (worth reading via `claude logs <id>` if something looks off, never trusted programmatically).

### 6. Independent code review

```
Agent({
  subagent_type: "code-reviewer",
  description: "Review bugfix for <repo>/<slug>",
  prompt: "Review the fix at <cwd from step 5> for the bug described in bugs/<slug>.md in that worktree. This is a small tool repo — ignore the coverage-percentage checklist item entirely; focus on whether the fix is correct and doesn't introduce regressions. Read the diff against origin/main to scope your review."
})
```

Look for its `**Overall Assessment**: [APPROVE / REQUEST CHANGES / BLOCK]` line (bolded, near the top of its output, not at the end).

### 7. Decide

**Merge bar** — all four required:
1. `verify`'s `suitePass` is `true`
2. `verify`'s `testTouched` is `true` (a real repro test was actually added, per the test-file-convention check — not just any file with "test" in its name)
3. `verify`'s `riskyPaths` is empty (nothing touched under `.github/`, `.env*`, `Dockerfile`, CI config)
4. `code-reviewer`'s verdict is `APPROVE`

All four hold → **merge path**: `bin/bugfix-worker finish <id> merge` (pushes to `main`, then `claude rm`s the session — cleanly, since the push already happened first; if `rm` unexpectedly refuses even after a successful push, that's a real anomaly, not something to force past — see step 8).

Anything short → **PR path**: `bin/bugfix-worker finish <id> pr` (pushes the branch, opens a PR, then `claude stop`s the session — preserved and `claude attach`-able later, since this is exactly the outcome worth Josh inspecting).

### 8. Release the lock

```
bin/bugfix-worker unlock <id>
```

### 9. Reply to the caller

`SendMessage` back to whoever originally reported the bug, with the outcome: merged (link the commit), PR opened (link the PR), or rejected as out of scope.

### 10. Notify Josh on any non-clean outcome

"Non-clean" = PR opened, rejected, a `verify`/`finish` failure, a step-4 `blocked` escalation, or a `finish merge` warning about `claude rm` refusing unexpectedly. Fire the same pattern `bin/claude-notification-hook` uses: a distinct `@claude-state` value (not the generic `waiting` one, so it doesn't blend into normal idle-bell noise) plus a direct TTY bell write on your own pane:

```bash
tmux set-option -w -t "$TMUX_PANE" @claude-state bugfix-alert 2>/dev/null || true
tty=$(tmux display-message -pt "$TMUX_PANE" '#{pane_tty}' 2>/dev/null)
[ -n "$tty" ] && printf '\a' > "$tty" 2>/dev/null || true
```

A clean auto-merge gets no notification — silent on success, per Josh's stated preference.

## A note on attaching

If Josh (or you, checking on something) runs `claude attach <id>` on a `stop`ped session (the PR-fallback path), it **resumes/wakes the session**, not just views it — confirmed empirically. If he detaches without re-`stop`ping, it keeps running with `bypassPermissions` in the background. Mention this if you're the one telling him to go inspect a stopped session.
