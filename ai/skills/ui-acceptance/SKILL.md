---
name: ui-acceptance
description: Use when designing, changing, or reviewing a user interface in a project that selects source-code UI acceptance guidance, including rendered evidence and interaction coverage.
---

# Project UI acceptance

This optional source-code capability defines project UI acceptance. Read [source-code lifecycle](../source-code-lifecycle/SKILL.md) for stage, authority, and adoption, and [testing](../testing/SKILL.md) for proportionate protection. Preserve the project's design system, explicit gates, established stack, and shared/upstream agreement. Installing a browser or Viewrule does not select this policy; installing this profile does not authorize unrelated redesign or changing project gates.

Before designing, identify the user's primary decision and the information needed to make it. Inspect applicable project rules and approved references. Reuse existing configuration for a scoped small edit; do not force every UI into a dashboard or invent universal density, spacing, color, or typography thresholds.

Before claiming a UI change works, inspect the actual affected rendered states at representative viewports with realistic data. Review hierarchy, comparison quality, legibility, clipping, chart truthfulness, and relevant keyboard, loading, empty, error, and recovery behavior. Inspect detailed regions at a readable scale, including right and bottom edges. A resized overview, screenshot capture, successful build, DOM assertion, or clean process exit alone does not establish visual correctness. Report the page, viewport, and state reviewed, and identify missing coverage.

Read [the visual review guidance](references/visual-review.md) when assessing grouping, semantic color, density, or interaction-state coverage. Use the project's configured browser checks and capture tools; Viewrule is optional. Follow the host's browser authorization, visibility, and cleanup rules. Do not fabricate screenshots or automate an unsupported signed-in flow to satisfy an evidence requirement.

Fix objective defects and rerun the affected checks. Do not weaken rules, remove failing selectors, disable enforcement, or mark screenshots approved merely to pass. Scope the evidence to the changed behavior and selected lifecycle: follow the installed testing skill for the minimum useful protection of retained interaction behavior. Existing project gates remain binding at every stage.

Preserve actual user feedback against the exact reference reviewed. A model's judgment is not user approval; approval of one screen does not establish a universal rule. Project selectors, thresholds, feedback, and approved screenshots stay with the project. User-level preferences apply where appropriate without overriding project requirements. Include durable rendered evidence in a review when it helps assess the change, subject to project requirements and publication authorization.
