---
name: testing
description: Use when selecting, writing, running, or reviewing software verification in a project with an installed source-code lifecycle policy.
---

# Testing

Read the project policy through [source-code lifecycle](../source-code-lifecycle/SKILL.md). Preserve existing project gates. Select the smallest real check that can expose a defect; scale evidence with the selected stage, consequences, and uncertainty.

- **Research:** Compile/typecheck and exercise the experiment against the relevant real boundary. Preserve findings and limits. Discarded experiments need no permanent suite; retained consequential results need reproducible evidence.
- **Alpha:** Protect retained steel-thread behavior and consequential failures. Favor focused checks through the real entrypoint; add unit tests when stable decisions benefit from isolation. Avoid speculative harnesses and coverage quotas.
- **Beta:** Require the full language profile for delivery, normally through CI. Verify affected integrations and compatibility or migration behavior against independent expectations. Preserve counterexamples in existing regression checks where practical.
- **Production:** Add independent review and relevant recovery, rollout, and operational evidence. State which requirements automation establishes and which need manual or external observation. Do not claim measured reliability from a stage label.

Optimize local verification for iteration speed. Avoid lengthy local test runs during the edit-and-check loop. Start with the smallest affected check that can expose the defect or verify the change, then run related tests while keeping selection tied to the changed behavior and its dependencies. Let CI run the full suite by default. Broaden local runs only for a concrete failure, risk, explicit project gate, or unavailable CI, and choose the narrowest scope that resolves the concern. Once relevant checks pass, rerun them only after a relevant edit or when new evidence requires it.

For installed generated Go/TypeScript/Python profiles, `python3 scripts/check-source-code.py LANGUAGE` runs the stage-selected gate; reserve full-profile runs for the appropriate delivery gate rather than every local edit. Other detected languages use existing repository commands and the applicable language skill. A failing or unavailable required check is a failure or limitation to resolve or report; do not silently skip it. Targeted local passes do not establish that the full CI suite passed.

TDD is optional unless the project requires it. Protect meaningful retained behavior before substantial expansion. Tests must admit contradictory evidence; copying the production algorithm or asserting source strings cannot establish correctness. Use controlled external commands when testing orchestration; real compatibility claims require real integrations. Distinguish observed legacy behavior from intended behavior and mocked boundaries from live outcomes.

Keep local test timeouts tight for fast feedback, and allow longer timeouts in remote environments such as CI to resist flakes from slower runners and contention. Choose deadlines from the operation's expected duration and observed variability. For example, a fast operation might allow one second locally and thirty seconds in CI; these are illustrative values, not universal defaults. Do not lengthen timeouts to mask failures. Distinguish an operation's deadline from the total duration of a multi-step suite, and keep test deadlines separate from product timeouts.

Use independent review for complex interactions, state transitions, security-sensitive logic, or material uncertainty at every stage. Simple mechanically verifiable changes need no review dispatch. Assess hosted CI separately from local checks. Give reviewers the changed capability, relevant constraints, and actionable findings; have material fixes reviewed again. Reviewers must not recursively dispatch reviews.

During detector sensitivity checks, modify only task-owned inputs and restore only the known mutation; do not use Git checkout/restore or leave the target directory. Do not use a shared stash for baseline checks. Read the project's Git verification reference when assigning evidence tiers or recording the detector that caught a fault.

Read [software verification lessons](references/verification-lessons.md) for detector sensitivity checks, delegated implementation evidence, integration wiring, or browser verification after a rebuild.
