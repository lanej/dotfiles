---
name: pr-writer
description: "Use when drafting or revising a pull request title and description, or preparing a branch for review. Follow repository conventions and add GitHub-specific formatting when applicable."
---

# PR Writer

The calling agent may use this drafting guidance directly for PR creation or title/body revisions. A separate writer is optional, not a publication prerequisite. When the repository has Octo's pr-description skill, follow it and run `octo-manager pr validate` on the finished draft. The caller owns factual accuracy, authorized publication, and verification of the saved result. Other review platforms use the shared pull-request writer. Delegated writers must not recurse.

Read [the shared PR writer](../../agents/pull-request-writer.md) and the writing
references it requires. For a GitHub pull request, also read
[the GitHub PR writer](../../agents/github-pr-writer.md).

Use these as drafting instructions, not as permission to publish. Inspect the
final diff and target repository's requirements, then return the inherited
title, body, and blockers contract. Existing repository title and template
requirements take precedence over the supplied defaults.

Keep the draft proportional to the change. Explain the outcome and why it
matters; add only evidence, constraints, and review needs the diff and checks do
not already supply. Do not invent verification or add boilerplate checklists.

When acting as a separately delegated writer, do not create, update, or merge the pull request. The calling agent may publish with existing user authorization and owns verification of the saved result.

For rendered UI changes, capture meaningful before/after evidence during verification and include durable screenshots in the PR or a follow-up comment. Inspect the rendered result; successful rendering alone does not establish correct content. Keep evidence proportional and preserve repository screenshot requirements.
