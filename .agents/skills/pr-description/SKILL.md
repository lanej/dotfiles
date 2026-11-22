---
name: pr-description
description: Use when preparing or revising a pull request title and description under the repository's Octo format contract.
---

# Write a PR description

The calling agent owns the content and factual accuracy. Octo checks declared format rules and publishes the submitted draft; it does not write or judge its meaning.

Read the repository's CONTRIBUTING and development guidance, the template selected in `.octo/pr-contract.json`, and that contract. Read .octo/pr-style.json when present for advisory local guidance and PR-sample statistics; its proposed format rules are not active checks. Follow authored project instructions. Explain the final outcome and why; add only context the diff and checks do not supply. Omit empty sections, boilerplate, file inventories, and automated test inventories. Include required template sections and material compatibility or verification gaps. Never invent observations or links.

Assess complexity from the actual diff: routine changes need a short explanation; interacting components or compatibility changes need the relevant decisions and limits. Use PR Flow evidence for an existing PR when available. Its current analyze command requires a PR URL; unavailable analysis is advisory, not a publication blocker. Historical PR statistics and inferred styles are also advisory.

Write the final title and description to a local file. Run `octo-manager pr validate --title TITLE --body-file FILE` and fix its specific findings. This command runs local checks only. When the user authorizes publication, run `octo-manager pr publish --title TITLE --body-file FILE`. An invalid draft fails before acceptance. A pending receipt means accepted for publication, not that GitHub accepted the PR. Inspect completion with `octo-manager publication show ID`. Publication defaults to tracking when the caller has a Codex thread ID. Use `--no-track` to opt out or `--track` to require a supported owner identity. Verify the publication and tracking status separately. Retry an unavailable enrollment with `octo-manager publication retry ID`.

For title/body revisions, apply these same writing and validation instructions to the revised draft. Octo never adds a separate writer or rewrites the content.
