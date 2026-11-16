---
name: matplotlib
description: Figure engineering patterns, gotchas, and reusable helpers for matplotlib. Use when directly building standalone figure scripts, diagram generators, or canvas visuals outside the epq render pipeline — e.g., generate_layer_icons.py, vision project banners, morning-brief charts, competitive analysis figures. Covers shape boundary math, arrow/edge geometry, series consistency, font registration, zorder, Unicode rendering, and canvas clipping. Distinct from the epq skill (which covers the Quarto/LaTeX analysis pipeline). Load alongside epq when figure work involves both the pipeline and standalone diagram construction.
---

# Matplotlib

Use this skill for standalone figures, diagram generators, and canvas visuals. Load it alongside the project’s document-rendering guidance when both apply.

Read the relevant notes before changing figure construction:

| Task | Read |
| --- | --- |
| Text offsets, clipping, legends, fonts, save/close order, fixed output dimensions | [Rendering and layout](references/rendering-and-layout.md) |
| Arrow attachment, rounded boundaries, z-order, shared series geometry, icon meaning | [Diagram geometry](references/diagram-geometry.md) |
| Domestic/world geography, panel extents, flow arcs, Mercator coordinates | [Geographic maps](references/geographic-maps.md) |

## Visual verification

Render the changed figure and inspect the image for clipping, overlap, readability, and contrast against each label's actual background. A successful render does not establish that the figure communicates correctly. Save before closing the figure. Use the current project's render commands and output paths.
