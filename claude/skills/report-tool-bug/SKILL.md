---
name: report-tool-bug
description: Report a bug in one of Josh's easypost-sandbox tool/MCP-server repos (bigquery, jira, kagi, gspace, dora, epq, and similar) to the bugfix-dispatcher session instead of working around it inline. Use when a tool, CLI, or MCP server under Josh's easypost-sandbox GitHub org is clearly broken and fixing it isn't part of your current task.
---

# Report a Tool Bug to the Dispatcher

If you hit a bug in a tool, script, or MCP server that lives in one of Josh's `easypost-sandbox` GitHub-org repos under `~/src` — and fixing it isn't your job right now — don't work around it silently and don't drop it. Report it to the `bugfix-dispatcher` session.

## When to use this

- A CLI, script, or MCP server under `~/src/<repo>` (where `<repo>`'s git remote is `easypost-sandbox/*`) produces incorrect output, errors, or crashes in a way that's clearly a bug in that tool, not a misuse on your part.
- Fixing it is out of scope for what you're currently doing.

## When NOT to use this

- The repo isn't an `easypost-sandbox` repo (check `git -C ~/src/<repo> remote get-url origin` if unsure) — the dispatcher only acts on that allowlist and will reject anything else.
- You're already the one fixing it as your actual task — just fix it directly.
- It's a one-off user error, not a tool bug.

## How to report

Call `SendMessage` addressed to the session named `bugfix-dispatcher`:

```
SendMessage({
  to: "bugfix-dispatcher",
  summary: "<repo>: <one-line bug title>",
  message: "Bug report for <repo>.\n\nExpected: <what should happen>\nActual: <what actually happens>\nRepro: <exact command/steps, if you have them>\nContext: <any error output, stack trace, or relevant detail>"
})
```

Include the exact repo name (matching its directory under `~/src`), and be concrete about expected vs. actual — this becomes the committed bug-report record the fix is built against, so vague reports produce vague fixes.

## After reporting

Don't block your own task waiting for a reply. The dispatcher works asynchronously and will reply with the outcome (fixed and merged, PR opened, or rejected as out of scope) whenever it's done — often well after you've moved on. If the `bugfix-dispatcher` session isn't currently running, the message simply won't be delivered; there's no queue. That's a known, accepted limitation — retry later or mention it to Josh directly if the bug is urgent.
