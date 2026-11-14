---
name: testing
description: Use when selecting, writing, running, or reviewing software verification in a project with an installed source-code lifecycle policy.
---

# Testing

Read the project policy through [source-code lifecycle](../source-code-lifecycle/SKILL.md). Preserve existing project gates. Select the smallest real check that can expose a defect; scale evidence with the selected stage, consequences, and uncertainty.

- **Research:** Compile/typecheck and exercise the experiment against the relevant real boundary. Preserve findings and limits. Discarded experiments need no permanent suite; retained consequential results need reproducible evidence.
- **Alpha:** Protect retained steel-thread behavior and consequential failures. Favor focused checks through the real entrypoint; add unit tests when stable decisions benefit from isolation. Avoid speculative harnesses and coverage quotas.
- **Beta:** Run the full language profile. Verify affected integrations and compatibility or migration behavior against independent expectations. Preserve counterexamples in existing regression checks where practical.
- **Production:** Add independent review and relevant recovery, rollout, and operational evidence. State which requirements automation establishes and which need manual or external observation. Do not claim measured reliability from a stage label.

Run `python3 scripts/check-source-code.py LANGUAGE` for the stage-selected generated gate. Full language runners remain available for additional evidence. A failing or unavailable required check is a failure or limitation to resolve or report; do not silently skip it. Run affected checks after relevant changes, then broaden only when consequences or unresolved interactions justify it.

TDD is optional unless the project requires it. Protect meaningful retained behavior before substantial expansion. Tests must admit contradictory evidence; copying the production algorithm or asserting source strings cannot establish correctness. Use controlled external commands when testing orchestration; real compatibility claims require real integrations. Distinguish observed legacy behavior from intended behavior and mocked boundaries from live outcomes.
