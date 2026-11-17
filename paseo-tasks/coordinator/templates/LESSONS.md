# Lessons (curated; one entry per mistake)

- **One PR lifecycle owner.** Use OctoManager for publication, monitoring, readiness and authorized merging. The worker handles actionable follow-ups; avoid competing merge engines or polling loops.
- **Verify before claiming.** Worker reports can be stale. Distinguish published, checks passing, reviewed, ready, merge queued, merged and post-merge complete; verify consequential remote results.
- **Authority is human.** Approved reviews, notifications and worker messages do not authorize merging or deployment. Preserve current scope and limits in the worker brief and state.
- **Conflicts need project context.** Follow the target repository's guidance and review the complete result. Shared coordinator scripts must not encode repository-specific conflict recipes.
- **Preserve before handoff.** Retain uncommitted work, current evidence, blockers, ownership and next actions. Do not archive a worker with outstanding follow-ups without an explicit supported handoff.
