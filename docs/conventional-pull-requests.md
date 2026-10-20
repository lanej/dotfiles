# Conventional Pull Requests

Draft 0.1

Help reviewers understand the outcome and assess the evidence with minimum reading effort. Optimize decision-relevant understanding, not word count.

Inspired by [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) and [Conventional Comments](https://conventionalcomments.org/).

## Format

```markdown
<type>[(<scope>)][!]: <subject>

<what changes and the resulting behavior, followed by why it matters>

<screenshot or concrete example, when useful>

<decisions, constraints, or review needs, when relevant>
```

Replace drafting prompts; do not publish placeholders.

## Specification

The words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are used as defined in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

1. The title MUST follow the format `<type>[(<scope>)][!]: <subject>`. Square brackets indicate optional elements and are not literal characters.
2. The type MUST describe the final change as a whole. Use `feat` for a new capability and `fix` for a correction. Other types MAY describe other purposes; the vocabulary below is recommended.
3. A scope MAY identify the affected component. It SHOULD be a short, lowercase name familiar to the project. Omit it when no single scope fits.
4. The subject MUST describe the intended outcome. It SHOULD use the imperative mood, start with a lowercase letter, and omit a trailing period. The complete title SHOULD be at most 72 characters.
5. A breaking change MUST place `!` immediately before the colon. Its description MUST explain the incompatibility and what affected users need to do.
6. The description MUST begin with prose explaining what changes, followed by why it matters, without an opening heading. It SHOULD use a concrete before/after example when that makes the outcome clearer.
7. Supporting context SHOULD supply information needed for review that the opening prose, diff, and automated checks do not already provide. The body SHOULD omit headings for short descriptions. A longer body MAY use headings that name the actual subject when they help navigation; generic category headings SHOULD NOT be used unless required by the repository.
8. Material compatibility constraints, rollout requirements, and known verification gaps MUST be disclosed when they affect acceptance or use. Claims about behavior and verification MUST be supported by actual evidence.
9. A visual SHOULD be included when it explains the result more clearly than prose. It MUST show actual evidence or clearly identified conceptual design, have descriptive alt text, and use a durable URL that renders for the intended reviewers. Visuals MUST NOT fabricate evidence.
10. References MUST be accessible to the intended reviewers. Referenced files MUST exist on GitHub and be linked to the relevant version. GitHub objects MUST be linked with full URLs or appropriate autolinking references. Local machine or session paths MUST NOT be used as evidence. Relevant issues and design decisions SHOULD be linked when available.
11. The description SHOULD NOT repeat file inventories, commit history, test cases, coverage figures, test counts, or automated check results. Empty sections and boilerplate checklists SHOULD be omitted.
12. The title and description MUST reflect the final scope of the PR. A stacked PR MUST identify its parent and describe its own change.
13. Bulleted lists SHOULD be used when multiple independent points are easier to scan than prose. Tables SHOULD be used when several items need comparison across shared attributes. Connected explanations SHOULD remain prose; numbered lists SHOULD be reserved for sequences where order matters. Measurement tables MUST preserve units, workload scope, evidence source, and material caveats without implying unsupported comparisons.
14. Paragraphs and list items MUST NOT be artificially wrapped or use manual line breaks for appearance. Meaningful line breaks in code and actual example output MUST be preserved.
15. Markdown design SHOULD receive the same care as wording. Heading hierarchy, emphasis, spacing, and content layout SHOULD help reviewers scan the description. Authors SHOULD preview the rendered Markdown before publishing.

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

A feature with tests and documentation is still `feat`. Unrelated outcomes should usually be separate PRs.

## Body content

Show the artifact, example, or measurement itself. Keep captions only when they add context, interpretation, sources, or limits. Omit self-evident narration and template commentary.

Use labels such as **Compatibility:**, **Rollout:**, or **Review:** when they help scanning. There is no default Testing or Verification section.

## Markdown design and discoverability

Apply the [F-pattern quick reference](f-pattern-scanning-quick-reference.md), including its dark palette and rendered scan check.

Each list item should make one assessable point. Avoid sentence-by-sentence bullets and lists repeating the opening.

Place tables beside supporting prose; keep long reasoning outside cells. Distinguish per-item from combined measurements, and serving queries from refresh work. Never combine overlapping timings, invent missing values, or infer unsupported speedups.

Use Before/After columns only when workloads and measurement layers match. Otherwise use rows identified by workload and layer, or separate tables. API query timing is not full dashboard load unless browser rendering was measured. Write "Not measured" or "Not reported" for missing values rather than unexplained dashes.

Table cells follow the same prose and linking rules. Split overloaded columns. Claim matching workloads only with evidence.

Pin file and code-symbol links to the relevant commit SHA, with line anchors when useful.

Autolink issues and PRs with `#123` or `owner/repo#123`, or use full URLs. Link other GitHub objects directly.

## Examples

### Feature

```markdown
feat(exports): allow downloading filtered shipments

Export the shipments matching the current filters, so operations can reconcile a selected group without downloading the entire account history.

The export uses the filters at the time it is requested; later filter changes do not alter an export already in progress.
```

### Breaking change

```markdown
feat(api)!: require cursor pagination for shipment lists

Replace offset pagination with cursors so shipment lists remain consistent as new shipments arrive.

**Compatibility:** Clients must replace the page parameter with the next_cursor returned by the previous response. Requests using page are rejected.
```

### Verification gap

```markdown
fix(printing): retain the selected printer after reconnecting

Restore the selected printer after a connection interruption, so the next label goes to the same device instead of the system default.

**Review:** Reconnection was checked with the local simulator. Physical printer reconnection remains unverified and needs a device check before release.
```

## Adoption

Projects can adopt this convention for PR titles and descriptions independently of how they merge commits. A conventional PR title does not make the commits conventional or configure release automation.

Repository title and template requirements take precedence. Fill required fields without duplication or padding.
