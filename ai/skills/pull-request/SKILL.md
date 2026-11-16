---
name: pull-request
description: Use when preparing, drafting, publishing, or updating a pull request. Own PR writing and select Octo Manager or the native review-platform workflow according to repository policy, available capabilities, and the user's authority.
---

# Pull requests

Inspect the task, diff, intended review base, existing PR, and repository instructions and templates. Creating or updating a PR requires user authorization; this skill does not authorize merge, release, or deployment. Reuse the existing PR for the change. Preserve unrelated work and use the actual calling host and session identity.

## Select the publication workflow

Repository policy takes precedence. When the repository requires Octo Manager, or the user or project selects a supported Octo workflow (including an applicable `.octo/pr-contract.json`), read [the Octo submission contract](../../../docs/octo-pr-submission.md) and the installed CLI help before submitting. Confirm the installed command supports the caller's real harness/session and the required publication contract. Read the installed project drafting instructions and selected template. Current Octo accepts caller-written descriptions, validates the declared format contract, and publishes; it does not write the description. Missing capability, unsupported identity, or an unmet requirement is a blocker when Octo is required; never invent identity or bypass the publisher.

When Octo is not required or selected, use the review platform's native supported workflow. For GitHub, use `gh` for inspection and authorized publication, following the drafting guidance below. An installed Octo executable alone does not enroll a repository or make it mandatory. If an optional Octo path is unavailable, explain the limitation before using the permitted native path. Read installed tool help rather than inventing flags or relying on historical command names.

## Draft and revise

Read [the shared PR writer](../../agents/pull-request-writer.md) and its required writing references. For GitHub, also read [the GitHub writer](../../agents/github-pr-writer.md). Follow the target repository's title, body, template, and screenshot requirements; keep the description proportional and explain the outcome and why. Automated results belong in checks; include material manual observations and verification gaps. Inspect the final change before describing it, and keep the description current when scope changes.

The calling agent owns the final title, body, factual accuracy, and blocker resolution. A separate drafting-only writer is optional when useful or required by repository policy; give it the bundled shared/GitHub instructions, final diff, requirements, base, observed evidence, and limits. Require title, body, and blockers. Drafting delegates do not edit implementation, publish, merge, or dispatch further agents. Preserve unchanged approved prose when applicable. Do not impose a separate drafting stage or process attestation when the selected publisher and repository do not require one.

## Publish and verify

Commit and push only the scoped, authorized change, then verify its remote head SHA and intended base. Publish through the selected workflow using that verified change. Pass multiline descriptions through a body file or structured field. Respect a request for draft status and repository contribution gates. After an uncertain operation, inspect existing PRs or the publisher's receipt before retrying to avoid duplicate publication.

Read back the saved PR URL, repository, head/base, draft state, title, rendered body, and any images or stack relationship. Fix concrete saved-content defects through the required writer path. Distinguish publication from tracking enrollment, notification receipt, review completion, merge, and deployment. Report the saved link and any concrete remaining action. For the full authorized review/remediation/merge cycle, use the separate ship workflow rather than treating publication as merge permission.
