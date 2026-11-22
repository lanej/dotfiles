# Standing coordinator instructions

Read [the coordinator workflow](PR-WORKFLOW.md) at session start. Discover existing conversations for the operator’s selection, keep brainstorms as drafts and create workers for specified outcomes. Use host-qualified worker identities and report bulk results per task.

## Dispatch

- Include the outcome, success criteria, constraints, repository guidance, checks, relevant issue or PR and the operator’s authorization in each brief. Return proposed changes in scope for the operator’s decision.
- Keep up to two workers actively running on the Mac. Workers waiting for CI free a slot. Keep additional tasks as drafts until capacity is available.
- Check host connectivity before dispatch. Preserve other people’s processes, checkouts and uncommitted work. Follow the target repository’s worktree and cleanup guidance.
- Prefer one reviewable PR per change. Stack PRs when later changes depend on earlier ones and each layer can be reviewed on its own.
- Use Octo Manager’s event delivery for PR follow-up. Report check failures, unavailable ownership or uncertain outcomes with enough evidence for the next decision.

Keep operator updates concise, with links to the relevant tasks or PRs. Keep credentials and customer data out of coordinator notes.
