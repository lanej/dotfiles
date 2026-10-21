# Diagrams and charts

Use visuals to explain structure, workflow, or quantitative patterns with less reading effort.

## Design

Answer one reader question with one visible takeaway. Choose the form that exposes the relationship:

| Reader needs | Use |
| --- | --- |
| Choices and outcomes | Flow or decision tree |
| Structure | Dependency or boundary diagram |
| Change | Before/after comparison |
| Quantitative patterns | Chart |

- Name concrete concepts, inputs, and outputs. Keep prose and lists as native text. Images must add spatial relationships, data patterns, or visual evidence beyond restyling text.
- Give arrows a consistent direction and explicit meaning: data flow, dependency, or sequence. Distinguish meanings when combining them. Label conditional branches beside their edges.
- Use shapes and grouping consistently. Draw meaningful boundaries, such as a pure decision excluding network and storage.
- Make the entry point obvious. Use whitespace and short labels; avoid crossing lines and unattached notes.

Remove any element whose deletion loses no information or relationship, including redundant titles.

## Palette and accessibility

Authored GitHub diagrams and charts default to dark:

| Role | Color |
| --- | --- |
| Background | `#0d1117` |
| Text | `#e6edf3` |
| Muted text | `#9da7b3` |
| Borders | `#30363d` |
| Accents | `#79c0ff`, `#d2a8ff` |

Preserve actual application screenshots. Use readable contrast and explicit labels; never rely on color alone.

## Evidence and preview

Show actual evidence or clearly identified conceptual design. Never fabricate measurements or imply unmeasured results.

Preserve axes, units, workload scope, sources, and material caveats. Keep the takeaway and consequential limits in adjacent text without repeating the visual. Captions must add information.

Preview the actual render in the intended theme at desktop and mobile widths. Check labels, contrast, boundaries, arrow routing, and clipping. Keep the outcome and informative text labels visible; images must complement the scan path.
