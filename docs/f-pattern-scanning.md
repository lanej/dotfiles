# Writing for F-pattern scanning

Maximize decision-relevant understanding per reader effort.

## Scope and research

Apply this specification to left-to-right prose, including proposals, release notes, and review descriptions.

Nielsen Norman Group's [F-shaped reading pattern](https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content-discovered/) describes observed scanning. Readers often scan opening lines horizontally, then scan down the left side. The pattern is approximate, not a layout to reproduce.

Its [layer-cake scanning research](https://www.nngroup.com/articles/layer-cake-pattern-scanning/) describes readers using meaningful headings to locate relevant sections.

These recommendations apply general research; they do not establish a PR-specific optimum.

## Writing rules

MUST means required; SHOULD allows an exception when the reader's task warrants it.

1. **Lead with the outcome.** The opening MUST state what changes, what matters, or what action the reader needs.
2. **Frontload meaningful words.** Paragraphs and list items SHOULD begin with information-bearing words.
3. **Order by reader need.** Place decisions, required actions, and consequential constraints before optional detail. Keep instructions in execution order when order matters.
4. **Keep paragraphs focused.** Each paragraph SHOULD develop one idea.
5. **Choose navigation deliberately.** Longer documents SHOULD use descriptive headings with a logical hierarchy. Short documents need no headings. Use brief labels to distinguish independent points when a list helps scanning.
6. **Use structure for meaning.** Keep connected reasoning in prose. Use lists for independent points, numbered steps for sequences, and tables for comparisons. Do not add empty sections or decorative scaffolding.
7. **Separate ideas visibly.** Use blank lines between paragraphs and before lists. Let the renderer wrap prose; do not manufacture an F shape with manual line breaks.
8. **Emphasize selectively.** Bold SHOULD identify key labels or consequential facts, never whole paragraphs.
9. **Keep caveats with claims.** Material limits MUST appear beside the claim or action they qualify.
10. **Name link destinations.** Links MUST use meaningful text identifying their subject. Place supporting links beside the relevant claim; avoid generic instructions such as “click here.”
11. **Choose the clearest medium.** Use screenshots for appearance, diagrams for structure, and charts for quantitative patterns when clearer than prose. Not every document needs a visual. Images MUST complement the outcome and informative text labels, not erase that scan path. For diagrams or charts, read [Diagrams and charts](diagrams-and-charts.md).

Do not impose fixed word counts, heading counts, or list lengths.

## Illustrative example

Fictional release: cursor pagination becomes available alongside page numbers.

> Export changing shipment lists without skipping records by using cursor pagination. Page-number requests remain available but can skip records when shipments arrive during an export.
>
> - **Requests:** Pass the returned cursor to fetch the next batch.
> - **Completion:** Stop when the response contains no next cursor.
> - **Adoption:** Update exporters before enabling concurrent shipment imports.

## Rendered scan check

Preview in the intended renderer before sharing.

- Scan the opening, headings, labels, and first words for outcome, action, and major distinctions.
- Check that consequential caveats remain visible beside the claims they qualify.
- Check spacing, wrapping, emphasis, and link text at desktop and mobile widths.
- Read fully; remove repetition between the scan path and explanation.

This is an editorial check, not an eye-tracking measurement or proof of reader behavior.
