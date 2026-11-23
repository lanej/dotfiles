# Resume coordinator work

Start here, then read the [standing instructions](INSTRUCTIONS.md) and [curated lessons](LESSONS.md). Use the following records to resume work.

1. In a configured Pi session, `/tasks` shows the native bead ID. In a Paseo coordinator’s `task_reports` inbox, use the report’s host and task UUID to locate the task. For a task created through Paseo, its bead ID is `tasks-<task-UUID>` in that host’s configured Beads project. Read the accepted brief, assignee, status, evidence and next action. On a configured Pi host, `studio tasks <bead-id> --json` also shows the latest execution attempt recorded there.
2. Confirm the bound conversation on the execution host before resuming the worker. For Paseo-managed Pi work, read the coordinator’s `task_reports` inbox for outstanding questions, blockers and decisions. Recheck the current task if a report describes an earlier assignment. Use native agent tools for Codex workers and Paseo task tools for Paseo-managed Pi workers.
3. For a linked PR, inspect `octo-manager --full pr show <PR-URL>` for the registered owner, current head, checks and review feedback. Confirm the owning session can receive events. If a required record or host is unavailable, report what is missing and arrange a supported handoff before dispatch.

## PR ownership

Each worker publishes and enrolls its PR through Octo Manager under its own session. The coordinator routes actionable feedback to that worker. The worker handles reviews, failed checks and conflict repairs under the target repository’s guidance. Octo Manager coordinates conflicts and authorized merges.

The worker’s brief must identify the scope of the operator’s authorization. Merging, enabling auto-merge, closing a PR and deploying each require explicit authority for that action. If authority is unclear, return to the operator’s instruction.

After a repair, the worker obtains independent review where required and runs the affected checks. Attesting readiness can trigger an enabled merge. Record readiness for the reviewed commit only when the operator currently authorizes merging this PR and its gates pass. An explicit hold keeps readiness pending even after review and checks pass. Reassess when the head or relevant base changes. Keep the worker available through GitHub’s confirmed merge, verification on the target branch, and any configured follow-up or explicit handoff.
