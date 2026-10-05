# Conventional Pull Requests

Draft 0.1

A lightweight convention for pull request titles and descriptions. Help reviewers quickly understand what changes and why, find supporting evidence, and make an accurate, well-informed approval or rejection decision.

Inspired by [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) and [Conventional Comments](https://conventionalcomments.org/).

## Format

```markdown
<type>[(<scope>)][!]: <subject>

<what changes and the resulting behavior, followed by why it matters>

## Result

<screenshot or concrete example, when useful>

## Additional context

<decisions, constraints, or review needs, when relevant>
```

The title identifies the kind of change and its intended outcome. Every body starts with prose: first explain what changes and the resulting behavior, then why the change matters. Use one or two short paragraphs without an opening heading.

Use the sections in the order shown. `## Result` and `## Additional context` are optional: omit each heading and its content when unnecessary. Replace all drafting prompts; do not publish placeholders or empty sections.

For example:

```markdown
fix(tracking): preserve filters when returning from details

Keep the destination filter when returning to the shipment list, so reviewers can continue through the same set of shipments. Previously, returning from details reset the filter.
```

This is a complete description. Larger changes may need more explanation; smaller ones may need only a sentence.

## Specification

The words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are used as defined in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

1. The title MUST follow the format `<type>[(<scope>)][!]: <subject>`. Square brackets indicate optional elements and are not literal characters.
2. The type MUST describe the final change as a whole. Use `feat` for a new capability and `fix` for a correction. Other types MAY describe other purposes; the vocabulary below is recommended.
3. A scope MAY identify the affected component. It SHOULD be a short, lowercase name familiar to the project. Omit it when no single scope fits.
4. The subject MUST describe the intended outcome. It SHOULD use the imperative mood, start with a lowercase letter, and omit a trailing period. The complete title SHOULD be at most 72 characters.
5. A breaking change MUST place `!` immediately before the colon. Its description MUST explain the incompatibility and what affected users need to do.
6. The description MUST begin with prose explaining what changes, followed by why it matters, without an opening heading. It SHOULD use a concrete before/after example when that makes the outcome clearer.
7. Additional context SHOULD supply information needed for review that the opening prose, diff, and automated checks do not already provide. After the opening prose, the body MAY include `## Result`, then `## Additional context` in that order, omitting either when unnecessary.
8. Material compatibility constraints, rollout requirements, and known verification gaps MUST be disclosed when they affect acceptance or use. Claims about behavior and verification MUST be supported by actual evidence.
9. A screenshot or other illustration SHOULD be included when it helps assess the result. It MUST show the actual current result, have descriptive alt text, and use a durable URL that renders for the intended reviewers.
10. References MUST be accessible to the intended reviewers. Referenced files MUST exist on GitHub and be linked to the relevant version. GitHub objects MUST be linked with full URLs or appropriate autolinking references. Local machine or session paths MUST NOT be used as evidence. Relevant issues and design decisions SHOULD be linked when available.
11. The description SHOULD NOT repeat file inventories, commit history, test cases, coverage figures, test counts, or automated check results. Empty sections and boilerplate checklists SHOULD be omitted.
12. The title and description MUST reflect the final scope of the PR. A stacked PR MUST identify its parent and describe its own change.
13. Bulleted lists SHOULD be used when multiple independent points are easier to scan than prose. Tables SHOULD be used when several items need comparison across shared attributes. Connected explanations SHOULD remain prose; numbered lists SHOULD be reserved for sequences where order matters. Measurement tables MUST preserve units, workload scope, evidence source, and material caveats without implying unsupported comparisons.
14. Paragraphs and list items MUST NOT be artificially wrapped or use manual line breaks for appearance. Meaningful line breaks in code and actual example output MUST be preserved.

## Types

Use the same meanings as the project's Conventional Commit types.

| Type | Purpose |
| --- | --- |
| `feat` | Add a capability |
| `fix` | Correct a defect |
| `perf` | Improve performance |
| `refactor` | Restructure without changing behavior |
| `docs` | Change documentation |
| `style` | Change formatting without changing behavior |
| `test` | Add or improve tests |
| `build` | Change dependencies or build tooling |
| `ci` | Change continuous integration |
| `chore` | Other maintenance |

Choose the type for the resulting change, rather than its supporting edits. A feature with tests and documentation is still `feat`. Unrelated outcomes should usually be separate PRs.

## Body sections

Begin with prose, then use the exact level-two headings below for any optional sections. Keep each included section concise.

| Section | Content |
| --- | --- |
| Opening prose (no heading) | Required: what changes and the resulting behavior, followed by why it matters |
| Result | Optional: a current screenshot, example output, or before/after example that helps assess the implemented result |
| Additional context | Optional: consequential decisions, compatibility or rollout constraints, manual findings, verification gaps, or questions requiring reviewer judgment |

Result must show the artifact, example, or decision-relevant measurement table itself, rather than summarize changes or list examples available elsewhere. Explain changed rules in the opening prose. Additional context concerns this particular change; do not fill it with an explanation of the template.

Link relevant requirements in the section they support. In Additional context, use brief labels such as **Compatibility:**, **Rollout:**, or **Review:** when they help scanning. There is no default Testing or Verification section, and no requirement to fill every section.

## Readability and discoverability

Use prose for connected reasoning. Use bullets when multiple independent outcomes, constraints, tradeoffs, or decisions are easier to scan separately. Each item should make one assessable point, with parallel phrasing and enough explanation to understand its effect. Avoid sentence-by-sentence bullets, file inventories, lists repeating the opening, and arbitrary item counts. Use numbered lists when order matters, such as migration steps.

Use a compact table when readers need to compare several items across shared attributes, such as before/after performance and cost, alternatives, compatibility, or rollout status. Put measurement and example results under Result; put tradeoffs and constraints under Additional context. Label units and workload scope, identify the evidence source, and keep caveats nearby. Distinguish per-item from combined measurements, and serving queries from refresh work. Separate unlike measurement layers or clearly label them; do not combine overlapping timings, invent missing values, or infer unsupported speedups. Explicitly mark missing values as not measured or not reported. Keep long reasoning outside cells. Tables should contain decision-relevant manual measurements or external evidence, not routine automated check reports.

Use Before/After columns only when workloads and measurement layers match. Otherwise use rows identified by workload and layer, or separate tables. API query timing is not full dashboard load unless browser rendering was measured. Write "Not measured" or "Not reported" for missing values rather than unexplained dashes.

Table cells follow the same prose and linking rules: do not insert `<br>` or other manual breaks for appearance, and link cited GitHub objects in cells. Split overloaded columns or move details into adjacent prose. Do not label workloads as "the same" without evidence of matching scope. The opening prose still must explain why the change matters.

Write each paragraph and list item on one source line, allowing GitHub to wrap it for the reader's screen. Use blank lines between paragraphs and before lists. Preserve meaningful line breaks in code and actual example output.

Reference files only when they exist on GitHub and reviewers can open them. Use descriptive Markdown links to full GitHub file URLs pinned to the relevant commit SHA, with line anchors when useful. An unlinked filename, inline-code path, or local plan is not a discoverable reference.

Link GitHub issues and PRs using full URLs or autolinking references: `#123` in the same repository and `owner/repo#123` across repositories. Link commits, reviews, discussions, releases, comparisons, and Actions runs directly to the object being cited. When citing a code symbol as evidence, link its definition. Verify that targets exist, identify the intended version, and are accessible to reviewers before handoff.

Read the rendered description as a reviewer before requesting a decision. The outcome should be clear immediately, supporting evidence reachable in one click, and the facts and judgments needed for approval or rejection explicit.

## Examples

### Feature

```markdown
feat(exports): allow downloading filtered shipments

Export the shipments matching the current filters, so operations can reconcile a selected group without downloading the entire account history.

## Additional context

The export uses the filters at the time it is requested; later filter changes do not alter an export already in progress.
```

### Breaking change

```markdown
feat(api)!: require cursor pagination for shipment lists

Replace offset pagination with cursors so shipment lists remain consistent as new shipments arrive.

## Additional context

**Compatibility:** Clients must replace the page parameter with the next_cursor returned by the previous response. Requests using page are rejected.
```

### Verification gap

```markdown
fix(printing): retain the selected printer after reconnecting

Restore the selected printer after a connection interruption, so the next label goes to the same device instead of the system default.

## Additional context

**Review:** Reconnection was checked with the local simulator. Physical printer reconnection remains unverified and needs a device check before release.
```

## Adoption

Projects can adopt this convention for PR titles and descriptions independently of how they merge commits. A conventional PR title does not make the commits conventional or configure release automation.

Required repository fields still apply and take precedence over this default layout when they conflict. Map the content into those fields without duplicating it or padding the rest of the description. When working in a repository that has not adopted this convention, follow its title and template requirements.
