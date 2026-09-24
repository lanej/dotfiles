---
description: "Finish the planned work without checking in: make routine decisions, fix what breaks, stop only for genuine blockers"
---

# Continue

Planning is done. Execute every remaining task in the plan, spec, or todo list to verified completion without pausing for approval between steps.

Decide routine matters yourself and keep going: implementation details, following existing patterns, running tests/builds/linters, fixing failures they surface, installing a dependency the task clearly needs. Never stop over size, effort, or the number of tasks left (Constitution V).

Stop and ask only for:
- A requirement that is contradictory, or ambiguous with no reasonable default
- A trade-off between valid approaches that the plan doesn't settle
- Destructive or hard-to-reverse actions (data deletion, force push, public API breaks, anything needing approval under CLAUDE.md)
- A failure you still can't explain after several distinct fix attempts

Stay in scope: fix what the task breaks, not everything you notice; note unrelated improvements in the summary instead.

Report at milestones, not per edit. End with what was done, how it was verified, and anything left open.
