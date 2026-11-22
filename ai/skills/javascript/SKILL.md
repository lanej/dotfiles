---
name: javascript
description: Node.js and JavaScript development patterns, gotchas, and library compatibility notes. Use when working with Node.js projects, TypeScript, React, antd, Zustand, Playwright, Bun, or Vitest.
---

# JavaScript / Node.js Skill

Before selecting application tools or an API protocol, read [the project tool-choice policy](../source-code-lifecycle/references/tool-choices.md). Apply the declared authority and adoption at every lifecycle stage, including research; preserve external providers’ protocols and established stacks according to that policy.

Use the installed [testing](../testing/SKILL.md) for proportionate evidence. Language detection installs this guidance; it does not add or replace compiler, test, or CI configuration. Preserve existing repository gates.

## Project Setup Basics

- Always check `package.json` first to understand available scripts before running anything
- Before running or briefing any install/test/lint/build command, check which package manager the repo actually uses — a tracked `pnpm-lock.yaml`/`yarn.lock`/`package-lock.json`, or a `packageManager` field in `package.json` — and use that tool by name. Don't default to `npm` as a generic placeholder; running the wrong manager's install command can generate a stray lockfile and produce a false "this repo is missing X" claim. (detail: memory "feedback_subagent_briefed_wrong_package_manager")
- Run `npm install` (or the repo's actual package manager's install) before attempting to execute Node.js scripts in a new project
- If a user specifies a script to run, use exactly what they specify

## Load task-specific guidance

Read the matching reference before working on these capabilities:

| Task | Read |
| --- | --- |
| Optional peers, React/antd/Zustand compatibility, browser layout, stale diagnostics, Vitest/Bun | [Runtime and testing](references/runtime-and-testing.md) |
| Streaming completion, input recovery, interleaved text and tools | [SSE state](references/sse-streaming.md) |
| MCP transport lifetime, respawn, child-process environment | [MCP stdio](references/mcp-stdio.md) |
| Content collections, MDX, public assets, standalone HTML, dev routing | [Astro](references/astro.md) |
| Fresh or relocated checkout verification | [Worktree runtime lessons](references/worktree-lessons.md) |
