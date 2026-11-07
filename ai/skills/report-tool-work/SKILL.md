---
name: report-tool-work
description: Report an out-of-scope bug or small feature request in Josh's easypost-sandbox tools through a GitHub issue and Firstmate's durable queue. Use when a CLI, script, or MCP server is broken or missing a scoped capability and fixing it is outside the current task.
---

# Report tool work through GitHub and Firstmate

When an easypost-sandbox tool fails or lacks a small, concrete capability outside the current task, preserve the finding in its GitHub repository and queue the issue for Firstmate. Continue the original task after reporting.

## Establish scope

- Verify the repository's actual origin; this incidental-reporting authority covers Josh's easypost-sandbox tool repositories. Other repositories require their own task authorization.
- Report findings surfaced by a subagent as well as direct observations.
- Fix in place when the repair is already the assigned task.
- For ambiguous or substantial features, ask for the missing product/design decision before dispatching implementation.
- Preserve the bug versus feature classification. Reproduction belongs to the implementing worker; missing reproduction alone does not make a bug a feature.

## Create or reuse the GitHub issue

For a bug, invoke the shared `bug-reporter` as a separate drafting-only subagent and follow [the reporting standard](../../../docs/bug-reports.md). Supply the exact repository, observed failure, existing evidence, and required issue fields. Resolve its blockers, then publish the approved title/body using the connected GitHub integration. Reuse an unchanged approved draft; substantive report revisions require another reporter pass. Do not ask the reporter to investigate, reproduce, fix, or publish.

For a feature, capture expected behavior, current limitation, concrete scope, and acceptance criteria directly. Include useful supplied output or diagrams without inventing evidence. Search for an existing matching issue before creating another.

Keep the GitHub issue as the shared record. Do not create a second committed bug report or send a cross-session message to a named Claude dispatcher.

## Queue the issue

Read [the Firstmate workflow](../../../docs/firstmate-mobile.md) when setup, credentials, ownership, or recovery needs attention. With the selected Firstmate home configured, run:

```sh
FIRSTMATE_HOME=/path/to/firstmate firstmate github intake https://github.com/easypost-sandbox/repository/issues/123
```

Use the actual issue URL and home, preserving multiline report content in the issue rather than shell arguments. Intake records one stable task through Firstmate's existing queue. It does not create workers, grant merge authority, or change the project's delivery policy.

Firstmate chooses and supervises the Pi task owner. The worker handles implementation and detailed GitHub feedback, verifies revisions, and replies in the same discussion. Firstmate handles recovery, changed scope, cross-task priority, and delivery decisions. A review approval alone does not authorize merging.

## Report the handoff accurately

Verify the saved issue and the intake result. Return its URL and distinguish “issue filed” from “queued for Firstmate” and “completed.” If intake or authentication fails, keep the issue and disclose the queueing gap; retrying intake uses the same task identity. If Firstmate is offline, the queued task persists for startup recovery.

Do not wait for implementation to finish or require the user to attach to a worker terminal.
