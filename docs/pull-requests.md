# Pull requests

A PR should help a reviewer understand the intended outcome and the decisions
that need judgment. Keep the description proportional to the change; one or two
short paragraphs are usually enough.

## Prepare the change

- [Keep the change coherent](https://google.github.io/eng-practices/review/developer/small-cls.html).
  Split unrelated work by purpose, not an arbitrary line count. Keep changes
  together when they share correctness or compatibility context.
- Inspect the final diff against the intended review base. For a stack, name the
  parent PR and make the child description cover its own change.
- Run the applicable checks and review the implementation and its tests before
  requesting review. Clear code and durable documentation should carry details
  that future maintainers will need.

## Write the description

[Explain what changes and why](https://google.github.io/eng-practices/review/developer/cl-descriptions.html).
Lead with the problem and resulting behavior, using a concrete before/after
example when useful. Supply context that is not apparent from the diff. Link
relevant requirements and design decisions.

Use a specific, concise title that follows the repository's conventions.
[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) can make
change intent clear; do not impose a new title convention on another repository.

Let tests and checks provide their own evidence. Do not transcribe test cases,
coverage figures, test counts, or automated check results into the description.
There is no default Testing or Verification section. Add manual observations,
external evidence, known verification gaps, compatibility constraints, or
rollout/recovery instructions only when reviewers cannot learn them from the
diff and existing checks.

Avoid file inventories, commit-by-commit narratives, repeated summaries, empty
headings, boilerplate checklists, and implementation history. When the scope
changes, rewrite the title and body around the final behavior. Honor required
repository fields without expanding them into another report.

## Show the result

Include a screenshot when it helps reviewers understand or assess a visual
change, such as a UI, chart, or rendered document. Omit it when the diff and prose
already explain the change adequately; screenshots are not a universal PR
requirement.

When included, show the actual current result, use descriptive alt text and a
durable image URL, and verify that it renders inline on GitHub. A local path or
downloadable CI artifact is insufficient. Keep the image current when the visible
result changes. Do not invent an image URL or substitute a mockup for the
implemented result.

## Minimal shape

Start with **What and why**. Add a screenshot when it helps explain the result
and **Additional context** when it supplies information the diff and checks do
not show. Headings are optional for a short description; omit unused sections
and drafting prompts.

This is enough for a routine UI fix; a screenshot can illustrate the result:

> Keep the selected shipment and destination filter when returning from details,
> so reviewers can continue through the same set of shipments. Previously,
> returning to the list restored the selection but reset the filter.

## Publish and hand off

Use the existing PR when updating a change. Confirm the repository, branch,
review base, and publication authorization before creating a new one. Inspect
the published title, rendered body, any included images, and stack relationship.

Pass multiline descriptions through a file (for example,
`gh pr create --body-file /tmp/pr-body.md`) so Markdown and literal text survive
unchanged. Creating or updating a PR does not authorize merging it.
