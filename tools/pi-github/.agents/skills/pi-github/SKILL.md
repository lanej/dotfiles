---
name: pi-github
description: Submit and observe jobs in this project's Pi scheduler, including public GitHub PR summaries and the disposable merge-conflict demo. Use when delegating these tasks to the running scheduler or inspecting its queue and state transitions.
---

# Pi GitHub scheduler

Use this repository's `bin/pi-github` executable after `bun run build`. A user runs `bin/pi-github dashboard` in a terminal; Codex submits work from another process. All commands must use the same `--state DIR` when a nondefault state directory is selected.

Submit a public PR with `bin/pi-github submit summarize-pr --url URL --request-id ID --json`. Retain the request ID and returned job ID; retry an uncertain submission with the same request ID rather than generating another one. A reused request ID with different task content is rejected.

Run `bin/pi-github demo --request-id ID --json` to queue the disposable Git conflict followed by the public example PR. The conflict job edits only a generated fixture; it does not repair conflicts in a user's repository.

Use `get JOB --json` for state and result, `events JOB --after SEQUENCE` for bounded transition history, or `events JOB --watch` to follow a job until terminal. Job submission is not completion. `cancel JOB` waits asynchronously for worker exit; inspect state until `cancelled`. `retry JOB` explicitly requeues failed or interrupted work and preserves prior attempts. `pause` prevents new dispatch; `resume` continues it.

Explain `failed` and `interrupted` states using their recorded reason. Recovery can block dispatch until a previous worker PID exits. Never remove ownership files, bypass this fence, or substitute another tool for a denied operation. The worker uses existing Pi authentication or a read-only in-memory reference to the existing file-backed Codex ChatGPT session. Never inspect, print, or copy credentials yourself. Codex owns its session refresh. Use `bin/pi-github login` only if there is no usable existing session.

The first thread supports confirmed public repository PR reads and generated fixture writes. It does not publish comments, create PRs, push branches, or change GitHub configuration. Keep implementation work and project checks in Codex.
