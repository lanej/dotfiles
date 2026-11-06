---
name: pr-writer
description: "Use when drafting or revising a pull request title and description, or preparing a branch for review. Follow repository conventions and add GitHub-specific formatting when applicable."
---

# PR Writer

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

Do not create, update, or merge the pull request. The caller owns authorized
publication and verification of the saved result.
