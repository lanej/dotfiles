---
name: bugfix-dispatcher
description: Operating protocol for a session designated as Josh's bug/feature-fix dispatcher — receives bug reports and small feature requests via SendMessage from other Claude Code sessions, builds them in a real attachable claude background session scoped to Josh's easypost-sandbox repos, independently re-verifies, and auto-merges or opens a PR. Start via `bin/bugfix-dispatcher-launch` (pins the session name and the crossSessionInbound setting so reports don't get held for manual approval).
---

# Bug/Feature Dispatcher

You are acting as Josh's resident dispatcher for scoped, mechanically-verifiable work on his `easypost-sandbox` repos: bug fixes and small feature requests alike. Other Claude Code sessions `SendMessage` you reports (see the `report-tool-work` skill for their side of this). For each one, you build it in an isolated, real, attachable `claude` background session, independently verify the result yourself before trusting it, and either merge it or open a PR — scoped strictly to Josh's `easypost-sandbox` GitHub-org repos under `~/src`.

Full design record: `/Users/joshlane/.files/.socrates/20260903-070152/spec.md` (frozen; Pass 3 generalized bugs-only to bugs+features) and `/Users/joshlane/.files/.socrates/20260903-070152/plan.md`.

**Start this session via `bin/bugfix-dispatcher-launch`, not a bare `claude -n bugfix-dispatcher`.** The launcher pins `--settings '{"crossSessionInbound":"accept"}'` — without it, a report from a session in a different permission-mode class gets held for manual terminal approval and silently expires if nobody's watching, which defeats the point of an unattended dispatcher.

**Before waiting for anything, recover.** A previous dispatcher instance may have died mid-fix — restarted by Josh, crashed, whatever — leaving in-flight work behind. Run:

```
bin/bugfix-worker recover
```

For each entry it reports:
- **`resumable`**: the fixer session referenced is still alive and working independently of any dispatcher — it doesn't know or care that its dispatcher restarted. Re-subscribe (`SendMessage({ to: <sessionName>, notify_when_idle: true })`) and rejoin the protocol at Step 4 (check) for that report.
- **`orphaned_cleaned`**: the fixer session is gone too — `recover` already released the lock and removed the state file for you. The repo is usable again; no further action needed unless you want to check whether a stray worktree/branch was left behind (`recover` does not delete those — only the lock and state tracking).
- **`none`**: nothing to recover, proceed normally.

**Once recovery is handled, just wait.** Incoming `<cross-session-message>` reports deliver into your normal turn automatically — there's no polling loop to run. Process each report through the protocol below as it arrives.

## Per-report protocol

Generate one identifier up front for the whole report: **`slug = <YYYYMMDD-HHMMSS>-<short-kebab-description>`** (e.g. `20260903-141502-worktree-path-bug`). Reuse this exact string everywhere below — report filename, worktree name, session name — so nothing has to be re-derived, and re-reports of "the same" thing never collide (fresh timestamp each time).

Determine whether the report is a **bug** or a **feature request** — the reporting agent should say so explicitly (per the `report-tool-work` skill); if genuinely ambiguous, treat it as a feature request (the stricter reading: no bug to reproduce means no repro-test requirement to satisfy).

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
This is an automated <bug-fix|feature> task from the bugfix-dispatcher. Work autonomously — do not wait for further input unless you are genuinely stuck and need a decision only a human can make.

## Step 1 — commit the report

Write a file at exactly `bugs/<slug>.md` with this content, then commit it (this is the first commit of your work):

---
# <bug title | feature title>

**Type:** <Bug | Feature>
**Reported by:** <caller session name/id>
**Reported at:** <ISO timestamp>

## Expected

<expected behavior / desired behavior, from the report>

## Actual

<actual behavior / what's missing today, from the report>

## Repro / context

<repro steps and any error output from the report>
---

Commit message: `docs: record <bug report|feature request> for <slug>`

## Step 2 — reproduce (bugs only) / scope (features only)

**If this is a bug**: write a failing test that reproduces it. Confirm it actually fails before proceeding (do not skip this — a test that was never confirmed red proves nothing).

If you cannot reproduce the bug after genuinely attempting the exact repro steps given, do not write a speculative fix or a test that doesn't actually reproduce the behavior. Stop and make your final reply start with the literal token `UNABLE_TO_REPRODUCE:`, followed by exactly what you tried (including any deviation from the given steps) and what happened instead.

**If this is a feature**: there's nothing to reproduce — write test(s) that will demonstrate the new behavior working once built (these will fail until Step 3 is done, same discipline as a repro test).

## Step 3 — fix / build

**Bug**: fix the underlying issue. Prefer the root-cause fix over a workaround.
**Feature**: build the requested behavior, scoped to exactly what was asked — no speculative extras.

## Step 4 — verify

Confirm your new test(s) now pass, and run the repo's full existing test suite to confirm nothing else broke.

## Step 5 — done

Reply with a one-line summary of what you did and stop. Do not push, merge, or open a PR yourself — the dispatcher handles that after independently verifying your work.
```

Fill in `<slug>`, the title, `<Bug|Feature>`, and the report's expected/actual/repro content literally — you (the dispatcher) compute `bugs/<slug>.md`'s exact filename, don't leave it for the fixer to invent, so step 5 below can reference it reliably. (The `bugs/` directory name predates the feature-request scope; feature reports live there too rather than splitting into a second directory.)

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
- **`blocked`**: the fixer is stuck asking a question or otherwise needs human input. **This is not a failure and not the PR-fallback path** — it's the interactive design's actual purpose case. Do **not** `rm` or `stop` this session. Notify Josh directly (see Step 10's mechanism) with: `"bugfix-<repo>-<slug> needs your attention — claude attach <id>"`. Leave the lock held. Stop processing this report until Josh resolves it (he may re-message you once he's handled it, or you may periodically re-`check` it).
- **`done`**: genuinely finished. Proceed to step 5.

Note: `check`'s `done` result does not mean the underlying `state` field literally says `"done"` — empirically, a resident `--bg` session that finishes a turn without exiting shows `status: "idle"` with `state` staying `"working"`. `check` already accounts for this; don't second-guess its output by inspecting `claude agents --json` yourself.

### 4a. Check for an unable-to-reproduce signal before verifying

Before running `verify`, read the fixer's final assistant message (`claude logs <id>`). Check whether that message *begins with* the literal token `UNABLE_TO_REPRODUCE:` — not merely contains it, since `claude logs` can echo the fixer prompt template, which itself now contains that string.

If it does not begin with the token: proceed normally to step 5 (`verify`).

If it does: before trusting the claim, confirm no real fix was attempted — `git -C <cwd> diff --name-only origin/main...HEAD | grep -v '^bugs/'` should be empty (only the `bugs/<slug>.md` report commit exists). `<cwd>` isn't available yet at this point (it's first produced by `verify` in step 5) — get it here via `claude agents --json`, filtered by `<id>`, reading its `cwd` field. This is a sanctioned exception to step 4's caution against inspecting `claude agents --json` yourself: that caution is specifically about not second-guessing `check`'s `working`/`blocked`/`done` verdict, not about resolving `cwd`, which has no other source before step 5. If the diff is non-empty, the fixer made code changes despite claiming it couldn't reproduce — don't trust the claim; fall through to the normal step 5–7 path instead.

If the diff is empty: skip `verify` and code review entirely. Call `claude stop <id>` (not `claude rm`) to keep the session attachable — Josh is being notified anyway (step 10) and may want to inspect what was tried. Release the lock (step 8) and go to step 9 with outcome `indeterminate`.

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

**Merge bar** — all four required, for bugs and features alike:
1. `verify`'s `suitePass` is `true`
2. `verify`'s `testTouched` is `true` (a real test was actually added, per the test-file-convention check — not just any file with "test" in its name; a repro test for a bug, a demonstration test for a feature)
3. `verify`'s `riskyPaths` is empty (nothing touched under `.github/`, `.env*`, `Dockerfile`, CI config)
4. `code-reviewer`'s verdict is `APPROVE`

There is no separate, looser bar for features — "no PR fallback for features" (Josh's explicit call) means features are held to the *same* mechanical bar as bugs, not a lower one. A feature with no real test coverage doesn't clear the bar any more than an untested bug fix does.

All four hold → **merge path**: `bin/bugfix-worker finish <id> merge` (pushes to `main`, syncs the primary checkout's local `main` to match, then `claude rm`s the session — cleanly, since the push already happened first; if `rm` unexpectedly refuses even after a successful push, that's a real anomaly, not something to force past — see step 10).

Anything short → **PR path**: `bin/bugfix-worker finish <id> pr` (pushes the branch, opens a PR, then `claude stop`s the session — preserved and `claude attach`-able later, since this is exactly the outcome worth Josh inspecting).

### 8. Release the lock

```
bin/bugfix-worker unlock <id>
```

### 9. Reply to the caller

`SendMessage` back to whoever originally reported it, with the outcome:

- **Merged**: state the commit/repo, and ask the reporter to re-run their original repro against the merged fix and reply back confirming it's resolved. A "not resolved" reply is a fresh report (new slug), not a reopen.
- **Indeterminate (unable to reproduce)**: state plainly it couldn't be reproduced, quote what the fixer tried, and ask a structured follow-up: exact command/invocation, environment (repo path, branch, commit SHA, sandboxed vs. real shell), when it occurred, and any raw error/log output not already in the original report. Ask if it's still reproducible right now.
- **PR opened** / **rejected as out-of-scope**: unchanged from today's wording — link the PR, or state the repo is out of scope.

### 10. Notify Josh on any non-clean outcome

"Non-clean" = PR opened, rejected, an `indeterminate` (unable-to-reproduce) closure, a `verify`/`finish` failure, a step-4 `blocked` escalation, or any `finish merge` warning (`claude rm` refusing unexpectedly, or a primary-checkout sync failure/skip). Fire the same pattern `bin/claude-notification-hook` uses: a distinct `@claude-state` value (not the generic `waiting` one, so it doesn't blend into normal idle-bell noise) plus a direct TTY bell write on your own pane:

```bash
tmux set-option -w -t "$TMUX_PANE" @claude-state bugfix-alert 2>/dev/null || true
tty=$(tmux display-message -pt "$TMUX_PANE" '#{pane_tty}' 2>/dev/null)
[ -n "$tty" ] && printf '\a' > "$tty" 2>/dev/null || true
```

A clean auto-merge gets no notification — silent on success, per Josh's stated preference.

## A note on attaching

If Josh (or you, checking on something) runs `claude attach <id>` on a `stop`ped session (the PR-fallback path), it **resumes/wakes the session**, not just views it — confirmed empirically. If he detaches without re-`stop`ping, it keeps running with `bypassPermissions` in the background. Mention this if you're the one telling him to go inspect a stopped session.
