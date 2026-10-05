# Pull requests

Use [Conventional Pull Requests](conventional-pull-requests.md) for the title and description format in this repository. The guidance below covers preparing, publishing, and handing off the change; other repositories' conventions still apply when working there.

A PR should help a reviewer understand the intended outcome and the decisions that need judgment. Keep the description proportional to the change; one or two short paragraphs are usually enough.

Optimize for quick understanding and an accurate, well-informed approval or rejection decision. Make supporting evidence easy to discover from the description.

## Prepare the change

- [Keep the change coherent](https://google.github.io/eng-practices/review/developer/small-cls.html). Split unrelated work by purpose, not an arbitrary line count. Keep changes together when they share correctness or compatibility context.
- Inspect the final diff against the intended review base. For a stack, name the parent PR and make the child description cover its own change.
- Run the applicable checks and review the implementation and its tests before requesting review. Clear code and durable documentation should carry details that future maintainers will need.

## Write the description

[Explain what changes and why](https://google.github.io/eng-practices/review/developer/cl-descriptions.html). Start with what changes and the resulting behavior, then explain why it matters. Use a concrete before/after example when useful. Supply context that is not apparent from the diff. Link relevant requirements and design decisions.

Use a specific, concise title that follows the repository's conventions. [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) can make change intent clear; do not impose a new title convention on another repository.

Let tests and checks provide their own evidence. Do not transcribe test cases, coverage figures, test counts, or automated check results into the description. There is no default Testing or Verification section. Add manual observations, external evidence, known verification gaps, compatibility constraints, or rollout/recovery instructions only when reviewers cannot learn them from the diff and existing checks.

Avoid file inventories, commit-by-commit narratives, repeated summaries, empty headings, boilerplate checklists, and implementation history. When the scope changes, rewrite the title and body around the final behavior. Honor required repository fields without expanding them into another report.

## Readability and links

Use bullets for multiple independent outcomes, constraints, or review decisions when that makes them easier to scan; use prose for connected reasoning or a single point. Keep items parallel and concise. Avoid file inventories and lists that repeat the opening. Number steps only when their order matters.

Use tables when several items need comparison across shared attributes, such as before/after performance and cost, alternatives, or compatibility. Keep columns compact and label units, workload scope, and evidence source. Preserve caveats and distinguish per-item from combined measurements; do not present unlike layers or refresh costs as equivalent query measurements, invent missing values, or calculate unsupported speedups. Put numerical results under Result and tradeoffs under Additional context. Keep longer reasoning outside cells; routine automated check results still belong to the checks.

Reserve Before/After columns for matching workloads and layers; otherwise identify each measured workload and layer by row or use separate tables. Label API timings accurately when browser rendering was not measured. Mark missing values as "Not measured" or "Not reported" rather than unexplained dashes.

Write each paragraph and list item on one source line. Let GitHub wrap text for the reader's screen; preserve meaningful line breaks in code and actual example output.

Referenced files must already exist on GitHub. Link them with descriptive text to the relevant commit's full GitHub file URL, adding line anchors when useful. Link GitHub issues and PRs with full URLs or autolinking references (`#123` in this repository, `owner/repo#123` across repositories); link commits, reviews, discussions, releases, comparisons, and Actions runs to the specific object cited. Verify each target exists and is accessible to reviewers. Do not reference local-only files or leave cited paths and object names unlinked.

## Show the result

Include a screenshot when it helps reviewers understand or assess a visual change, such as a UI, chart, or rendered document. Omit it when the diff and prose already explain the change adequately; screenshots are not a universal PR requirement.

When included, show the actual current result, use descriptive alt text and a durable image URL, and verify that it renders inline on GitHub. A local path or downloadable CI artifact is insufficient. Keep the image current when the visible result changes. Do not invent an image URL or substitute a mockup for the implemented result.

## Description template

Start with prose answering what changes, then why, without an opening heading. Use the optional headings below in this order; omit **Result** and **Additional context** when they do not add useful evidence or information. Remove drafting prompts and empty sections.

```markdown
Explain what changes and the resulting behavior, followed by why it matters.

## Result

Show a current screenshot or concrete example when it helps assess the result.

## Additional context

Add decisions, constraints, manual findings, or review questions the diff and checks do not already supply.
```

Required repository templates take precedence over this default layout; map the same content into their fields without duplicating it.

Result shows the screenshot, output, or example itself. A summary of changed rules belongs in the opening prose. Additional context concerns this particular change; do not fill it with an explanation of the template.

This is enough for a routine UI fix; a screenshot can be added under **Result**:

> Keep the selected shipment and destination filter when returning from details, so reviewers can continue through the same set of shipments. Previously, returning to the list restored the selection but reset the filter.

## Publish and hand off

Use the existing PR when updating a change. Confirm the repository, branch, review base, and publication authorization before creating a new one. Inspect the published title, rendered body, any included images, and stack relationship.

Pass multiline descriptions through a file (for example, `gh pr create --body-file /tmp/pr-body.md`) so Markdown and literal text survive unchanged. Creating or updating a PR does not authorize merging it.
