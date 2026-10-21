---
name: report-tool-work
description: "Report a bug or request a feature in one of Josh's easypost-sandbox tool/MCP-server repos to the bugfix-dispatcher session instead of working around it inline or building it directly. Use when a tool, CLI, or MCP server under Josh's easypost-sandbox GitHub org is broken, or when it's missing something it should have, and fixing/building it isn't part of the current task."
---

# Report a Bug or Feature Request to the Dispatcher

If you hit a bug, or notice something missing, in a tool, script, or MCP server that lives in one of Josh's `easypost-sandbox` GitHub-org repos under `~/src` — and fixing or building it isn't your job right now — don't work around it silently and don't drop it. Report it to the `bugfix-dispatcher` session (the name predates the feature-request scope; it handles both).

## When to use this

- A CLI, script, or MCP server under `~/src/<repo>` (where `<repo>`'s git remote is `easypost-sandbox/*`) produces incorrect output, errors, or crashes in a way that's clearly a bug in that tool, not a misuse on your part — **or** it's missing a capability that would clearly help and is small enough to build without a design discussion.
- Fixing or building it is out of scope for what you're currently doing.
- This applies just as much when a sub-agent surfaces the bug in its own report as when you hit it directly — a sub-agent has no path to `bugfix-dispatcher` itself, so relaying its finding to Josh in your summary is not a substitute for sending the report yourself. Send it in the same turn you tell Josh about it. (detail: memory "feedback_tool_bug_flagged_not_reported_to_dispatcher")

## When NOT to use this

- The repo isn't an `easypost-sandbox` repo (check `git -C ~/src/<repo> remote get-url origin` if unsure) — the dispatcher only acts on that allowlist and will reject anything else.
- You're already the one fixing/building it as your actual task — just do it directly.
- It's a one-off user error, not a tool bug.
- The feature is large, ambiguous, or needs product/design judgment calls beyond "here's the behavior I want" — this path has no design-review step; it's for scoped, mechanically-verifiable work only.

## How to report

For a **bug**, first invoke `bug-reporter` as a separate subagent with the exact repository, dispatcher destination, observed failure, and supplied evidence. Follow `~/.files/docs/bug-reports.md`. Its only job is to report; do not ask it to investigate, reproduce, fix, or send the message. Missing reproduction alone is not a blocker. Encourage load bearing supplied screenshots, diagrams, and output; avoid redundant prose. Resolve its blockers and use its title and body, excluding the handoff-only `blockers:` line. If named selection is unavailable, use a generic drafting-only agent with the shared `~/.files/ai/agents/bug-reporter.md` definition or installed Codex instructions; report the delegation gap if neither is available.

Feature requests retain the direct reporting format below. An unchanged reporter-approved bug draft can be reused; substantive revisions require a new reporter pass.

Call `SendMessage` addressed to the session named `bugfix-dispatcher`:

```
SendMessage({
  to: "bugfix-dispatcher",
  summary: "<repo>: <one-line title>",
  message: "<Bug report|Feature request> for <repo>.\n\nExpected: <what should happen / what you want it to do>\nActual: <what actually happens / what's missing today>\nRepro: <exact command/steps, if you have them>\nContext: <any error output, stack trace, or relevant detail>"
})
```

State plainly which kind it is (bug vs. feature) — the dispatcher's merge bar differs slightly: a bug fix needs a test that reproduces the reported bug; a feature needs tests that demonstrate the new behavior. Include the exact repo name (matching its directory under `~/src`), and be concrete about expected vs. actual — this becomes the committed report the work is built against, so vague reports produce vague results. Reproduction is the fixer's responsibility; do not invent reporting steps or relabel a bug because no reproduction was supplied.

## After reporting

Check the send result and distinguish successful message delivery from a drafted report or a failed send. Don't block your own task waiting for a repair reply. The dispatcher works asynchronously and will reply with the outcome (merged, PR opened, or rejected as out of scope) whenever it's done — often well after you've moved on. If the `bugfix-dispatcher` session isn't currently running, the message simply won't be delivered; there's no queue. That's a known, accepted limitation — report the delivery gap, retry later or mention it to Josh directly if it's urgent.
