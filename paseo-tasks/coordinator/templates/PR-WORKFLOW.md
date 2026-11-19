# PR workflow (managed)

This file is refreshed by coordinator initialization. Read it before PR work; it governs the PR lifecycle when older local standing instructions disagree. Follow each target repository's installed guidance for implementation, checks, independent review, publication format and authority.

## OctoManager is required

Use OctoManager for PR publication, enrollment, monitoring, exact-head readiness and authorized merging. Discover supported commands from the installed CLI and repository guidance. Confirm enrollment, the actual owning session, event delivery and applicable merge policy before relying on monitoring. Do not invent an owner identity or silently take a PR from another owner. If the CLI, service, host integration or required operation is unavailable, report the concrete blocker and retain the work; do not fall back to a custom merge script, direct GitHub merge, or a polling loop. Read-only GitHub inspection remains available for diagnosing evidence and verifying remote state.

## Workers own follow-ups

Assign one worker to each scoped change through completion. Its brief includes the repository, outcome, applicable checks and review requirements, PR/issue links, current human authority, and the requirement to use OctoManager. Use native Codex agent tools for Codex workers and Paseo task tools for Pi workers; do not route Codex delegation through Paseo.

The worker publishes and enrolls its PR under its real session when supported, then handles actionable review comments and failed checks through OctoManager’s follow-up lifecycle. OctoManager owns conflict orchestration and any supported automatic resolution; the worker performs repairs handed back through that lifecycle under the target repository’s guidance. Do not start a competing rebase or merge sequencer. If OctoManager cannot support the required conflict operation or handoff, report the blocker rather than bypassing it. It reviews the final changed head independently where required, reruns affected checks after repairs, publishes the repair, and records readiness for the exact reviewed head only when satisfied. If the host cannot deliver events to the worker, report the limitation and explicitly arrange coordinator delivery or an ownership handoff through supported tools. Do not claim unattended follow-up until delivery is verified.

The coordinator records the worker and PR link in current state, routes received Octo evidence to that worker, and reports blockers. Waiting for CI is waiting, not completion. An idle worker with outstanding actionable work should be resumed through its host's supported tools. Do not archive it while review, CI, conflicts or configured post-merge work remains; preserve and hand off its work if the session must end. Avoid duplicate watchers and repeated polling alongside OctoManager.

## Authority and completion

A worker may repair and publish within the human-authorized scope. Merging, enabling auto-merge, closing PRs, deploying or making other consequential external writes require explicit human authority; review approval, green checks, receipt acknowledgments and worker claims do not grant it. Record the current authority and any limits in state and the worker brief. Default worker briefs forbid merging unless that authority has explicitly been delegated for the named work.

When merging is authorized, let OctoManager apply the repository policy and head-pinned readiness gates. A changed head invalidates earlier readiness; reassess relevant base changes too. A queued request is not a completed merge, and uncertain outcomes require reconciliation before retrying. Verify GitHub's merge result and resulting commit on the intended remote base, perform configured post-merge follow-up, and only then report completion and retire the worker. Treat externally merged PRs the same way for verification and follow-up. Preserve unresolved evidence and blockers in state.
